from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class WorkshopSaleLine(models.Model):
    _name = 'yt.reception.sale.line'
    _description = 'Workshop billable service or spare part'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    order_id = fields.Many2one('yt.reception.order', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='order_id.company_id', store=True)
    product_id = fields.Many2one('product.product', required=True, domain="[('sale_ok','=',True)]")
    name = fields.Char(required=True)
    product_uom_qty = fields.Float(string='الكمية', default=1, required=True, digits='Product Unit of Measure')
    price_unit = fields.Float(string='سعر الوحدة', digits='Product Price')
    available_qty = fields.Float(string='المتاح بالموقع', compute='_compute_available_qty', digits='Product Unit of Measure')
    sale_line_id = fields.Many2one('sale.order.line', readonly=True, copy=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.display_name
                line.price_unit = line.product_id.lst_price

    @api.depends('product_id', 'order_id.location_id')
    def _compute_available_qty(self):
        for line in self:
            line.available_qty = 0.0
            if line.product_id and line.order_id.location_id and line.product_id.type == 'product':
                line.available_qty = line.product_id.with_company(line.order_id.company_id).with_context(
                    location=line.order_id.location_id.id
                ).free_qty

    @api.constrains('product_uom_qty', 'price_unit')
    def _check_values(self):
        for line in self:
            if line.product_uom_qty <= 0 or line.price_unit < 0:
                raise ValidationError(_('الكمية يجب أن تكون موجبة والسعر غير سالب.'))


class WorkshopSale(models.Model):
    _inherit = 'yt.reception.order'

    location_id = fields.Many2one(
        'stock.location', string='موقع قطع الغيار',
        domain="[('usage','=','internal'), ('company_id','in',[False,company_id])]",
        check_company=True,
    )
    sale_line_ids = fields.One2many('yt.reception.sale.line', 'order_id', string='الخدمات وقطع الغيار')
    sale_order_id = fields.Many2one('sale.order', string='أمر البيع', readonly=True, copy=False)
    invoice_ids = fields.Many2many('account.move', string='الفواتير', compute='_compute_invoices')
    invoice_count = fields.Integer(compute='_compute_invoices')

    @api.depends('sale_order_id.invoice_ids')
    def _compute_invoices(self):
        for order in self:
            invoices = order.sale_order_id.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice')
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

    @api.constrains('location_id', 'company_id')
    def _check_stock_location_company(self):
        for order in self:
            if order.location_id and order.location_id.company_id and order.location_id.company_id != order.company_id:
                raise ValidationError(_('موقع المخزون يجب أن يتبع شركة أمر العمل.'))

    def _check_part_availability(self):
        self.ensure_one()
        parts = self.sale_line_ids.filtered(lambda l: l.product_id.type == 'product')
        if parts and not self.location_id:
            raise UserError(_('حدد موقع قطع الغيار قبل إنشاء أمر البيع.'))
        needed = {}
        for line in parts:
            product = line.product_id
            qty = line.product_id.uom_id._compute_quantity(line.product_uom_qty, product.uom_id)
            needed[product] = needed.get(product, 0.0) + qty
        for product, qty in needed.items():
            free = product.with_company(self.company_id).with_context(location=self.location_id.id).free_qty
            if float_compare(free, qty, precision_rounding=product.uom_id.rounding) < 0:
                raise UserError(_('الكمية المتاحة من %s في الموقع المحدد هي %s، والمطلوب %s.') % (
                    product.display_name, free, qty))

    def action_create_sale_and_invoice(self):
        self.ensure_one()
        self.check_access_rights('write')
        self.check_access_rule('write')
        if self.state == 'cancelled':
            raise UserError(_('لا يمكن فوترة أمر عمل ملغي.'))
        if not self.sale_line_ids:
            raise UserError(_('أضف الخدمات أو قطع الغيار أولاً.'))
        if self.sale_order_id:
            return self.action_open_sale_order()
        if self.company_id not in self.env.companies:
            raise UserError(_('ليس لديك صلاحية على شركة أمر العمل.'))
        self._check_part_availability()
        lines = []
        for line in self.sale_line_ids:
            product = line.product_id.with_company(self.company_id)
            if not product.sale_ok:
                raise UserError(_('الصنف %s غير متاح للبيع.') % product.display_name)
            taxes = product.taxes_id.filtered(lambda t: t.company_id == self.company_id)
            lines.append((0, 0, {
                'product_id': product.id,
                'name': line.name,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': product.uom_id.id,
                'price_unit': line.price_unit,
                'tax_id': [(6, 0, taxes.ids)],
            }))
        so = self.env['sale.order'].with_company(self.company_id).create({
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'client_order_ref': self.name,
            'origin': self.name,
            'warehouse_id': self._get_workshop_warehouse().id,
            'order_line': lines,
        })
        self.sale_order_id = so.id
        self.sale_line_ids.write({'sale_line_id': False})
        for source, target in zip(self.sale_line_ids, so.order_line.filtered(lambda l: not l.display_type)):
            source.sale_line_id = target.id
        so.action_confirm()
        # A confirmed sale order is the commercial source of truth. Invoice only
        # invoiceable lines: stockable delivered-quantity products require delivery.
        invoiceable = so.order_line.filtered(lambda l: l.qty_to_invoice > 0)
        if len(invoiceable) != len(so.order_line.filtered(lambda l: not l.display_type)):
            raise UserError(_('لا يمكن إصدار الفاتورة تلقائياً: توجد قطع تتطلب إثبات التسليم أولاً حسب سياسة فوترة الصنف. لم يتم إنشاء أمر بيع أو فاتورة.'))
        invoices = so._create_invoices()
        if not invoices:
            raise UserError(_('لم تتوفر بنود قابلة للفوترة.'))
        return self.action_open_sale_order()

    def _get_workshop_warehouse(self):
        self.ensure_one()
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id),
            ('view_location_id', 'parent_of', self.location_id.id),
        ], limit=1) if self.location_id else self.env['stock.warehouse']
        if not warehouse:
            warehouse = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id)], limit=1)
        if not warehouse:
            raise UserError(_('لا يوجد مستودع لشركة أمر العمل.'))
        return warehouse

    def action_open_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('لم يُنشأ أمر البيع بعد.'))
        return {'type': 'ir.actions.act_window', 'name': _('أمر البيع'),
                'res_model': 'sale.order', 'view_mode': 'form',
                'res_id': self.sale_order_id.id, 'target': 'current'}

    def action_open_workshop_invoices(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('فواتير أمر العمل'),
                'res_model': 'account.move', 'view_mode': 'tree,form',
                'domain': [('id', 'in', self.invoice_ids.ids)],
                'context': {'default_move_type': 'out_invoice'}}
