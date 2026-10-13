from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class WorkshopSaleLine(models.Model):
    _name = 'yt.reception.sale.line'
    _description = 'Workshop billable service or spare part'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    inspection_category_id = fields.Many2one('yt.inspection.category', string='تصنيف الفحص', readonly=True, copy=False, ondelete='restrict')
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

    workshop_approved = fields.Boolean(string='أمر العمل معتمد', readonly=True, copy=False, tracking=True)

    finance_invoice_ids = fields.Many2many(
        'account.move', compute='_compute_workshop_finance',
        string='الفواتير والإشعارات الدائنة')
    finance_payment_ids = fields.Many2many(
        'account.payment', compute='_compute_workshop_finance',
        string='الدفعات')
    finance_invoiced = fields.Monetary(compute='_compute_workshop_finance', currency_field='currency_id')
    finance_credited = fields.Monetary(compute='_compute_workshop_finance', currency_field='currency_id')
    finance_received = fields.Monetary(compute='_compute_workshop_finance', currency_field='currency_id')
    finance_refunded = fields.Monetary(compute='_compute_workshop_finance', currency_field='currency_id')
    finance_due = fields.Monetary(compute='_compute_workshop_finance', currency_field='currency_id')
    finance_to_refund = fields.Monetary(compute='_compute_workshop_finance', currency_field='currency_id')
    cancel_reason = fields.Text(string='سبب الإلغاء', readonly=True, copy=False)

    def _workshop_financial_documents(self):
        self.ensure_one()
        sale = self.sale_order_id
        invoices = sale.invoice_ids.filtered(
            lambda move: move.move_type in ('out_invoice', 'out_refund'))
        # Include credit notes created from the invoice reversal wizard even
        # when the sale order invoice relation does not expose them.
        refunds = self.env['account.move'].search([
            ('reversed_entry_id', 'in', invoices.filtered(
                lambda move: move.move_type == 'out_invoice').ids),
            ('move_type', '=', 'out_refund'),
            ('company_id', '=', self.company_id.id),
        ]) if invoices else self.env['account.move']
        return invoices | refunds

    @api.depends('sale_order_id.invoice_ids', 'advance_payment_ids',
                 'advance_payment_ids.state', 'advance_payment_ids.amount')
    def _compute_workshop_finance(self):
        for order in self:
            moves = order._workshop_financial_documents()
            posted = moves.filtered(lambda move: move.state == 'posted')
            payments = order.advance_payment_ids
            for move in posted:
                payments |= move._get_reconciled_payments()
            payments = payments.filtered(
                lambda p: p.state == 'posted' and p.company_id == order.company_id
                and p.partner_id == order.partner_id)
            received = sum(
                p.currency_id._convert(p.amount, order.currency_id,
                    order.company_id, p.date)
                for p in payments.filtered(lambda p: p.payment_type == 'inbound'))
            refunded = sum(
                p.currency_id._convert(p.amount, order.currency_id,
                    order.company_id, p.date)
                for p in payments.filtered(lambda p: p.payment_type == 'outbound'))
            invoiced = sum(posted.filtered(
                lambda move: move.move_type == 'out_invoice').mapped('amount_total'))
            credited = sum(posted.filtered(
                lambda move: move.move_type == 'out_refund').mapped('amount_total'))
            balance = invoiced - credited - received + refunded
            order.finance_invoice_ids = moves
            order.finance_payment_ids = payments
            order.finance_invoiced = invoiced
            order.finance_credited = credited
            order.finance_received = received
            order.finance_refunded = refunded
            order.finance_due = max(balance, 0)
            order.finance_to_refund = max(-balance, 0)

    def _check_finance_before_cancel(self):
        for order in self:
            moves = order._workshop_financial_documents()
            if moves.filtered(lambda move: move.state == 'draft'):
                raise UserError(_('لا يمكن إلغاء أمر العمل مع وجود فاتورة أو إشعار دائن مسودة. عالج المستندات أولاً.'))
            order._compute_workshop_finance()
            if not order.currency_id.is_zero(order.finance_invoiced - order.finance_credited):
                raise UserError(_('لا يمكن الإلغاء قبل معالجة صافي الفواتير بإشعارات دائنة.'))
            if not order.currency_id.is_zero(order.finance_received - order.finance_refunded):
                raise UserError(_('لا يمكن الإلغاء قبل رد كامل المبالغ المقبوضة من العميل.'))
            unsettled = moves.filtered(
                lambda move: move.state == 'posted'
                and not order.currency_id.is_zero(move.amount_residual))
            if unsettled:
                raise UserError(_('يجب تسوية الفواتير والإشعارات الدائنة المرحلة قبل الإلغاء.'))
            if order.sale_order_id and order.sale_order_id.picking_ids.filtered(
                lambda picking: picking.state == 'done'):
                raise UserError(_('يوجد صرف مخزني منفذ؛ عالج مرتجع المخزون قبل إلغاء أمر العمل.'))

    def action_cancel(self):
        for order in self:
            order._check_finance_before_cancel()
        return {
            'type': 'ir.actions.act_window',
            'name': _('إلغاء أمر العمل'),
            'res_model': 'yt.workshop.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.ensure_one().id},
        }

    def action_create_workshop_credit_note(self):
        self.ensure_one()
        invoices = self._workshop_financial_documents().filtered(
            lambda move: move.move_type == 'out_invoice' and move.state == 'posted')
        if not invoices:
            raise UserError(_('لا توجد فاتورة مرحلة لإنشاء إشعار دائن.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('إنشاء إشعار دائن'),
            'res_model': 'account.move.reversal',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_model': 'account.move', 'active_ids': invoices.ids,
                        'default_reason': _('تسوية أمر العمل %s') % self.name},
        }

    def action_approve_workshop(self):
        for order in self:
            if order.state == 'cancelled':
                raise UserError(_('لا يمكن اعتماد أمر عمل ملغي.'))
            if not order.sale_line_ids:
                raise UserError(_('أضف خدمة أو قطعة غيار قبل الاعتماد.'))
            order.workshop_approved = True
        return True

    advance_payment_ids = fields.Many2many(
        'account.payment', 'yt_workshop_advance_payment_rel',
        'order_id', 'payment_id', string='دفعات أمر العمل', copy=False, readonly=True)
    payment_count = fields.Integer(compute='_compute_workshop_payment_count')

    @api.depends('advance_payment_ids')
    def _compute_workshop_payment_count(self):
        for order in self:
            order.payment_count = len(order.advance_payment_ids)

    def action_register_workshop_payment(self):
        """Register an invoice payment using Odoo's native payment wizard."""
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError(_('لا يمكن تسجيل دفعة لأمر ملغي.'))
        invoices = self._workshop_financial_documents().filtered(
            lambda move: move.state == 'posted'
            and move.move_type == 'out_invoice'
            and move.amount_residual > 0
            and move.company_id == self.company_id
        )
        if not invoices:
            raise UserError(_(
                'لا توجد فاتورة مرحلة بمبلغ مستحق. '
                'لتسجيل مبلغ قبل إصدار الفاتورة استخدم زر دفعة مقدمة.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('تسجيل دفعة فاتورة'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': invoices.ids,
                'active_id': invoices[0].id,
                'allowed_company_ids': [self.company_id.id],
            },
        }

    def action_register_workshop_advance(self):
        """Collect an advance before invoicing without a fake invoice."""
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError(_('لا يمكن تسجيل دفعة لأمر ملغي.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('تسجيل دفعة مقدمة'),
            'res_model': 'yt.workshop.advance.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            },
        }

    def action_open_workshop_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('دفعات أمر العمل'),
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.advance_payment_ids.ids)],
            'context': {'create': False},
        }

    def action_reconcile_workshop_advances(self):
        self.ensure_one()
        invoices = self.invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and inv.move_type == 'out_invoice'
            and inv.amount_residual > 0)
        if not invoices:
            raise UserError(_('يجب ترحيل فاتورة مستحقة أولاً لتسوية الدفعات المقدمة.'))
        payments = self.advance_payment_ids.filtered(
            lambda p: p.state == 'posted' and p.payment_type == 'inbound'
            and p.partner_id == self.partner_id and p.company_id == self.company_id)
        if not payments:
            raise UserError(_('لا توجد دفعات مقدمة مرحلة قابلة للتسوية.'))
        invoice_lines = invoices.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
        payment_lines = payments.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled)
        reconciled = False
        for account in (invoice_lines | payment_lines).mapped('account_id'):
            lines = (invoice_lines | payment_lines).filtered(lambda l: l.account_id == account)
            if lines.filtered(lambda l: l.debit > 0) and lines.filtered(lambda l: l.credit > 0):
                lines.reconcile()
                reconciled = True
        if not reconciled:
            raise UserError(_('لا توجد قيود مدينة ودائنة متطابقة في حساب ذمم العميل للتسوية.'))
        return self.action_open_workshop_invoices()

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
            # The editable service/part widgets may contain unsaved NewId lines
            # that are not yet present in the inverse sale_line_ids cache.
            # Compute from the visible collections and keep persisted lines
            # from sale_line_ids only when they are not already represented.
            lines = order.service_line_ids | order.part_line_ids
            lines |= order.sale_line_ids.filtered(lambda line: line not in lines)
            services = sum(
                line.product_uom_qty * line.price_unit for line in lines
                if line.product_id.type == 'service'
            )
            parts = sum(
                line.product_uom_qty * line.price_unit for line in lines
                if line.product_id.type in ('product', 'consu')
            )
            untaxed = sum(line.product_uom_qty * line.price_unit for line in lines)
            order.service_amount = services
            order.parts_amount = parts
            discount = min(
                untaxed,
                untaxed * order.discount_value / 100.0
                if order.discount_type == 'percent' else order.discount_value,
            )
            settings = self.env['yt.workshop.finance.settings'].search(
                [('company_id', '=', order.company_id.id)], limit=1,
            )
            tax = 0.0
            if untaxed:
                for line in lines:
                    if not line.product_id or not line.product_uom_qty:
                        continue
                    taxes = settings.tax_id if settings.tax_id else line.product_id.taxes_id.filtered(
                        lambda t: t.company_id == order.company_id
                    )
                    if taxes:
                        base = (line.product_uom_qty * line.price_unit) * (untaxed - discount) / untaxed
                        result = taxes.compute_all(
                            base / line.product_uom_qty,
                            currency=order.currency_id,
                            quantity=line.product_uom_qty,
                            product=line.product_id,
                            partner=order.partner_id,
                        )
                        tax += result['total_included'] - result['total_excluded']
            order.amount_untaxed = untaxed
            order.discount_amount = discount
            order.amount_tax = tax
            order.amount_total = untaxed - discount + tax

    @api.onchange('service_line_ids', 'part_line_ids', 'sale_line_ids', 'discount_type', 'discount_value')
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
        if not product or product.detailed_type != 'product':
            return 0.0
        warehouse = self._get_workshop_warehouse()
        location = self._workshop_source_location(warehouse)
        quants = self.env['stock.quant'].with_company(self.company_id).search([
            ('product_id', '=', product.id),
            ('location_id', '=', location.id),
            ('warehouse_id', '=', warehouse.id),
        ])
        return sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))

    @api.model
    def _workshop_default_warehouse(self, company):
        config = self.env['res.user.inventory.config'].search([
            ('user_id', '=', self.env.uid), ('company_id', '=', company.id),
            ('operation_type', '=', 'outgoing')], limit=1)
        warehouse = config.default_warehouse_id or company.default_warehouse_id
        if not warehouse or warehouse.company_id != company:
            raise UserError(_('حدد مستودع المبيعات الافتراضي للمستخدم أو الشركة أولاً.'))
        if config.allowed_warehouse_ids and warehouse not in config.allowed_warehouse_ids:
            raise UserError(_('المستودع الافتراضي غير مسموح للمستخدم.'))
        return warehouse

    def _workshop_source_location(self, warehouse):
        self.ensure_one()
        config = self.env['res.user.inventory.config'].search([
            ('user_id', '=', self.env.uid),
            ('company_id', '=', self.company_id.id),
            ('operation_type', '=', 'outgoing'),
        ], limit=1)
        picking_type = config.picking_type_id if config.picking_type_id and config.picking_type_id.warehouse_id == warehouse and config.picking_type_id.code == 'outgoing' else warehouse.out_type_id
        return picking_type.default_location_src_id or warehouse.lot_stock_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('location_id'):
                company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
                warehouse = self._workshop_default_warehouse(company)
                config = self.env['res.user.inventory.config'].search([
                    ('user_id', '=', self.env.uid), ('company_id', '=', company.id),
                    ('operation_type', '=', 'outgoing')], limit=1)
                picking_type = config.picking_type_id if config.picking_type_id and config.picking_type_id.warehouse_id == warehouse and config.picking_type_id.code == 'outgoing' else warehouse.out_type_id
                vals['location_id'] = (picking_type.default_location_src_id or warehouse.lot_stock_id).id
        return super().create(vals_list)

    @api.onchange('company_id')
    def _onchange_workshop_company_location(self):
        for order in self:
            if order.company_id:
                warehouse = order._workshop_default_warehouse(order.company_id)
                order.location_id = order._workshop_source_location(warehouse)

    def _check_part_availability(self):
        self.ensure_one()
        warehouse = self._get_workshop_warehouse()
        location = self._workshop_source_location(warehouse)
        if self.location_id and self.location_id != location:
            raise UserError(_('موقع قطع الغيار يجب أن يطابق موقع صرف المستودع المعتمد.'))
        user = self.env.user
        policy = user.has_group('yousentech_inventory_minus_quantity.group_prevent_selling_negative_value')
        exempt = user.override_negative_quantities and user.negative_quantity_type == 'all_orders'
        if not policy or exempt:
            return
        needed = {}
        for line in self.sale_line_ids:
            product = line.product_id
            if product.detailed_type != 'product' or product.categ_id.temp_categ_flag:
                continue
            qty = product.uom_id._compute_quantity(line.product_uom_qty, product.uom_id)
            needed[product] = needed.get(product, 0.0) + qty
        for product, qty in needed.items():
            quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id), ('location_id', '=', location.id),
                ('warehouse_id', '=', warehouse.id)])
            reserved = sum(quants.mapped('reserved_quantity'))
            product.validate_product_quentity(qty, reserved, warehouse.id, location.ids)

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
        warehouse = self._get_workshop_warehouse()
        if not self.location_id:
            self.location_id = self._workshop_source_location(warehouse)
        self._check_part_availability()
        # Sale confirmation sources inventory from the warehouse stock location.
        # Do not display stock from a different location as if it were saleable.
        if self.sale_line_ids.filtered(lambda l: l.product_id.type == 'product') and self.location_id != self._workshop_source_location(warehouse):
            raise UserError(_('موقع قطع الغيار (%s) لا يطابق موقع الصرف الأساسي للمستودع (%s). اختر موقع الصرف الصحيح قبل إنشاء أمر البيع، أو اضبط مسار المخزون للمستودع.') % (self.location_id.display_name, self._workshop_source_location(warehouse).display_name))
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
        so_vals = {
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'client_order_ref': self.name,
            'origin': self.name,
            'warehouse_id': warehouse.id,
            'order_line': lines,
        }
        if 'picking_type_id' in self.env['sale.order']._fields:
            config = self.env['res.user.inventory.config'].search([
                ('user_id', '=', self.env.uid), ('company_id', '=', self.company_id.id),
                ('operation_type', '=', 'outgoing')], limit=1)
            picking_type = config.picking_type_id if config.picking_type_id and config.picking_type_id.warehouse_id == warehouse and config.picking_type_id.code == 'outgoing' else warehouse.out_type_id
            so_vals['picking_type_id'] = picking_type.id
        so = self.env['sale.order'].with_company(self.company_id).create(so_vals)
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
        return self._workshop_default_warehouse(self.company_id)

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


class WorkshopAdvancePaymentWizard(models.TransientModel):
    _name = 'yt.workshop.advance.payment.wizard'
    _description = 'تسجيل دفعة مقدمة لأمر العمل'

    order_id = fields.Many2one('yt.reception.order', required=True, readonly=True)
    company_id = fields.Many2one('res.company', related='order_id.company_id', readonly=True)
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', readonly=True)
    journal_id = fields.Many2one('account.journal', string='الصندوق / البنك', required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]")
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line', string='طريقة الدفع', required=True,
        domain="[('id', 'in', available_payment_method_line_ids)]")
    available_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line', compute='_compute_available_payment_methods')
    amount = fields.Monetary(string='المبلغ', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    payment_date = fields.Date(string='تاريخ الدفعة', default=fields.Date.context_today, required=True)
    memo = fields.Char(string='البيان')

    @api.depends('journal_id')
    def _compute_available_payment_methods(self):
        for wizard in self:
            wizard.available_payment_method_line_ids = wizard.journal_id.inbound_payment_method_line_ids

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        for wizard in self:
            available = wizard.journal_id.inbound_payment_method_line_ids
            if wizard.payment_method_line_id not in available:
                wizard.payment_method_line_id = available[:1] if len(available) == 1 else False

    def action_confirm_advance(self):
        self.ensure_one()
        order = self.order_id
        if order.state == 'cancelled':
            raise UserError(_('لا يمكن تسجيل دفعة لأمر ملغي.'))
        if self.amount <= 0:
            raise ValidationError(_('مبلغ الدفعة يجب أن يكون أكبر من صفر.'))
        if self.journal_id.company_id != order.company_id:
            raise ValidationError(_('يجب اختيار صندوق أو بنك تابع لشركة أمر العمل.'))
        method = self.payment_method_line_id
        if not method or method not in self.journal_id.inbound_payment_method_line_ids:
            raise ValidationError(_('اختر طريقة دفع واردة صالحة للصندوق أو البنك المحدد.'))
        payment = self.env['account.payment'].with_company(order.company_id).create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': order.partner_id.id,
            'amount': self.amount,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'payment_method_line_id': method.id,
            'ref': self.memo or _('دفعة مقدمة لأمر العمل %s') % order.name,
        })
        payment.action_post()
        order.write({'advance_payment_ids': [(4, payment.id)]})
        return {'type': 'ir.actions.act_window_close'}

class WorkshopCancelWizard(models.TransientModel):
    _name = 'yt.workshop.cancel.wizard'
    _description = 'Workshop Cancellation Confirmation'

    order_id = fields.Many2one('yt.reception.order', required=True, readonly=True)
    reason = fields.Text(string='سبب الإلغاء', required=True)

    def action_confirm_cancel(self):
        self.ensure_one()
        order = self.order_id
        order._check_finance_before_cancel()
        order.write({'state': 'cancelled', 'cancel_reason': self.reason})
        order.message_post(body=_('تم إلغاء أمر العمل. السبب: %s') % self.reason)
        return {'type': 'ir.actions.act_window_close'}
