# -*- coding: utf-8 -*-
import logging


from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class HrEmployeePublic(models.Model):
    # Model inherit
    _inherit = 'hr.employee.public'

    # Custom fields
    id_mobinome = fields.Integer(string='ID', related='employee_id.id_mobinome', compute_sudo=True)
    iri_mobinome = fields.Char(string='IRI', related='employee_id.iri_mobinome', compute_sudo=True)
    login_mobinome = fields.Char(string='Login App', related='employee_id.login_mobinome', compute_sudo=True)
    password_mobinome = fields.Char(string='Password App', related='employee_id.password_mobinome', compute_sudo=True)
    is_sent_to_mobinome_as_material = fields.Boolean(string='Is sent as Mobinome material', related='employee_id.is_sent_to_mobinome_as_material', compute_sudo=True)
    is_mobinome_material = fields.Boolean(string='is Mobinome material?', related='employee_id.is_mobinome_material', compute_sudo=True)