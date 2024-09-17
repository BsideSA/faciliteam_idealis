# -*- coding: utf-8 -*-
import logging

import requests

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    # Model inherit
    _inherit = 'res.partner'

    # Custom fields
    id_mobinome = fields.Integer(string='ID Mobinome')
    iri_mobinome = fields.Char(string='IRI Mobinome')
    id_project_task_mobinome = fields.Integer(string='ID Project Mobinome')
    iri_project_task_mobinome = fields.Char(string='IRI Project Mobinome')
    url_mobinome = fields.Char(string='URL Mobinome', compute='_get_url_mobinome', readonly=True)
    url_mobinome_file = fields.Char(string='URL Mobinome File', compute='_compute_url_mobinome_file')

    def _get_url_mobinome(self):
        for partner in self:
            partner.url_mobinome = ""
            if partner.id_mobinome:
                str_id = str(partner.id_mobinome)
                partner.url_mobinome = 'https://' + self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_url') + '/fr/customer/' + str_id + '/edit#historic'

    def _compute_url_mobinome_file(self):
        for res_partner in self:
            if res_partner.id_mobinome:
                res_partner.url_mobinome_file = "https://"+self.env['ir.config_parameter'].sudo().get_param('mobinome'
                                                                                                        '.mobinome_url')+"/fr/gmao/equipment/customerList/" + str(res_partner.id_mobinome)
            else:
                res_partner.url_mobinome_file = ''

    ###############
    # ODOO : POST #
    ###############
    @api.model
    def create(self, vals):
        # Call parent
        res = super(ResPartner, self).create(vals)

        # Post partner on mobinome
        json_mobinome = self.mobinome_post(res)
        if json_mobinome:
            res['id_mobinome'] = json_mobinome['id']
            res['iri_mobinome'] = json_mobinome['@id']

        try:
            # Create project if needed
            if self.env['ir.config_parameter'].sudo().get_param('mobinome.create_project_task_with_customer'):
                self.create_or_update_project_task(self)
        except Exception as error:
            _logger.debug('[ERROR] : %s', error)

        # Return resource
        return res

    ################
    # ODOO : PATCH #
    ################
    def write(self, vals):
        # Call parent
        res = super(ResPartner, self).write(vals)

        # Patch partner on mobinome
        for partner in self:
            if partner.iri_mobinome:
                self.mobinome_patch(partner)

        # Return resource
        return res

    #################
    # ODOO : DELETE #
    #################
    def unlink(self):
        # Delete partner on mobinome
        for partner in self:
            if partner.iri_mobinome:
                self.delete_partner(partner.iri_mobinome)

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

        try:
            # Create project if needed
            if self.env['ir.config_parameter'].sudo().get_param('mobinome.create_project_task_with_customer'):
                self.create_or_update_project_task(self)
        except Exception as error:
            _logger.debug('[ERROR] : %s', error)
        return True

    ##############
    # API : POST #
    ##############
    def mobinome_post(self, partner):
        try:
            # Request
            response = self.env['res.config.settings'].make_post_call(self.set_values(partner), '/api/customers')
        except Exception as error:
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
    def mobinome_patch(self, partner):
        try:
            # Update project if needed
            if self.env['ir.config_parameter'].sudo().get_param('mobinome.create_project_task_with_customer'):
                self.create_or_update_project_task(partner)

            # Request
            response = self.env['res.config.settings'].make_patch_call(self.set_values(partner), partner.iri_mobinome)

        except :
            return False

        # Log error if unsuccess patch
        if response and response.status_code != requests.codes.ok:
            _logger.error('Error: %d', response.status_code)
            return False

        return True

    ################
    # API : DELETE #
    ################
    def delete_partner(self, iri_partner):
        try:
            # Request
            response = self.env['res.config.settings'].make_api_call("DELETE", {}, '', iri_partner)
        except:
            return False

        # Log error if unsuccess delete
        if response and response.status_code != requests.codes.no_content:
            _logger.error('Error: %d', response.status_code)
            return False

        return True

    def create_or_update_project_task(self, partner):
        if partner['id_project_task_mobinome']:
            self.env['res.config.settings'].make_patch_call(
                self.env['project.task'].set_values({'name': partner['name']}, partner),
                partner['iri_project_task_mobinome'])
        else:
            response = self.env['res.config.settings'].make_post_call(
                self.env['project.task'].set_values({'name': partner['name']}, partner), '/api/projects')

            if response and response.status_code == requests.codes.created:
                json_data = response.json()

                partner['id_project_task_mobinome'] = json_data['id']
                partner['iri_project_task_mobinome'] = json_data['@id']

        return True

    ##############
    # SET VALUES #
    ##############
    def set_values(self, partner):
        values = {
            "name": partner['name'] or 'unnamed',
            "address1": partner['street'] or None,
            "address2": partner['street2'] or None,
            "city": partner['city'] or None,
            "zip": partner['zip'] or None,
            "vat": partner['vat'] or None,
            "phone": partner['phone'] or None,
            "mobile": partner['mobile'] or None,
            "email": partner['email'] or None,
            "website": partner['website'] or None,
            "country": partner['country_code'] or 'BE',
            "locale": partner['lang'] or 'fr_BE',
            "internalReference": 'ODOO_RES_PARTNER_' + str(partner['id']),
        }

        if not partner['iri_mobinome']:
            values['company'] = [self.env['mobinome.companies'].search([('id', '=', 
                                                                         self.env['ir.config_parameter'].sudo().get_param(
                                                                            'mobinome.mobinome_default_company_id'))])['iri_mobinome']] or None
        if self.env['ir.config_parameter'].sudo().get_param('mobinome.customer_have_lastname'):
            if partner['lastname']:
                values['lastname'] = partner['lastname']
            else:
                values['lastname'] = partner['name'] or 'unnamed'

            if partner['firstname']:
                values['firstname'] = partner['firstname']
            else:
                values['firstname'] = partner['name'] or 'unnamed'

        return values

    ############################
    # SHOW PARTNER IN MOBINOME #
    ############################
    def show_in_mobinome(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.url_mobinome,
        }
