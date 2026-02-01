from odoo import fields, models, _,api
class res_config_settings(models.TransientModel):
    _inherit = 'res.config.settings'

    discount_posted = fields.Boolean('ترحيل الخصم في اوامر التركيب')

    car_no = fields.Boolean('ادخال رقم لوحة السيارة اجباري')
    vin_no = fields.Boolean('ادخال رقم الشاصي للسيارة اجباري')
    compelete_done_date_not_required = fields.Boolean('تاريخ اكتمال التنفيذ غير اجباري')
    partner_mobile_not_required = fields.Boolean('ادخال رقم جوال العميل غير اجباري')
    service_price_include_tax = fields.Boolean('سعر الخدمة شاملة الضريبة')

    collecting_products = fields.Boolean('تجميع الاصناف في بند واحد')
    car_type = fields.Boolean('ادخال نوع السيارة اجباري')


    @api.model
    def get_values(self):
        res = super(res_config_settings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        l_discount_posted = params.get_param('discount_posted',
                                             default=False)
        l_car_no = params.get_param('car_no',
                                             default=False)
        l_vin_no = params.get_param('vin_no',
                                    default=False)

        l_partner_mobile_not_required = params.get_param('partner_mobile_not_required',
                                    default=False)

        l_compelete_done_date_not_required = params.get_param('compelete_done_date_not_required',
                                                       default=False)

        l_collecting_products = params.get_param('collecting_products',
                                    default=False)
        l_car_type = params.get_param('car_type',
                                             default=False)


        l_service_price_include_tax = params.get_param('service_price_include_tax',
                                                       default=False)
  
        res.update(discount_posted=l_discount_posted)
        res.update(car_no=l_car_no)
        res.update(vin_no=l_vin_no)
        res.update(partner_mobile_not_required=l_partner_mobile_not_required)

        res.update(compelete_done_date_not_required=l_compelete_done_date_not_required)
        res.update(collecting_products=l_collecting_products)
        res.update(car_type=l_car_type)
        res.update(service_price_include_tax=l_service_price_include_tax)
        return res

    def set_values(self):
        super(res_config_settings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            "discount_posted",
            self.discount_posted)

        self.env['ir.config_parameter'].sudo().set_param(
            "car_no",
            self.car_no)

        self.env['ir.config_parameter'].sudo().set_param(
            "vin_no",
            self.vin_no)

        self.env['ir.config_parameter'].sudo().set_param(
          "partner_mobile_not_required",self.partner_mobile_not_required)

        self.env['ir.config_parameter'].sudo().set_param(
            "compelete_done_date_not_required",
            self.compelete_done_date_not_required)

        self.env['ir.config_parameter'].sudo().set_param(
                    "collecting_products",
                    self.collecting_products)

        self.env['ir.config_parameter'].sudo().set_param(
        "car_type",
        self.car_type)

        self.env['ir.config_parameter'].sudo().set_param(
        "service_price_include_tax",
        self.service_price_include_tax)

      

