# -*- coding: utf-8 -*-
from webbrowser import get
from odoo import models, fields, api
from odoo.addons.website.tools import text_from_html
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
import logging
import requests
import json
import pytz
import re

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    # Model inherit
    _inherit = 'project.task'

    # Custom fields
    id_mobinome = fields.Integer(string='ID Mobinome')
    iri_mobinome = fields.Char(string='IRI Mobinome')
    can_update_to_mobinome = fields.Boolean(string='Can update to mobinome', compute='_compute_can_update_to_mobinome')

    # Parent custom fields
    url_mobinome_file = fields.Char(string='URL Mobinome File', compute='_compute_url_mobinome_file')
    mobinome_task_name = fields.Char(string='Mobinome task name')
    user_id = fields.Many2one('res.users', string="User", compute='_compute_user_id', store=True)
    project_manager = fields.Many2one('hr.employee', string="Project manager employee", related="user_id.employee_id")
    total_hours_planned = fields.Float(string='Hours Planned')
    total_mobiner_planned = fields.Integer(string='Number of technician')
    desired_start = fields.Datetime(string="Due date")
    supplier_order_date = fields.Datetime(string="Supplier order date")
    mobinome_department_id = fields.Many2one('mobinome.departments', string='Mobinome department')
    mobinome_service_time_activity_id = fields.Many2one('mobinome.service.time.activities', string='Mobinome service '
                                                                                                   'time activity')
    street = fields.Char(string="Street", related="site_id.street")
    street2 = fields.Char(string="Street 2", related="site_id.street2")
    zip = fields.Char(string="Zip", related="site_id.zip")
    city = fields.Char(string="City", related="site_id.city")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', related="site_id.country_id")
    country_code = fields.Char(related='country_id.code', string="Country Code")
    email = fields.Char(related='site_id.email')
    mobile = fields.Char(string="Mobile", unaccent=False, related='site_id.mobile')

    def _compute_url_mobinome_file(self):
        for task in self:
            if not task.parent_id and task.id_mobinome:
                task.url_mobinome_file = "https://"+self.env['ir.config_parameter'].sudo().get_param('mobinome'
                                                                                                        '.mobinome_url')+"/fr/gmao/equipment/projectList/" + str(task.id_mobinome)
            else:
                task.url_mobinome_file = ''

    def _compute_can_update_to_mobinome(self):
        for task in self:
            task.can_update_to_mobinome = task['parent_id'] and task['parent_id']['iri_mobinome']

    @api.depends('user_ids')
    def _compute_user_id(self):
        for task in self:
            if task.user_ids:
                task.user_id = task.user_ids[0]
            else:
                task.user_id = False

    ###############
    # ODOO : POST #
    ###############
    @api.model
    def create(self, vals):
        # Call parent
        res = super(ProjectTask, self).create(vals)

        if not res['parent_id'] and self.env['ir.config_parameter'].sudo().get_param('mobinome.parent_task_automatic_creation'):
            # Post task on mobinome
            json_mobinome = self.mobinome_post(res)

            if json_mobinome:
                res['id_mobinome'] = json_mobinome['id']
                res['iri_mobinome'] = json_mobinome['@id']        

        if res['parent_id'] and res['parent_id']['iri_mobinome'] and self.env['ir.config_parameter'].sudo().get_param('mobinome.tasks_automatic_creation'):
            # Post task on mobinome
            json_mobinome = self.mobinome_post(res)

            if json_mobinome:
                res['id_mobinome'] = json_mobinome['id']
                res['iri_mobinome'] = json_mobinome['@id']

            # Check if stock picking will create
            self.check_picking(res)

        # Return resource
        return res

    ################
    # ODOO : PATCH #
    ################
    def write(self, vals):
        # Call parent
        res = super(ProjectTask, self).write(vals)

        # Patch task on mobinome
        for task in self:
            if task.iri_mobinome:
                self.mobinome_patch(task)
            if 'mobinome_task_name' in vals and task.mobinome_task_name or \
                'total_hours_planned' in vals and task.total_hours_planned or \
                'total_mobiner_planned' in vals and task.total_mobiner_planned or \
                'desired_start' in vals and task.desired_start or \
                'supplier_order_date' in vals and task.supplier_order_date or \
                'description' in vals and task._description:
                for child_task in task.child_ids:
                    if child_task.iri_mobinome:
                        child_task.write({})

        # Return resource
        return res

    #################
    # ODOO : DELETE #
    #################
    def unlink(self):
        # Delete task on mobinome
        for task in self:
            if task.iri_mobinome:
                self.delete_task(task.iri_mobinome)

        # Call parent
        res = super().unlink()

        # Return resource
        return res

    def send_mobinome(self):
        if self['id_mobinome']:
            self.mobinome_patch(self)
        else:
            json_mobinome = self.mobinome_post(self)

            if json_mobinome:
                self['id_mobinome'] = json_mobinome['id']
                self['iri_mobinome'] = json_mobinome['@id']

        # Update stock / delivery
        if self.sale_line_id and self.sale_line_id.order_id.delivery_count :
            if self['sale_line_id']['order_id']['delivery_count'] > 0:
                self.env['stock.picking'].mobinome_update(
                    self.env['stock.picking'].search([('sale_id', '=', self['sale_line_id']['order_id']['id'])]))
        return True

    ##############
    # API : POST #
    ##############
    def mobinome_post(self, project_task):
        if not project_task['parent_id']:
            partner = None
            # Take only parent task with sales
            sale_order = project_task['sale_order_id'] if project_task['sale_order_id'] else None
            if sale_order and sale_order['partner_shipping_id']:
                partner = sale_order['partner_shipping_id']
            if not partner:
                partner = project_task['partner_id']

            if partner:
                if not partner.iri_mobinome:
                    json_mobinome = partner.mobinome_post(partner)
                    if json_mobinome:
                        partner.write({
                            'id_mobinome': json_mobinome['id'],
                            'iri_mobinome': json_mobinome['@id']
                        })
                try:
                    # Check if parent_task is not already created by customer
                    if self.env['ir.config_parameter'].sudo().get_param('mobinome.create_project_task_with_customer'):
                        self.env['res.partner'].create_or_update_project_task(partner)

                        project_task['id_mobinome'] = partner['id_project_task_mobinome']
                        project_task['iri_mobinome'] = partner['iri_project_task_mobinome']
                    else:
                        # Request
                        response = self.env['res.config.settings'].make_post_call(self.set_values(project_task, partner), '/api/projects')

                        # If success, return data
                        if response and response.status_code == requests.codes.created:
                            json_data = response.json()
                            return json_data
                        elif response and response.status_code:
                            # Log error & return False
                            _logger.error('Error: %d', response.status_code)
                except:
                    logging.exception('')
                    return False
        if project_task['parent_id'] and project_task['parent_id']['iri_mobinome']:
            try:
                # Request
                values = self.set_values(project_task)
                values['forecast'] = False
                response = self.env['res.config.settings'].make_api_call("POST", 'application/json',
                                                                        values, '/api/event_carts')
            except Exception as e:
                _logger.error(e)
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
    def mobinome_patch(self, project_task):
        if project_task['parent_id'] and project_task['parent_id']['iri_mobinome']:
            try:
                # Request
                response = self.env['res.config.settings'].make_api_call("PATCH", 'application/merge-patch+json',
                                                                        self.set_values(project_task),
                                                                        project_task['iri_mobinome'])
            except Exception as e:
                _logger.error(e)
                return False

            # Log error if unsuccess patch
            if response and response.status_code != requests.codes.ok:
                _logger.error('Error: %d', response.status_code)
                return False
        if not project_task['parent_id'] and project_task['iri_mobinome']:
            partner = None
            sale_order = project_task['sale_order_id'] if project_task['sale_order_id'] else None
            if sale_order and sale_order['partner_shipping_id']:
                partner = sale_order['partner_shipping_id']
            elif project_task['partner_id']:
                partner = project_task['partner_id']
            if partner:
                if not partner['iri_mobinome']:
                    json_mobinome = partner.mobinome_post(partner)
                    if json_mobinome:
                        partner.write({
                            'id_mobinome': json_mobinome['id'],
                            'iri_mobinome': json_mobinome['@id']
                        })

                # Check if parent task is not already created by customer
                if self.env['ir.config_parameter'].sudo().get_param('mobinome.create_project_task_with_customer'):
                    self.env['res.partner'].create_or_update_project_task(partner)
                else:
                    # Request
                    response = self.env['res.config.settings'].make_patch_call(self.set_values(project_task, partner), project_task['iri_mobinome'])

                    # Log error if unsuccess patch
                    if response and response.status_code != requests.codes.ok:
                        _logger.error('Error: %d', response.status_code)
                        return False
        return True

    ################
    # API : DELETE #
    ################
    def delete_task(self, iri_task):
        try:
            # Request
            response = self.env['res.config.settings'].make_api_call("DELETE", '', {}, iri_task)
        except:
            return False

        # Log error if unsuccess delete
        if response and response.status_code != requests.codes.no_content:
            _logger.error('Error: %d', response.status_code)
            return False

        return True

    def set_values(self, project_task, partner=False):
        if not project_task['parent_id']:
            city = ''
            partner_id = project_task.partner_id.display_name if project_task.partner_id else ''
            if city:
                name = city
                if partner_id:
                    name += f' - {partner_id}'
            else:
                name = str(project_task['id']) + " - " + project_task['name'] if project_task['name'] else 'unnamed'
            value = {
                "name": name,
                "customer": partner['iri_mobinome'] if partner else project_task['partner_id']['iri_mobinome'],
                "projectManager": project_task['project_manager']['iri_mobinome'] if project_task['project_manager'] else None,
                # "...": project_task['origin_contact_id'] or None, #TODO if needed in mobinome create this field or merge in name or in another field
                "address1": project_task['street'] or None,
                "address2": project_task['street2'] or None,
                "city": project_task['city'] or None,
                "zip": project_task['zip'] or None,
                "phone": project_task['partner_phone'] or None,
                "mobile": project_task['mobile'] or None,
                "email": project_task['email'] or None,
                "country": project_task['country_code'] or 'BE',
                "internalReference": 'ODOO_RES_PROJECT_TASK_' + str(project_task['id']),
            }
            return value
        if project_task['parent_id'] and project_task['parent_id']['iri_mobinome']:
            # html_description = project_task['parent_id']['description']
            html_description = project_task['description']
            description = ""
            if html_description:
                description_with_paragraphs = re.sub(r'</p>', '\n', html_description)
                description_with_paragraphs = re.sub(r'<p>', '', description_with_paragraphs)
                description = text_from_html(description_with_paragraphs)
                description = description.rstrip()
                if description.endswith('\n'):
                    description = description[:-1]
                description = description.lstrip('\n')
                description = description.lstrip(' ')

            values = {
                "allDay": False,
                "title": project_task['parent_id']['mobinome_task_name'] if project_task['parent_id'][
                    'mobinome_task_name'] else project_task['parent_id']['name'] + " - " + project_task['name'],
                "project": project_task['parent_id']['iri_mobinome'],
                "externalReference": str(project_task['id']),
                "internalReference": 'ODOO_PROJECT_TASK_' + str(project_task['id']),
                "costQuoteAmount": project_task['sale_order_id']['amount_untaxed'],
                "totalHoursPlanned": project_task['parent_id']['total_hours_planned'] if project_task['parent_id'][
                    'total_hours_planned'] else 0.00,
                "totalMobinerPlanned": project_task['parent_id']['total_mobiner_planned'],
                "description": description,
            }
            if not project_task['iri_mobinome']:
                values['company'] = self.env['mobinome.companies'].search([('id', '=', 
                                                                            self.env['ir.config_parameter'].sudo().get_param(
                                                                                'mobinome.mobinome_default_company_id'))])['iri_mobinome'] or None
                values["department"] = self.env['mobinome.departments'].search([('id', '=', 
                                                                                self.env['ir.config_parameter'].sudo().get_param(
                                                                                    'mobinome.mobinome_default_department_id'))])['iri_mobinome'] or None
            defaultCostQuote = self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_default_event_cart_cost_quote_duration_in_week')
            if defaultCostQuote:
                values["costQuoteDuration"] = int(defaultCostQuote)

            if project_task['planned_date_begin']:
                values["desiredStart"] = str(self.convert_utc_date_to_user_tz(
                    project_task['planned_date_begin']))  # example 2023-06-19T12:29:45.806Z

            if project_task['date_deadline']:
                values["deadline"] = str(self.convert_utc_date_to_user_tz(
                    project_task['date_deadline']))  # example 2023-06-19T12:29:45.806Z

            if project_task['parent_id']['mobinome_department_id']:
                values["department"] = project_task['parent_id']['mobinome_department_id']['iri_mobinome']

            if project_task['parent_id']['project_manager']:
                values["projectManager"] = project_task['parent_id']['project_manager']['iri_mobinome']

            if project_task['parent_id']['mobinome_service_time_activity_id']:
                values["defaultServiceTimeActivity"] = project_task['parent_id']['mobinome_service_time_activity_id']['iri_mobinome']
                values["color"] = project_task['parent_id']['mobinome_service_time_activity_id']['color']
            return values

    def check_picking(self, task):
        sale_order = task['sale_line_id']['order_id']
        if sale_order['state'] == 'sale':
            for line in sale_order['order_line']:
                if line['product_id']['detailed_type'] == 'product':
                    if sale_order['delivery_count'] > 0:
                        delivery = sale_order.env['stock.picking'].search([('sale_id', '=', sale_order['id'])])
                        sale_order.env['stock.picking'].mobinome_update(delivery)
                        break
        return True

    def convert_utc_date_to_user_tz(self, utc_date):
        # Convert desiredStart to local timezone due to mobinome planning not saving in UTC
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        date_tz = datetime.strftime(pytz.utc.localize(utc_date).astimezone(local),
                                    "%Y-%m-%d %H:%M:%S") if utc_date else None
        return date_tz

    def refresh_departments(self):
        self.env['res.config.settings'].refresh_departments()

    def refresh_service_time_activity(self):
        self.env['mobinome.service.time.activities'].refresh()

    ##################
    # API : SYNC ALL #
    ##################
    def sync_all(self):
        # Check if sale order linked to project task
        for task in self:
            if task.sale_order_id:
                if task.sale_order_id.partner_shipping_id:
                    if task.sale_order_id.partner_shipping_id.iri_mobinome:
                        # Patch project task on mobinome
                        task.sale_order_id.sync_all()
            else:
                self.env['account.analytic.line'].sync_services(sale_order_id=None, project_task_id=self.id)
                self.env['account.analytic.line'].sync_events(sale_order_id=None, project_task_id=self.id)
