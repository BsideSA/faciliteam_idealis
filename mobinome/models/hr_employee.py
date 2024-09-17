# -*- coding: utf-8 -*-
import logging

import requests

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    # Model inherit
    _inherit = 'hr.employee'

    # Custom fields
    id_mobinome = fields.Integer(string='ID')
    iri_mobinome = fields.Char(string='IRI')
    login_mobinome = fields.Char(string='Login App')
    password_mobinome = fields.Char(string='Password App')
    is_sent_to_mobinome_as_material = fields.Boolean(string='Is sent as Mobinome material', default=False)
    is_mobinome_material = fields.Boolean(string="is Mobinome material?", default=False)

    ###############
    # ODOO : POST #
    ###############
    @api.model
    def create(self, vals):
        # Call parent
        res = super(HrEmployee, self).create(vals)

        # Post employee on mobinome
        json_response = self.mobinome_post(res)

        if json_response:
            res.write({
                'id_mobinome': json_response['id'],
                'iri_mobinome': json_response['@id'],
            })

        # Return resource
        return res

    ################
    # ODOO : PATCH #
    ################
    def write(self, vals):
        # Call parent
        res = super(HrEmployee, self).write(vals)

        # Patch employee on mobinome
        for employee in self:
            if employee.iri_mobinome:
                self.mobinome_patch(employee)

        # Return resource
        return res

    #################
    # ODOO : DELETE #
    #################
    def unlink(self):
        # Delete employee on mobinome
        for employee in self:
            if employee.iri_mobinome:
                self.delete_employee(employee.iri_mobinome)

        # Call parent
        res = super().unlink()

        # Return resource
        return res

    ##############
    # API : POST #
    ##############
    def mobinome_post(self, employee):
        if employee and employee['login_mobinome'] and employee['password_mobinome']:
            try:
                if not employee['work_email']:
                    employee['work_email'] = '%s@mobinome.com' % employee['login_mobinome']

                # Request
                response = self.env['res.config.settings'].make_api_call("POST", 'application/json',
                                                                         self.set_values(employee), '/api/' + self.get_mobinome_type(employee))

            except:
                logging.exception('')
                return False

            # If success, return data
            if response and response.status_code == requests.codes.created:
                    json_data = response.json()
                    return json_data
            elif response and response.status_code:
                # Log error & return False
                _logger.error('Error: %d', response.status_code)
        return False

    ###############
    # API : PATCH #
    ###############
    def mobinome_patch(self, employee):
        if employee and employee['login_mobinome']:
            if not employee['work_email']:
                employee['work_email'] = '%s@mobinome.com' % employee['login_mobinome']

            # Request
            response = self.env['res.config.settings'].make_api_call("PATCH", 'application/merge-patch+json',
                                                                     self.set_values(employee),
                                                                     employee['iri_mobinome'])

            # Log error if unsuccess patch
            if response and response.status_code != requests.codes.ok:
                _logger.error('Error: %d', response.status_code)
                return False

        return True

    ################
    # API : DELETE #
    ################
    def delete_employee(self, iri_employee):
        try:
            # Request
            response = self.env['res.config.settings'].make_api_call("DELETE", {}, '', iri_employee)
        except:
            return False

        # Log error if unsuccess delete
        if response and response.status_code != requests.codes.no_content:
            _logger.error('Error: %d', response.status_code)
            return False

        return True

    def set_values(self, employee):
        if 'materials' in self.get_mobinome_type(employee):
            material_data = {
                "name": employee['name'],
                "internalReference": 'ODOO_EMPLOYEE_' + str(employee['id']),
            }
            if not employee['iri_mobinome']:
                material_data["category"] = self.env['mobinome.material.category'].search([('id', '=', 
                                                                                            self.env['ir.config_parameter'].sudo().get_param(
                                                                                                'mobinome.mobinome_default_material_category_id'))])['iri_mobinome'] or None
            return material_data
        else:
            employee_data = {
                "name": employee['name'],
                "mobile": employee['mobile_phone'] or None,
                "email": employee['work_email'],
                "login": employee['login_mobinome'],
                "internalReference": 'ODOO_EMPLOYEE_' + str(employee['id']),
            }

            if employee['password_mobinome']:
                employee_data["plainPassword"] = employee['password_mobinome']
            if not employee['iri_mobinome']:
                employee_data["profile"] = self.env['mobinome.mobiner.profile'].search([('id', '=', 
                                                                                         self.env['ir.config_parameter'].sudo().get_param(
                                                                                             'mobinome.mobinome_default_mobiner_profile_id'))])['iri_mobinome'] or None
                employee_data["department"] = self.env['mobinome.departments'].search([('id', '=', 
                                                                                        self.env['ir.config_parameter'].sudo().get_param(
                                                                                            'mobinome.mobinome_default_department_id'))])['iri_mobinome'] or None
                employee_data["company"] = self.env['mobinome.companies'].search([('id', '=', 
                                                                                   self.env['ir.config_parameter'].sudo().get_param(
                                                                                       'mobinome.mobinome_default_company_id'))])['iri_mobinome'] or None
            return employee_data

    def get_mobinome_type(self, employee):
        return 'materials' if employee.is_mobinome_material or employee.is_sent_to_mobinome_as_material else 'mobiners'

    def send_mobinome(self):
        if self['id_mobinome']:
            self.mobinome_patch(self)
        else:
            json_mobinome = self.mobinome_post(self)

            if json_mobinome:
                self['id_mobinome'] = json_mobinome['id']
                self['iri_mobinome'] = json_mobinome['@id']
        return True
