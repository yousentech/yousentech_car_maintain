from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
import re

class WorkshopMake(models.Model):
    _name = 'yt.reception.make'
    _description = 'Vehicle Manufacturer'
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    _sql_constraints = [('make_unique', 'unique(name)', 'الشركة المصنعة موجودة مسبقاً.')]

class WorkshopModel(models.Model):
    _name = 'yt.reception.model'
    _description = 'Vehicle Model'
    name = fields.Char(required=True)
    make_id = fields.Many2one('yt.reception.make', required=True, ondelete='restrict')
    active = fields.Boolean(default=True)
    _sql_constraints = [('model_unique', 'unique(name,make_id)', 'الموديل موجود لهذه الشركة.')]

class WorkshopVehicle(models.Model):
    _name = 'yt.reception.vehicle'
    _description = 'Customer Vehicle'
    _rec_name = 'plate'
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict')
    plate = fields.Char(required=True)
    plate_country = fields.Char(default='SA', required=True)
    plate_type = fields.Selection([('private','خصوصي'),('commercial','تجاري'),('other','أخرى')], default='private', required=True)
    plate_condition = fields.Selection([('good','جيدة'),('damaged','متضررة')], default='good')
    make_id = fields.Many2one('yt.reception.make')
    model_id = fields.Many2one('yt.reception.model')
    year = fields.Integer()
    gear = fields.Selection([('auto','أوتوماتيك'),('manual','عادي')])
    vin = fields.Char()
    engine_number = fields.Char()
    odometer = fields.Float()
    color = fields.Char()
    _sql_constraints = [('vin_unique','unique(vin)','رقم الشاصي مسجل مسبقاً.'),('plate_unique','unique(company_id,plate_country,plate_type,plate)','هوية اللوحة مسجلة مسبقاً.')]
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('plate'):
                vals['plate'] = re.sub(r'[\s\-]+','',vals['plate']).upper()
            if vals.get('vin'):
                vals['vin'] = vals['vin'].strip().upper()
        return super().create(vals_list)
    @api.constrains('model_id','make_id','odometer','vin','year','plate')
    def _check_vehicle(self):
        for rec in self:
            if rec.model_id and rec.model_id.make_id != rec.make_id:
                raise ValidationError(_('الموديل لا يتبع الشركة المصنعة.'))
            if rec.odometer < 0:
                raise ValidationError(_('قراءة العداد غير صحيحة.'))
            if rec.year and not 1900 <= rec.year <= 2100:
                raise ValidationError(_('سنة صنع السيارة غير صحيحة.'))
            if rec.vin and (len(rec.vin) != 17 or re.search('[IOQ]',rec.vin) or not re.fullmatch('[A-HJ-NPR-Z0-9]{17}',rec.vin)):
                raise ValidationError(_('رقم الشاصي يجب أن يكون 17 خانة ولا يحتوي I أو O أو Q.'))
            if not rec.plate:
                raise ValidationError(_('رقم اللوحة مطلوب.'))

class ReceptionComplaint(models.Model):
    _name = 'yt.reception.complaint'
    _description = 'Customer Complaint'
    order_id = fields.Many2one('yt.reception.order', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    @api.constrains('name')
    def _nonempty(self):
        for rec in self:
            if not (rec.name or '').strip():
                raise ValidationError(_('لا يمكن حفظ شكوى فارغة.'))

class ReceptionRequest(models.Model):
    _name = 'yt.reception.request'
    _description = 'Requested Service at Reception'
    order_id = fields.Many2one('yt.reception.order', required=True, ondelete='cascade')
    name = fields.Char(required=True)

class ReceptionPhoto(models.Model):
    _name = 'yt.reception.photo'
    _description = 'Vehicle Reception Photo'
    order_id = fields.Many2one('yt.reception.order', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    data = fields.Binary(required=True, attachment=True)
    is_primary = fields.Boolean()
    mimetype = fields.Selection([('image/jpeg','JPEG'),('image/png','PNG')], required=True)
    @api.constrains('data','mimetype')
    def _validate_photo(self):
        import base64
        for rec in self:
            if rec.data:
                raw = base64.b64decode(rec.data)
                if len(raw) > 6*1024*1024:
                    raise ValidationError(_('حجم الصورة يجب أن لا يتجاوز 6 ميجابايت.'))
                if not ((rec.mimetype == 'image/jpeg' and raw.startswith(b'\xff\xd8\xff')) or (rec.mimetype == 'image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n'))):
                    raise ValidationError(_('يُسمح فقط بصور JPEG أو PNG صحيحة.'))

class ReceptionOrder(models.Model):
    _name = 'yt.reception.order'
    _description = 'Workshop Reception'
    _inherit = ['mail.thread']
    _order = 'id desc'
    name = fields.Char(default='/', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', required=True)
    vehicle_id = fields.Many2one('yt.reception.vehicle', required=True)
    arrival_at = fields.Datetime(required=True, default=fields.Datetime.now)
    odometer_in = fields.Float(required=True)
    odometer_out = fields.Float()
    branch_id = fields.Many2one('res.company', string='الفرع')
    advisor_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    reception_notes = fields.Text()
    internal_notes = fields.Text(groups='base.group_user')
    customer_source = fields.Char()
    work_source = fields.Char()
    no_parts_needed = fields.Boolean()
    warranty = fields.Boolean()
    intake_method = fields.Selection([('branch','في الفرع'),('pickup','استلام من العميل')], default='branch')
    state = fields.Selection([('draft','جديد'),('cancelled','ملغي')], default='draft', required=True)
    complaint_ids = fields.One2many('yt.reception.complaint','order_id')
    request_ids = fields.One2many('yt.reception.request','order_id')
    photo_ids = fields.One2many('yt.reception.photo','order_id')
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('yt.reception.order') or '/'
        return super().create(vals_list)
    @api.constrains('partner_id','vehicle_id','company_id','odometer_in','odometer_out')
    def _validate_reception(self):
        for rec in self:
            if rec.vehicle_id.partner_id != rec.partner_id or rec.vehicle_id.company_id != rec.company_id:
                raise ValidationError(_('السيارة يجب أن تتبع العميل والشركة المحددين.'))
            if rec.odometer_in < 0 or rec.odometer_out < 0:
                raise ValidationError(_('قراءة العداد لا يمكن أن تكون سالبة.'))
    def write(self, vals):
        if any(order.state != 'draft' for order in self) and any(key not in ('state',) for key in vals):
            raise AccessError(_('لا يمكن تعديل استقبال ملغي.'))
        return super().write(vals)
    def action_cancel(self):
        self.check_access_rights('write')
        self.write({'state':'cancelled'})
    def get_reception(self):
        self.ensure_one()
        self.check_access_rights('read')
        self.check_access_rule('read')
        result = self.read(['id','name','partner_id','vehicle_id','arrival_at','odometer_in','odometer_out','advisor_id','branch_id','reception_notes','internal_notes','customer_source','work_source','no_parts_needed','warranty','intake_method','state'])[0]
        result['complaints'] = self.complaint_ids.read(['id','name'])
        result['requests'] = self.request_ids.read(['id','name'])
        result['photos'] = self.photo_ids.read(['id','name','is_primary'])
        return result
    def save_reception(self, vals, complaints, requests):
        self.ensure_one()
        self.check_access_rights('write')
        if self.state != 'draft':
            raise AccessError(_('الأمر غير قابل للتعديل.'))
        permitted = {'odometer_in','odometer_out','arrival_at','branch_id','advisor_id','reception_notes','internal_notes','customer_source','work_source','no_parts_needed','warranty','intake_method'}
        if set(vals) - permitted:
            raise AccessError(_('هناك حقول لا يُسمح بتعديلها.'))
        if any(not (x or '').strip() for x in complaints + requests):
            raise ValidationError(_('لا يمكن حفظ شكوى أو خدمة فارغة.'))
        if len(complaints) > 100 or len(requests) > 100:
            raise ValidationError(_('عدد البنود كبير جدًا.'))
        self.write(vals)
        self.complaint_ids.unlink()
        self.request_ids.unlink()
        self.env['yt.reception.complaint'].create([{'order_id':self.id,'name':x.strip()} for x in complaints])
        self.env['yt.reception.request'].create([{'order_id':self.id,'name':x.strip()} for x in requests])
        return self.get_reception()
