# -*- coding: utf-8 -*-
import json
import logging

import requests

from odoo import models, fields

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    # Model inherit
    _inherit = 'res.config.settings'

    # Fields
    mobinome_url = fields.Char(string='Server', required=True, readonly=False)
    mobinome_login = fields.Char(string='Login', required=True, readonly=False)
    mobinome_password = fields.Char(string='Password', required=True, readonly=False)
    mobinome_token = fields.Text(string='Token', readonly=False)
    tasks_automatic_creation = fields.Boolean(string='Tasks Automatic Creation', default=False, readonly=False)
    parent_task_automatic_creation = fields.Boolean(string='Parent Task Automatic Creation', default=False, readonly=False)
    customer_have_lastname = fields.Boolean(string='Customer Have lastname', default=False, readonly=False)
    create_project_task_with_customer = fields.Boolean(string='Create project with customer', default=False, readonly=False)
    mobinome_default_company_id = fields.Many2one('mobinome.companies', string='Default company', readonly=False)
    mobinome_default_department_id = fields.Many2one('mobinome.departments', string='Default department', readonly=False)
    mobinome_default_mobiner_profile_id = fields.Many2one('mobinome.mobiner.profile', string='Default Profile', readonly=False)
    mobinome_default_event_cart_cost_quote_duration_in_week = fields.Integer(string='Default quote duration for tasks (in week)', default=1, readonly=False)
    mobinome_default_material_category_id = fields.Many2one('mobinome.material.category', string='Default material category', readonly=False)
    mobinome_default_end_stage_id = fields.Many2one('project.task.type', string='Default end task stage', readonly=False)

    # Get values
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        
        # Fetching parameters
        mobinome_default_company_id = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_default_company_id')
        mobinome_default_department_id = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_default_department_id')
        mobinome_default_mobiner_profile_id = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_default_mobiner_profile_id')
        mobinome_default_material_category_id = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_default_material_category_id')
        mobinome_default_end_stage_id = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_default_end_stage_id')
        
        # Converting IDs to recordsets
        res.update(
            mobinome_url=self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_url'),
            mobinome_login=self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_login'),
            mobinome_password=self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_password'),
            mobinome_token=self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_token'),
            tasks_automatic_creation=self.env['ir.config_parameter'].sudo().get_param('mobinome.tasks_automatic_creation'),
            parent_task_automatic_creation=self.env['ir.config_parameter'].sudo().get_param('mobinome.parent_task_automatic_creation'),
            customer_have_lastname=self.env['ir.config_parameter'].sudo().get_param('mobinome.customer_have_lastname'),
            mobinome_default_company_id=int(mobinome_default_company_id) if mobinome_default_company_id else False,
            mobinome_default_department_id=int(mobinome_default_department_id) if mobinome_default_department_id else False,
            mobinome_default_mobiner_profile_id=int(mobinome_default_mobiner_profile_id) if mobinome_default_mobiner_profile_id else False,
            mobinome_default_material_category_id=int(mobinome_default_material_category_id) if mobinome_default_material_category_id else False,
            mobinome_default_end_stage_id=int(mobinome_default_end_stage_id) if mobinome_default_end_stage_id else False,
            create_project_task_with_customer=self.env['ir.config_parameter'].sudo().get_param('mobinome.create_project_task_with_customer'),
            mobinome_default_event_cart_cost_quote_duration_in_week=int(self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_default_event_cart_cost_quote_duration_in_week')),
        )

        # Convert integer IDs to records
        if res['mobinome_default_company_id']:
            res['mobinome_default_company_id'] = self.env['mobinome.companies'].browse(res['mobinome_default_company_id'])
        if res['mobinome_default_department_id']:
            res['mobinome_default_department_id'] = self.env['mobinome.departments'].browse(res['mobinome_default_department_id'])
        if res['mobinome_default_mobiner_profile_id']:
            res['mobinome_default_mobiner_profile_id'] = self.env['mobinome.mobiner.profile'].browse(res['mobinome_default_mobiner_profile_id'])
        if res['mobinome_default_material_category_id']:
            res['mobinome_default_material_category_id'] = self.env['mobinome.material.category'].browse(res['mobinome_default_material_category_id'])
        if res['mobinome_default_end_stage_id']:
            res['mobinome_default_end_stage_id'] = self.env['project.task.type'].browse(res['mobinome_default_end_stage_id'])        
        return res

    # Set values
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        
        self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_url', self.mobinome_url)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_login', self.mobinome_login)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_password', self.mobinome_password)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.tasks_automatic_creation', self.tasks_automatic_creation)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.parent_task_automatic_creation', self.parent_task_automatic_creation)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.customer_have_lastname', self.customer_have_lastname)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_default_company_id', self.mobinome_default_company_id.id if self.mobinome_default_company_id else False)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_default_department_id', self.mobinome_default_department_id.id if self.mobinome_default_department_id else False)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_default_mobiner_profile_id', self.mobinome_default_mobiner_profile_id.id if self.mobinome_default_mobiner_profile_id else False)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_default_material_category_id', self.mobinome_default_material_category_id.id if self.mobinome_default_material_category_id else False)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_default_end_stage_id', self.mobinome_default_end_stage_id.id if self.mobinome_default_end_stage_id else False)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.create_project_task_with_customer', self.create_project_task_with_customer)
        self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_default_event_cart_cost_quote_duration_in_week', self.mobinome_default_event_cart_cost_quote_duration_in_week)


    ###############
    # API : TOKEN #
    ###############
    def get_token(self):
        token_from_odoo = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_token') or False
        return token_from_odoo if token_from_odoo else self.refresh_token()

    def refresh_token(self):
        # Get Url, Login & Password from ir.config.parameter model
        mobinome_url = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_url') or False
        mobinome_login = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_login') or False
        mobinome_password = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_password') or False

        # Ensure Url, Login & Password are set
        if mobinome_url and mobinome_login and mobinome_password:
            # Request
            try:
                response = requests.request("POST", "https://%s/api/authentication" % mobinome_url, headers={
                    'Content-Type': 'application/json'
                }, data=json.dumps({
                    "login": mobinome_login,
                    "password": mobinome_password
                }))
            except:
                return False
            # Log [DEBUG]
            _logger.debug('Request [%s]: %s', response.request.method, response.request.url)

            # Return token if succeed
            if response and response.status_code == 200:
                # Parse json response
                json_data = response.json()

                _logger.debug('Response [%s]: %s', response.status_code, json_data)
                _logger.debug('token : %s', json_data['token'])
                # Save token to settings
                self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_token', json_data['token'])

                # Return token
                return json_data['token']
            elif response and response.status_code == 401:
                _logger.error('Error: invalid credentials [%s, %s, %s]', mobinome_url, mobinome_login,
                              mobinome_password)
            elif response and response.status_code:
                _logger.error('Error: %d', response.status_code)

        return False

    ###############
    # CLEAR TOKEN #
    ###############
    def action_clear_token(self):
        self.env['ir.config_parameter'].sudo().set_param('mobinome.mobinome_token', None)

    #############
    # API PATCH #
    #############
    def make_patch_call(self, data, iri):
        return self.make_api_call("PATCH", 'application/merge-patch+json', data, iri)

    #############
    # API POST #
    #############
    def make_post_call(self, data, iri):
        return self.make_api_call("POST", 'application/json', data, iri)

    ##############
    # API DELETE #
    ##############
    def make_delete_call(self, iri):
        return self.make_api_call("DELETE", {}, '', iri)

    ################
    # API REQUESTS #
    ################
    def make_api_call(self, method, content_type, data, iri=''):
        if self.env.context.get('import_file') and self.env.context.get('is_test_import'):
            return False

        # Get Url, Login & Password from ir.config.parameter model
        mobinome_url = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_url') or False
        token = self.get_token()

        try:
            response = requests.request(method, "https://%s%s" % (mobinome_url, iri), headers={
                'Content-Type': content_type,
                'Authorization': 'Bearer %s' % token
            }, data=json.dumps(data))
            if response.status_code == requests.codes.unauthorized:
                token = self.refresh_token()
                response = requests.request(method, "https://%s%s" % (mobinome_url, iri), headers={
                    'Content-Type': content_type,
                    'Authorization': 'Bearer %s' % token
                }, data=json.dumps(data))
            # Log [DEBUG]
            _logger.debug('Request [%s]: %s', response.request.method, response.request.url)
            _logger.debug('Request [BODY]: %s', response.request.body)
        except:
            return False
        return response

    def refresh_companies(self):
        response = self.make_api_call("GET", 'application/json', {}, '/api/companies?pagination=false')
        if response and response.status_code == requests.codes.ok:
            # Log [DEBUG]
            _logger.debug('Request [%s]: %s', response.request.method, response.request.url)
            _logger.debug('Request [BODY]: %s', response.request.body)
            for company in self.env['mobinome.companies'].search([]):
                company.unlink()

            json_data = response.json()
            for company in json_data['hydra:member']:
                self.env['mobinome.companies'].create({
                    'name': company['name'],
                    'iri_mobinome': company['@id'],
                })
        elif response and response.status_code:
            _logger.error('Error: %d', response.status_code)

        return True

    def refresh_departments(self):
        response = self.make_api_call("GET", 'application/json', {}, '/api/departments?pagination=false')
        if response and response.status_code == requests.codes.ok:
            # Log [DEBUG]
            _logger.debug('Request [%s]: %s', response.request.method, response.request.url)
            _logger.debug('Request [BODY]: %s', response.request.body)
            for department in self.env['mobinome.departments'].search([]):
                department.unlink()

            json_data = response.json()
            for department in json_data['hydra:member']:
                self.env['mobinome.departments'].create({
                    'name': department['name'],
                    'iri_mobinome': department['@id'],
                })
        elif response and response.status_code:
            _logger.error('Error: %d', response.status_code)

        return True


    def refresh_mobiner_profile(self):
        response = self.make_api_call("GET", 'application/json', {}, '/api/mobiner_profiles?pagination=false')
        if response and response.status_code == requests.codes.ok:
            # Log [DEBUG]
            _logger.debug('Request [%s]: %s', response.request.method, response.request.url)
            _logger.debug('Request [BODY]: %s', response.request.body)
            for department in self.env['mobinome.mobiner.profile'].search([]):
                department.unlink()

            json_data = response.json()
            for department in json_data['hydra:member']:
                self.env['mobinome.mobiner.profile'].create({
                    'name': department['name'],
                    'iri_mobinome': department['@id'],
                })
        elif response and response.status_code:
            _logger.error('Error: %d', response.status_code)

        return True

    def refresh_material_category(self):
        response = self.make_api_call("GET", 'application/json', {}, '/api/material_categories?pagination=false')
        if response and response.status_code == requests.codes.ok:
            # Log [DEBUG]
            _logger.debug('Request [%s]: %s', response.request.method, response.request.url)
            _logger.debug('Request [BODY]: %s', response.request.body)
            for category in self.env['mobinome.material.category'].search([]):
                category.unlink()

            json_data = response.json()
            for category in json_data['hydra:member']:
                self.env['mobinome.material.category'].create({
                    'name': category['name'],
                    'iri_mobinome': category['@id'],
                })
        elif response and response.status_code:
            _logger.error('Error: %d', response.status_code)

        return True
