from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class WorkshopV2Vehicle(models.Model):
    _name = 'ycm.v2.vehicle'
    _description = 'Workshop V2 Vehicle'
    _order = 'id desc'
    _rec_name = 'plate_number'

    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company, index=True)
    partner_id = fields.Many2one('res.partner', required=True, index=True, ondelete='restrict')
    plate_number = fields.Char(required=True, index=True)
    vin = fields.Char(index=True)
    make = fields.Char()
    model = fields.Char()
    year = fields.Integer()
    odometer = fields.Float()
    active = fields.Boolean(default=True)

    _sql_constraints = [('vin_company_unique', 'unique(vin, company_id)', 'VIN already exists in this company.'),
                        ('odometer_nonnegative', 'CHECK(odometer >= 0)', 'Odometer must be positive.')]

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([self._normalize_vals(vals) for vals in vals_list])

    def write(self, vals):
        return super().write(self._normalize_vals(vals))

    @api.model
    def _normalize_vals(self, vals):
        vals = dict(vals)
        for key in ('plate_number', 'vin'):
            if vals.get(key):
                vals[key] = ''.join(vals[key].strip().upper().split()) if key == 'vin' else ' '.join(vals[key].strip().upper().split())
        return vals

    @api.constrains('vin')
    def _check_vin(self):
        for vehicle in self:
            if vehicle.vin and (len(vehicle.vin) != 17 or any(x in vehicle.vin for x in 'IOQ')):
                raise ValidationError(_('VIN must contain 17 characters excluding I/O/Q.'))

    @api.constrains('year', 'plate_number')
    def _check_vehicle(self):
        for vehicle in self:
            if not vehicle.plate_number or not vehicle.plate_number.strip():
                raise ValidationError(_('Plate is required.'))
            if vehicle.year and not 1886 <= vehicle.year <= fields.Date.today().year + 2:
                raise ValidationError(_('Invalid vehicle year.'))


class WorkshopV2Order(models.Model):
    _name = 'ycm.v2.order'
    _description = 'Workshop V2 Work Order'
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(default='New', required=True, readonly=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company, index=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    partner_id = fields.Many2one('res.partner', required=True, index=True)
    vehicle_id = fields.Many2one('ycm.v2.vehicle', required=True, check_company=True, ondelete='restrict')
    odometer_in = fields.Float()
    complaint = fields.Text()
    diagnosis = fields.Text()
    advisor_id = fields.Many2one('res.users', default=lambda s: s.env.user)
    promised_at = fields.Datetime()
    state = fields.Selection([
        ('draft', 'استقبال'), ('estimate', 'تقدير'), ('approved', 'معتمد'),
        ('in_progress', 'قيد التنفيذ'), ('completed', 'مكتمل فنيًا'),
        ('cancelled', 'ملغي'),
    ], default='draft', required=True, index=True, copy=False)
    line_ids = fields.One2many('ycm.v2.order.line', 'order_id', string='Services and parts', copy=True)
    amount_untaxed = fields.Monetary(compute='_compute_amounts', currency_field='currency_id')
    amount_tax = fields.Monetary(compute='_compute_amounts', currency_field='currency_id')
    amount_total = fields.Monetary(compute='_compute_amounts', currency_field='currency_id')

    @api.depends('line_ids.price_subtotal', 'line_ids.price_tax', 'line_ids.price_total')
    def _compute_amounts(self):
        for order in self:
            order.amount_untaxed = sum(order.line_ids.mapped('price_subtotal'))
            order.amount_tax = sum(order.line_ids.mapped('price_tax'))
            order.amount_total = sum(order.line_ids.mapped('price_total'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('ycm.v2.order') or 'New'
        return super().create(vals_list)

    @api.constrains('vehicle_id', 'partner_id', 'company_id', 'odometer_in')
    def _validate_identity(self):
        for order in self:
            if order.vehicle_id.partner_id != order.partner_id or order.vehicle_id.company_id != order.company_id:
                raise ValidationError(_('The vehicle must belong to this customer and company.'))
            if order.odometer_in < 0:
                raise ValidationError(_('Odometer cannot be negative.'))

    def write(self, vals):
        if any(field in vals for field in ('partner_id', 'vehicle_id', 'company_id', 'line_ids', 'complaint', 'diagnosis', 'odometer_in')):
            if any(order.state not in ('draft', 'estimate') for order in self):
                raise UserError(_('An approved work order is locked for editing.'))
        if 'state' in vals and not self.env.context.get('ycm_v2_transition'):
            raise UserError(_('Use the workflow action to change status.'))
        return super().write(vals)

    def action_transition(self, new_state):
        allowed = {
            'draft': {'estimate', 'cancelled'},
            'estimate': {'approved', 'draft', 'cancelled'},
            'approved': {'in_progress', 'cancelled'},
            'in_progress': {'completed'},
        }
        for order in self:
            if new_state not in allowed.get(order.state, set()):
                raise UserError(_('Invalid work order transition.'))
            if new_state in ('approved', 'in_progress', 'completed') and not order.line_ids:
                raise UserError(_('Add at least one service or part.'))
            if new_state == 'completed' and any(l.qty <= 0 for l in order.line_ids):
                raise UserError(_('All items require positive quantities.'))
            order.with_context(ycm_v2_transition=True).write({'state': new_state})
        return True

    @api.model
    def ui_bootstrap(self):
        self.check_access_rights('read')
        company = self.env.company
        orders = self.search([('company_id', '=', company.id)], limit=80)
        Order = self.env['ycm.v2.order']
        Product = self.env['product.product']
        fields_to_read = ['name', 'partner_id', 'vehicle_id', 'state', 'complaint', 'diagnosis', 'odometer_in',
                          'promised_at', 'amount_untaxed', 'amount_tax', 'amount_total', 'line_ids']
        return {
            'orders': orders.read(fields_to_read),
            'customers': self.env['res.partner'].search([('active', '=', True), ('customer_rank', '>', 0)], limit=150).read(['name', 'phone']),
            'vehicles': self.env['ycm.v2.vehicle'].search([('company_id', '=', company.id)], limit=200).read(['plate_number', 'partner_id', 'make', 'model', 'year', 'odometer']),
            'products': Product.search([('sale_ok', '=', True)], limit=200).read(['display_name', 'list_price', 'detailed_type']),
            'currency': company.currency_id.symbol,
        }

    def ui_detail(self, order_id):
        order = self.browse(order_id).exists()
        if not order:
            raise UserError(_('Work order not found.'))
        order.check_access_rule('read')
        return {
            'order': order.read(['name', 'partner_id', 'vehicle_id', 'state', 'complaint', 'diagnosis', 'odometer_in',
                                  'promised_at', 'amount_untaxed', 'amount_tax', 'amount_total'])[0],
            'lines': order.line_ids.read(['kind', 'product_id', 'name', 'qty', 'price_unit', 'discount', 'price_subtotal', 'price_tax', 'price_total']),
        }

    @api.model
    def ui_create(self, customer_id, vehicle_id, complaint=''):
        order = self.create({'partner_id': customer_id, 'vehicle_id': vehicle_id, 'complaint': complaint})
        return order.id

    def ui_add_line(self, product_id, kind, quantity=1):
        self.ensure_one()
        product = self.env['product.product'].browse(product_id).exists()
        if not product or not product.sale_ok:
            raise UserError(_('Invalid catalog item.'))
        if kind not in ('service', 'part'):
            raise UserError(_('Invalid item kind.'))
        if kind == 'part' and product.detailed_type != 'product':
            raise UserError(_('Choose a storable product for parts.'))
        if kind == 'service' and product.detailed_type != 'service':
            raise UserError(_('Choose a service product.'))
        line = self.env['ycm.v2.order.line'].create({
            'order_id': self.id, 'kind': kind, 'product_id': product.id,
            'name': product.display_name, 'qty': quantity, 'price_unit': product.lst_price,
            'tax_ids': [(6, 0, product.taxes_id.filtered(lambda t: not t.company_id or t.company_id == self.company_id).ids)],
        })
        return line.id


class WorkshopV2OrderLine(models.Model):
    _name = 'ycm.v2.order.line'
    _description = 'Workshop V2 Service or Part'
    _order = 'sequence,id'
    _check_company_auto = True

    sequence = fields.Integer(default=10)
    order_id = fields.Many2one('ycm.v2.order', required=True, ondelete='cascade', check_company=True)
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id')
    kind = fields.Selection([('service', 'خدمة'), ('part', 'قطعة غيار')], required=True)
    product_id = fields.Many2one('product.product', required=True)
    name = fields.Char(required=True)
    qty = fields.Float(required=True, default=1)
    price_unit = fields.Monetary(required=True, currency_field='currency_id')
    discount = fields.Float(default=0)
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    price_subtotal = fields.Monetary(compute='_compute_amounts', currency_field='currency_id', store=True)
    price_tax = fields.Monetary(compute='_compute_amounts', currency_field='currency_id', store=True)
    price_total = fields.Monetary(compute='_compute_amounts', currency_field='currency_id', store=True)

    @api.constrains('qty', 'discount', 'price_unit', 'kind', 'product_id')
    def _validate_line(self):
        for line in self:
            if line.qty <= 0 or not 0 <= line.discount <= 100 or line.price_unit < 0:
                raise ValidationError(_('Invalid quantity, discount or price.'))
            expected = 'service' if line.kind == 'service' else 'product'
            if line.product_id.detailed_type != expected:
                raise ValidationError(_('Catalog product type does not match row type.'))

    @api.depends('qty', 'price_unit', 'discount', 'tax_ids', 'product_id', 'order_id.partner_id')
    def _compute_amounts(self):
        for line in self:
            unit = line.price_unit * (1 - line.discount / 100)
            tax = line.tax_ids.compute_all(unit, currency=line.currency_id, quantity=line.qty,
                                           product=line.product_id, partner=line.order_id.partner_id)
            line.price_subtotal = tax['total_excluded']
            line.price_total = tax['total_included']
            line.price_tax = line.price_total - line.price_subtotal

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order = self.env['ycm.v2.order'].browse(vals.get('order_id'))
            if order.state not in ('draft', 'estimate'):
                raise UserError(_('The work order is locked.'))
        return super().create(vals_list)

    def write(self, vals):
        if any(line.order_id.state not in ('draft', 'estimate') for line in self):
            raise UserError(_('The work order is locked.'))
        return super().write(vals)

    def unlink(self):
        if any(line.order_id.state not in ('draft', 'estimate') for line in self):
            raise UserError(_('The work order is locked.'))
        return super().unlink()
