from odoo import fields, models


class WorkshopV2Partner(models.Model):
    _inherit = 'res.partner'

    workshop_vehicle_ids = fields.One2many(
        'ycm.v2.vehicle', 'partner_id', string='سيارات العميل')
    workshop_vehicle_count = fields.Integer(
        compute='_compute_workshop_vehicle_count', string='عدد السيارات')

    def _compute_workshop_vehicle_count(self):
        groups = self.env['ycm.v2.vehicle'].read_group(
            [('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        counts = {row['partner_id'][0]: row['partner_id_count'] for row in groups}
        for partner in self:
            partner.workshop_vehicle_count = counts.get(partner.id, 0)

    workshop_order_ids = fields.One2many(
        'ycm.v2.order', 'partner_id', string='سجل صيانة العميل')

    def action_view_workshop_vehicles(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'سيارات العميل',
            'res_model': 'ycm.v2.vehicle', 'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
