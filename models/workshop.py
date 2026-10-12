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
    make = fields.Char(string='الشركة المصنعة (قديم)')
    model = fields.Char(string='الموديل (قديم)')
    make_id = fields.Many2one('ycm.v2.vehicle.make', string='الشركة المصنعة', ondelete='restrict', index=True)
    model_id = fields.Many2one('ycm.v2.vehicle.model', string='الموديل', ondelete='restrict', index=True, domain="[('make_id', '=', make_id)]")
    year = fields.Integer()
    transmission = fields.Selection([('automatic', 'أوتوماتيك'), ('manual', 'عادي'), ('cvt', 'CVT'), ('other', 'أخرى')], string='نوع الجير')
    color = fields.Char(string='اللون')
    engine_number = fields.Char(string='رقم المحرك')
    order_ids = fields.One2many('ycm.v2.order', 'vehicle_id', string='أوامر العمل')
    order_count = fields.Integer(compute='_compute_order_count', string='عدد أوامر العمل')

    def _compute_order_count(self):
        counts = self.env['ycm.v2.order'].read_group(
            [('vehicle_id', 'in', self.ids)], ['vehicle_id'], ['vehicle_id'])
        mapping = {row['vehicle_id'][0]: row['vehicle_id_count'] for row in counts}
        for vehicle in self:
            vehicle.order_count = mapping.get(vehicle.id, 0)

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Vehicle work orders'),
            'res_model': 'ycm.v2.order', 'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id, 'default_partner_id': self.partner_id.id},
        }
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
        if vals.get('model_id') and 'make_id' not in vals:
            model = self.env['ycm.v2.vehicle.model'].browse(vals['model_id']).exists()
            if model:
                vals['make_id'] = model.make_id.id
        if vals.get('make_id') and 'model_id' not in vals and self:
            # Never silently retain a model belonging to another manufacturer.
            if any(vehicle.model_id and vehicle.model_id.make_id.id != vals['make_id'] for vehicle in self):
                vals['model_id'] = False
        if 'make_id' in vals:
            make = self.env['ycm.v2.vehicle.make'].browse(vals['make_id']).exists() if vals['make_id'] else False
            vals['make'] = make.name if make else False
        if 'model_id' in vals:
            model = self.env['ycm.v2.vehicle.model'].browse(vals['model_id']).exists() if vals['model_id'] else False
            vals['model'] = model.name if model else False
        for key in ('plate_number', 'vin'):
            if vals.get(key):
                vals[key] = ''.join(vals[key].strip().upper().split()) if key == 'vin' else ' '.join(vals[key].strip().upper().split())
        return vals

    @api.constrains('vin')
    def _check_vin(self):
        for vehicle in self:
            if vehicle.vin and (len(vehicle.vin) != 17 or any(x in vehicle.vin for x in 'IOQ')):
                raise ValidationError(_('VIN must contain 17 characters excluding I/O/Q.'))

    @api.onchange('make_id')
    def _onchange_make_id(self):
        if self.model_id and self.model_id.make_id != self.make_id:
            self.model_id = False

    @api.constrains('make_id', 'model_id')
    def _check_make_model(self):
        for vehicle in self:
            if vehicle.model_id and vehicle.model_id.make_id != vehicle.make_id:
                raise ValidationError(_('The vehicle model must belong to the selected manufacturer.'))

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
            'makes': self.env['ycm.v2.vehicle.make'].search([('active', '=', True)]).read(['name']),
            'models': self.env['ycm.v2.vehicle.model'].search([('active', '=', True), ('make_id.active', '=', True)]).read(['name', 'make_id']),
            'vehicles': self.env['ycm.v2.vehicle'].search([('company_id', '=', company.id)], limit=200).read(['plate_number', 'partner_id', 'make', 'model', 'year', 'odometer']),
            'products': Product.search([('sale_ok', '=', True)], limit=200).read(['display_name', 'list_price', 'detailed_type']),
            'currency': company.currency_id.symbol,
        }

    @api.model
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
    def ui_save_diagnosis(self, order_id, diagnosis):
        order = self.browse(int(order_id)).exists()
        if not order:
            raise UserError(_('Work order not found.'))
        order.check_access_rule('write')
        order.check_access_rights('write')
        if order.state not in ('draft', 'estimate'):
            raise UserError(_('Inspection notes are locked after approval.'))
        if not isinstance(diagnosis, str) or len(diagnosis) > 10000:
            raise UserError(_('Invalid inspection notes.'))
        order.write({'diagnosis': diagnosis})
        return True

    @api.model
    def ui_register_vehicle(self, customer_id, vehicle_data):
        """Create a customer-owned vehicle from intake without bypassing ORM rules."""
        self.check_access_rights('create')
        Vehicle = self.env['ycm.v2.vehicle']
        Vehicle.check_access_rights('create')
        customer = self.env['res.partner'].browse(int(customer_id)).exists()
        if not customer:
            raise UserError(_('Select a valid customer.'))
        customer.check_access_rule('read')
        allowed = {
            'plate_number', 'plate_country', 'plate_type', 'vin',
            'make_id', 'model_id', 'year', 'transmission', 'color', 'engine_number', 'odometer',
        }
        vals = {key: value for key, value in (vehicle_data or {}).items() if key in allowed}
        if not vals.get('plate_number') or not str(vals['plate_number']).strip():
            raise UserError(_('Plate number is required.'))
        matches = Vehicle.find_existing_vehicle(
            vals['plate_number'], vals.get('vin'),
            vals.get('plate_country') or 'SA',
            vals.get('plate_type') or 'private',
        )
        if matches:
            existing = matches[0]
            if existing['partner_id'][0] == customer.id:
                raise UserError(_('This vehicle already exists for this customer. Select it from the list.'))
            raise UserError(_('This vehicle belongs to another customer. Ownership transfer must be handled separately.'))
        if not vals.get('make_id') or not vals.get('model_id'):
            raise UserError(_('Select manufacturer and model.'))
        make = self.env['ycm.v2.vehicle.make'].browse(int(vals['make_id'])).exists()
        model = self.env['ycm.v2.vehicle.model'].browse(int(vals['model_id'])).exists()
        if not make or not model or not make.active or not model.active or model.make_id != make:
            raise UserError(_('Invalid manufacturer/model combination.'))
        vals['make_id'] = make.id
        vals['model_id'] = model.id
        vals.update({'partner_id': customer.id, 'company_id': self.env.company.id})
        return Vehicle.create(vals).id

    @api.model
    def ui_create(self, customer_id, vehicle_id, complaint=''):
        self.check_access_rights('create')
        vehicle = self.env['ycm.v2.vehicle'].browse(int(vehicle_id)).exists()
        customer = self.env['res.partner'].browse(int(customer_id)).exists()
        if not vehicle or not customer:
            raise UserError(_('Select a valid customer and vehicle.'))
        vehicle.check_access_rule('read')
        if vehicle.company_id != self.env.company:
            raise UserError(_('The vehicle belongs to another company.'))
        if vehicle.partner_id != customer:
            raise UserError(_('The selected vehicle does not belong to this customer.'))
        order = self.create({
            'company_id': vehicle.company_id.id,
            'partner_id': customer.id,
            'vehicle_id': vehicle.id,
            'complaint': complaint,
        })
        return order.id

    def ui_add_line(self, product_id, kind, quantity=1):
        self.ensure_one()
        product = self.env['product.product'].browse(product_id).exists()
        if self.state not in ('draft', 'estimate'):
            raise UserError(_('The work order is locked.'))
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
