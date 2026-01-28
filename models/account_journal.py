
from odoo import models, fields, _

class account_journal(models.Model):
    _inherit = 'account.journal'

    use_main_cash_close = fields.Boolean(string='دفتر صندوق المركز الرئيسي لاقفال صناديق الفروع')

