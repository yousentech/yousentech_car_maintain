# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class hr_employee(models.Model):
    _inherit = 'hr.employee'

    supervisor_emp = fields.Boolean(string="المشرف الفني")
    technical_emp = fields.Boolean(string="فني تركيب")
    face_features_line_id = fields.One2many('emp.face.features','employee_id',copy=False ,ondelete='cascade')
    
class emp_face_features(models.Model):
    _name = 'emp.face.features'
    
    botton_mouth_x =fields.Integer()
    botton_mouth_y =fields.Integer()
    
    left_cheak_x =fields.Integer()
    left_cheak_y =fields.Integer()
    
    left_ear_x =fields.Integer()
    left_ear_y =fields.Integer()
    
    left_eye_x =fields.Integer()
    left_eye_y =fields.Integer()
    
    left_mouth_x =fields.Integer()
    left_mouth_y =fields.Integer()

    nose_base_x =fields.Integer()
    nose_base_y =fields.Integer()

    right_cheak_x =fields.Integer()
    right_cheak_y =fields.Integer()
    
    right_ear_x =fields.Integer()
    right_ear_y =fields.Integer()
    
    right_eye_x =fields.Integer()
    right_eye_y =fields.Integer()
    
    right_mouth_x =fields.Integer()
    right_mouth_y =fields.Integer()
    
    employee_id= fields.Many2one('hr.employee',copy=False, ondelete='cascade')
    