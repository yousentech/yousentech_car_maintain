# -*- coding: utf-8 -*-
"""Keep visit identity in sync across entry, inspection and work order.

The entry card owns visit data; child screens can edit it, but changes are
written back to the entry card and distributed to all existing child records.
Commercial documents are intentionally never silently rewritten.
"""
from odoo import fields, models, _
from odoo.exceptions import ValidationError

VISIT_FIELDS = (
    'partner_id', 'car_panel_no', 'partner_mobile', 'car_size_id',
    'car_model', 'car_type_id', 'vin_no', 'drum_counter', 'pay_type',
)
SYNC_CONTEXT = 'workshop_visit_sync_in_progress'


def _visit_values(source, target):
    result = {}
    for name in VISIT_FIELDS:
        if name in source._fields and name in target._fields:
            value = source[name]
            result[name] = value.id if source._fields[name].type == 'many2one' else value
    return result


class EntryVisitSync(models.Model):
    _inherit = 'mizan.car.entry.card.master'

    vehicle_model_year = fields.Integer(string='سنة الصنع', related='vehicle_id.model_year', readonly=True)

    def _has_commercial_documents(self):
        self.ensure_one()
        return bool(
            self.maint_wo_id.sale_order_id
            or self.maint_wo_id.create_invoice_manually_id
            or self.checkup_id.create_invoice_manually_id
        )

    def confirm_btn(self):
        for card in self:
            if card.state != 'draft':
                raise ValidationError(_('تأكيد الدخول متاح فقط في مرحلة الإعداد.'))
            if not card.partner_id or not card.car_panel_no:
                raise ValidationError(_('يجب اختيار العميل ولوحة السيارة قبل تأكيد الدخول.'))
        return super().confirm_btn()

    def return_to_modify(self):
        for card in self:
            if card.state not in ('confirm', 'execute_started', 'work_order_started'):
                raise ValidationError(_('لا يمكن إعادة هذه المرحلة إلى الإعداد.'))
            if card._has_commercial_documents():
                raise ValidationError(_('لا يمكن استعادة التعديل بعد إنشاء مستندات تجارية.'))
            if not self.env.user.has_group('yousentech_car_maintain.group_rtn_to_draft_and_cancel_priv'):
                raise ValidationError(_('ليس لديك صلاحية استعادة التعديل.'))
        return super().return_to_modify()

    def execute_completed(self):
        for card in self:
            if card.state not in ('execute_started', 'work_order_started'):
                raise ValidationError(_('إكمال التنفيذ متاح فقط بعد بدء الفحص أو أمر العمل.'))
            if not card.maint_wo_id:
                raise ValidationError(_('لا يمكن إكمال التنفيذ دون إنشاء أمر عمل.'))
            work = card.maint_wo_id
            if not work.result_lines and not work.lines_spare_parts:
                raise ValidationError(_('أمر العمل فارغ. أضف خدمة منفذة أو قطع غيار مستخدمة قبل إكمال التنفيذ.'))
            if work.lines_spare_parts and any(line.qty_done <= 0 for line in work.lines_spare_parts):
                raise ValidationError(_('يوجد سطر قطع غيار لم تُسجّل له كمية منفذة. أكمل الكميات أو احذف السطر غير المستخدم.'))
        return super().execute_completed()

    def not_checkup_car(self):
        for card in self:
            if card.state != 'confirm' or card.checkup_id or card.maint_wo_id:
                raise ValidationError(_('الخروج بدون فحص متاح فقط بعد التأكيد وقبل إنشاء الفحص.'))
            if card._has_commercial_documents():
                raise ValidationError(_('لا يمكن الخروج بدون فحص مع وجود مستندات تجارية.'))
        return super().not_checkup_car()

    def cancel_order_btn(self):
        for card in self:
            if card.state in ('cancel_order', 'execute_completed', 'not_checkup_car'):
                raise ValidationError(_('لا يمكن إلغاء زيارة مغلقة أو ملغاة.'))
            if card._has_commercial_documents():
                raise ValidationError(_('لا يمكن الإلغاء بعد إنشاء مستند تجاري؛ عالج المستند أولًا.'))
            if not self.env.user.has_group('yousentech_car_maintain.group_rtn_to_draft_and_cancel_priv'):
                raise ValidationError(_('ليس لديك صلاحية إلغاء الزيارة.'))
        return super().cancel_order_btn()

    def create_checkup_procedure(self):
        self.ensure_one()
        existing = self.env['mizan.car.checkup.procedure.master'].search([('entry_card_id', '=', self.id)], limit=1)
        if existing:
            if existing.maint_wo_id and not self.user_has_groups('yousentech_car_maintain.group_use_checkup_procedure'):
                return self.call_wo_procedure()
            return self.call_checkup_procedure()
        return super().create_checkup_procedure()

    def write(self, vals):
        changing = set(vals).intersection(VISIT_FIELDS)
        if changing and not self.env.context.get(SYNC_CONTEXT):
            for card in self:
                if not isinstance(card.id, int):
                    continue
                if card.maint_wo_id.sale_order_id or (
                    card.checkup_id.create_invoice_manually_id
                    and card.checkup_id.create_invoice_manually_id.state != 'cancel'
                ):
                    raise ValidationError(_('لا يمكن تغيير بيانات الزيارة بعد إنشاء مستند تجاري مرتبط.'))
        result = super().write(vals)
        if changing and not self.env.context.get(SYNC_CONTEXT):
            for card in self:
                if not card.id or not isinstance(card.id, int):
                    continue
                for model, relation in (
                    ('mizan.car.checkup.procedure.master', 'entry_card_id'),
                    ('mizan.car.work.procedure.master', 'entry_card_id'),
                ):
                    children = self.env[model].search([(relation, '=', card.id)])
                    for child in children:
                        child.with_context(**{SYNC_CONTEXT: True}).write(
                            {key: value for key, value in _visit_values(card, child).items()
                             if key in changing}
                        )
        return result


class CheckupVisitSync(models.Model):
    _inherit = 'mizan.car.checkup.procedure.master'

    vehicle_model_year = fields.Integer(string='سنة الصنع', related='entry_card_id.vehicle_id.model_year', readonly=True)

    def create_work_order_procedure(self):
        self.ensure_one()
        existing = self.env['mizan.car.work.procedure.master'].search([('checkup_id', '=', self.id)], limit=1)
        if existing:
            return self.call_wo_procedure()
        return super().create_work_order_procedure()

    def write(self, vals):
        changing = set(vals).intersection(VISIT_FIELDS)
        if changing and not self.env.context.get(SYNC_CONTEXT):
            for record in self.filtered('entry_card_id'):
                card_vals = {key: vals[key] for key in changing if key in record.entry_card_id._fields}
                if card_vals:
                    record.entry_card_id.write(card_vals)
        return super().write(vals)


class WorkOrderVisitSync(models.Model):
    _inherit = 'mizan.car.work.procedure.master'

    vehicle_model_year = fields.Integer(string='سنة الصنع', related='entry_card_id.vehicle_id.model_year', readonly=True)
    drum_counter = fields.Char(string='عداد وقت الدخول', related='entry_card_id.drum_counter', readonly=True)

    def write(self, vals):
        changing = set(vals).intersection(VISIT_FIELDS)
        if changing and not self.env.context.get(SYNC_CONTEXT):
            for record in self.filtered('entry_card_id'):
                card_vals = {key: vals[key] for key in changing if key in record.entry_card_id._fields}
                if card_vals:
                    record.entry_card_id.write(card_vals)
        return super().write(vals)
