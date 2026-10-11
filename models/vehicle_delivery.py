# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WorkshopVehicleDelivery(models.Model):
    _inherit = 'mizan.car.entry.card.master'

    delivery_state = fields.Selection([
        ('pending', 'بانتظار التسليم'),
        ('delivered', 'تم التسليم والإغلاق'),
    ], string='حالة التسليم', default='pending', required=True, copy=False, readonly=True)
    delivery_date = fields.Datetime(string='تاريخ تسليم السيارة', readonly=True, copy=False)
    delivery_user_id = fields.Many2one('res.users', string='سلّم السيارة', readonly=True, copy=False)
    delivery_odometer = fields.Float(string='عداد الخروج', copy=False)
    credit_approved = fields.Boolean(string='اعتماد التسليم على الحساب', copy=False)
    credit_approved_by = fields.Many2one('res.users', string='معتمد البيع الآجل', readonly=True, copy=False)

    @api.depends('maint_wo_id.sale_order_id', 'maint_wo_id.sale_order_id.invoice_ids.state',
                 'maint_wo_id.sale_order_id.invoice_ids.payment_state',
                 'maint_wo_id.create_invoice_manually_id.state',
                 'maint_wo_id.create_invoice_manually_id.payment_state',
                 'checkup_id.create_invoice_manually_id.state',
                 'checkup_id.create_invoice_manually_id.payment_state')
    def _compute_delivery_financial_state(self):
        for card in self:
            invoices = card._delivery_invoices()
            posted = invoices.filtered(lambda move: move.state == 'posted' and move.move_type == 'out_invoice')
            card.delivery_financial_state = (
                'not_invoiced' if not posted
                else 'paid' if all(move.payment_state in ('paid', 'reversed') for move in posted)
                else 'open'
            )

    delivery_financial_state = fields.Selection([
        ('not_invoiced', 'غير مفوتر'), ('open', 'مفوتر - مستحق'),
        ('paid', 'مدفوع'),
    ], string='الحالة المالية', compute='_compute_delivery_financial_state')

    def _delivery_invoices(self):
        self.ensure_one()
        wo = self.maint_wo_id
        invoices = wo.sale_order_id.invoice_ids
        invoices |= wo.create_invoice_manually_id
        invoices |= self.checkup_id.create_invoice_manually_id
        return invoices.filtered(lambda m: m.move_type == 'out_invoice' and m.state != 'cancel')

    def action_approve_delivery_credit(self):
        if not self.env.user.has_group('yousentech_car_maintain.group_supervisor_priv'):
            raise UserError(_('اعتماد البيع الآجل متاح للمشرف فقط.'))
        for card in self:
            if card.delivery_state == 'delivered':
                raise UserError(_('لا يمكن تعديل الاعتماد بعد تسليم السيارة.'))
            card.write({'credit_approved': True, 'credit_approved_by': self.env.uid})

    def action_deliver_vehicle(self):
        for card in self:
            if not self.env.user.has_group('yousentech_car_maintain.group_supervisor_priv'):
                raise UserError(_('تسليم السيارة وإغلاق الزيارة متاح للمشرف فقط.'))
            if card.delivery_state == 'delivered':
                raise UserError(_('تم تسليم السيارة مسبقًا.'))
            if card.state != 'execute_completed':
                raise UserError(_('يجب إكمال التنفيذ الفني قبل تسليم السيارة.'))
            if not card.maint_wo_id:
                raise UserError(_('لا يوجد أمر عمل مرتبط بهذه الزيارة.'))
            if card.delivery_odometer < 0:
                raise UserError(_('عداد الخروج لا يمكن أن يكون سالبًا.'))
            order = card.maint_wo_id.sale_order_id
            if not order:
                raise UserError(_('يجب إنشاء أمر البيع قبل التسليم.'))
            pickings = order.picking_ids.filtered(lambda p: p.state != 'cancel')
            unfinished = pickings.filtered(lambda p: p.state != 'done')
            if unfinished:
                raise UserError(_('هناك حركات مخزون مرتبطة بأمر البيع لم تُنجز بعد.'))
            invoices = card._delivery_invoices()
            posted = invoices.filtered(lambda m: m.state == 'posted')
            if not posted:
                raise UserError(_('يجب ترحيل فاتورة العميل قبل التسليم.'))
            if any(m.payment_state not in ('paid', 'reversed') for m in posted) and not card.credit_approved:
                raise UserError(_('الفاتورة غير مسددة. يلزم السداد أو اعتماد البيع الآجل من المشرف.'))
            card.write({
                'delivery_state': 'delivered',
                'delivery_date': fields.Datetime.now(),
                'delivery_user_id': self.env.uid,
            })

    def write(self, vals):
        if 'credit_approved' in vals and vals['credit_approved'] and not self.env.user.has_group(
            'yousentech_car_maintain.group_supervisor_priv'
        ):
            raise UserError(_('لا يمكن اعتماد البيع الآجل دون صلاحية المشرف.'))
        if any(key in vals for key in ('delivery_state', 'delivery_date', 'delivery_user_id')):
            if not self.env.user.has_group('yousentech_car_maintain.group_supervisor_priv'):
                raise UserError(_('تعديل بيانات التسليم محصور بالمشرف.'))
        for card in self:
            if card.delivery_state == 'delivered':
                protected = set(vals) - {'message_follower_ids', 'message_partner_ids'}
                if protected:
                    raise UserError(_('الزيارة مسلّمة ومغلقة ولا يمكن تعديل بياناتها.'))
        return super().write(vals)
