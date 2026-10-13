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
    line_subtotal = fields.Float(string='الإجمالي', compute='_compute_line_subtotal', digits='Product Price')

    @api.depends('product_uom_qty', 'price_unit')
    def _compute_line_subtotal(self):
        for line in self:
            line.line_subtotal = line.product_uom_qty * line.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.display_name
                line.price_unit = line.product_id.lst_price

    @api.depends('product_id', 'order_id.location_id', 'order_id.company_id')
    def _compute_available_qty(self):
        for line in self:
            line.available_qty = 0.0
            if line.product_id and line.order_id.location_id and line.product_id.type == 'product':
                line.available_qty = line.order_id._available_at_workshop_location(line.product_id)

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
    service_line_ids = fields.One2many('yt.reception.sale.line', 'order_id', string='الخدمات',
                                       domain=[('product_id.type', '=', 'service')])
    part_line_ids = fields.One2many('yt.reception.sale.line', 'order_id', string='قطع الغيار',
                                    domain=[('product_id.type', 'in', ['product', 'consu'])])
    sale_order_id = fields.Many2one('sale.order', string='أمر البيع', readonly=True, copy=False)
    invoice_ids = fields.Many2many('account.move', string='الفواتير', compute='_compute_invoices')
    invoice_count = fields.Integer(compute='_compute_invoices')
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    discount_type = fields.Selection([('fixed', 'مبلغ ثابت'), ('percent', 'نسبة مئوية')], default='fixed', string='نوع الخصم')
    discount_value = fields.Float(string='قيمة الخصم', digits='Product Price')
    service_amount = fields.Monetary(compute='_compute_workshop_amounts', currency_field='currency_id')
    parts_amount = fields.Monetary(compute='_compute_workshop_amounts', currency_field='currency_id')
    amount_untaxed = fields.Monetary(compute='_compute_workshop_amounts', currency_field='currency_id')
    discount_amount = fields.Monetary(compute='_compute_workshop_amounts', currency_field='currency_id')
    amount_tax = fields.Monetary(compute='_compute_workshop_amounts', currency_field='currency_id')
    amount_total = fields.Monetary(compute='_compute_workshop_amounts', currency_field='currency_id')

    @api.constrains('discount_type', 'discount_value')
    def _check_discount(self):
        for order in self:
            if order.discount_value < 0 or (order.discount_type == 'percent' and order.discount_value > 100):
                raise ValidationError(_('الخصم يجب أن يكون غير سالب، والنسبة لا تتجاوز 100%.'))

    @api.depends(
        'sale_line_ids', 'sale_line_ids.product_uom_qty',
        'sale_line_ids.price_unit', 'sale_line_ids.product_id',
        'service_line_ids', 'service_line_ids.product_uom_qty',
        'service_line_ids.price_unit', 'service_line_ids.product_id',
        'part_line_ids', 'part_line_ids.product_uom_qty',
        'part_line_ids.price_unit', 'part_line_ids.product_id',
        'discount_type', 'discount_value', 'company_id', 'partner_id',
    )
    def _compute_workshop_amounts(self):
        for order in self:
            services = sum(order.sale_line_ids.filtered(lambda l: l.product_id.type == 'service').mapped('line_subtotal'))
            parts = sum(order.sale_line_ids.filtered(lambda l: l.product_id.type in ('product', 'consu')).mapped('line_subtotal'))
            untaxed = sum(order.sale_line_ids.mapped('line_subtotal'))
            order.service_amount = services
            order.parts_amount = parts
            discount = min(untaxed, untaxed * order.discount_value / 100.0 if order.discount_type == 'percent' else order.discount_value)
            settings = self.env['yt.workshop.finance.settings'].search([('company_id', '=', order.company_id.id)], limit=1)
            tax = 0.0
            if untaxed:
                for line in order.sale_line_ids:
                    taxes = settings.tax_id if settings.tax_id else line.product_id.taxes_id.filtered(lambda t: t.company_id == order.company_id)
                    if taxes:
                        base = line.line_subtotal * (untaxed - discount) / untaxed
                        result = taxes.compute_all(base / line.product_uom_qty, currency=order.currency_id, quantity=line.product_uom_qty, product=line.product_id, partner=order.partner_id)
                        tax += result['total_included'] - result['total_excluded']
            order.amount_untaxed = untaxed
            order.discount_amount = discount
            order.amount_tax = tax
            order.amount_total = untaxed - discount + tax


    @api.onchange('service_line_ids', 'part_line_ids', 'discount_type', 'discount_value')
    def _onchange_workshop_totals(self):
        """Refresh KPI values for unsaved inline One2many changes."""
        self._compute_workshop_amounts()

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

    def _available_at_workshop_location(self, product):
        """Same company/location calculation for displayed stock and validation."""
        self.ensure_one()
        if not self.location_id or not product or product.type != 'product':
            return 0.0
        return product.with_company(self.company_id).with_context(
            location=self.location_id.id,
            allowed_company_ids=[self.company_id.id],
        ).free_qty

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
            free = self._available_at_workshop_location(product)
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
        warehouse = self._get_workshop_warehouse()
        # Sale confirmation sources inventory from the warehouse stock location.
        # Do not display stock from a different location as if it were saleable.
        if self.sale_line_ids.filtered(lambda l: l.product_id.type == 'product') and self.location_id != warehouse.lot_stock_id:
            raise UserError(_('موقع قطع الغيار (%s) لا يطابق موقع الصرف الأساسي للمستودع (%s). اختر موقع الصرف الصحيح قبل إنشاء أمر البيع، أو اضبط مسار المخزون للمستودع.') % (self.location_id.display_name, warehouse.lot_stock_id.display_name))
        lines = []
        untaxed = sum(self.sale_line_ids.mapped('line_subtotal'))
        discount = min(untaxed, untaxed * self.discount_value / 100.0 if self.discount_type == 'percent' else self.discount_value)
        for line in self.sale_line_ids:
            product = line.product_id.with_company(self.company_id)
            if not product.sale_ok:
                raise UserError(_('الصنف %s غير متاح للبيع.') % product.display_name)
            settings = self.env['yt.workshop.finance.settings'].search([('company_id', '=', self.company_id.id)], limit=1)
            taxes = settings.tax_id if settings.tax_id else product.taxes_id.filtered(lambda t: t.company_id == self.company_id)
            lines.append((0, 0, {
                'product_id': product.id,
                'name': line.name,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': product.uom_id.id,
                'price_unit': line.price_unit * (1 - discount / untaxed) if untaxed else line.price_unit,
                'tax_id': [(6, 0, taxes.ids)],
            }))
        so = self.env['sale.order'].with_company(self.company_id).create({
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'client_order_ref': self.name,
            'origin': self.name,
            'warehouse_id': warehouse.id,
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

    def action_open_workshop(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('أمر العمل'),
                'res_model': 'yt.reception.order', 'view_mode': 'form',
                'views': [(self.env.ref('yousentech_car_maintain.view_reception_workshop_form').id, 'form')],
                'res_id': self.id, 'target': 'current'}


class WorkshopFinanceSettings(models.Model):
    _name = 'yt.workshop.finance.settings'
    _description = 'Workshop financial configuration'
    _rec_name = 'name'

    name = fields.Char(default='الإعدادات المالية للورشة', required=True, readonly=True)
    tax_id = fields.Many2one('account.tax', string='ضريبة المبيعات المعتمدة',
                             domain="[('type_tax_use','=','sale')]")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company,
                                 required=True, readonly=True)
    _sql_constraints = [('one_per_company', 'unique(company_id)', 'يوجد سجل إعدادات مالية لهذه الشركة بالفعل.')]

    @api.model
    def action_open_settings(self):
        company = self.env.company
        record = self.search([('company_id', '=', company.id)], limit=1)
        if not record:
            record = self.create({'company_id': company.id})
        return {'type': 'ir.actions.act_window', 'name': _('إعدادات الورشة المالية'),
                'res_model': self._name, 'view_mode': 'form',
                'res_id': record.id, 'target': 'current'}
