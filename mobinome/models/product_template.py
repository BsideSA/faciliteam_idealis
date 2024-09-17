# -*- coding: utf-8 -*-
import logging

import requests

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    # Model inherit
    _inherit = 'product.template'

    # Custom fields
    id_mobinome = fields.Integer(string='ID')
    iri_mobinome = fields.Char(string='IRI')
    send_to_mobinome = fields.Boolean(string='Send to mobinome', default=False)

    ###############
    # ODOO : POST #
    ###############
    @api.model
    def create(self, vals):
        # Call parent
        res = super(ProductTemplate, self).create(vals)

        # Post article on mobinome
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
        res = super(ProductTemplate, self).write(vals)

        # Patch article on mobinome
        for article in self:
            if article.iri_mobinome:
                self.mobinome_patch(article)

        # Return resource
        return res

    #################
    # ODOO : DELETE #
    #################
    def unlink(self):
        # Delete article on mobinome
        for article in self:
            if article.iri_mobinome:
                self.delete_article(article.iri_mobinome)

        # Call parent
        res = super().unlink()

        # Return resource
        return res

    ##############
    # API : POST #
    ##############
    def mobinome_post(self, article):
        try:
            if not article['send_to_mobinome']:
                return False

            # Set values to send
            values = self.set_values(article)

            if article['detailed_type'] == 'consu':
                iri = '/api/consumables'
            elif article['detailed_type'] == 'product':
                iri = '/api/articles'

            # Request
            response = self.env['res.config.settings'].make_post_call(values, iri)

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

    ###############
    # API : PATCH #
    ###############
    def mobinome_patch(self, article):
        try:
            if not article['send_to_mobinome']:
                return False

            # Set values to send
            values = self.set_values(article)

            # Request
            response = self.env['res.config.settings'].make_patch_call(values, article['iri_mobinome'])

            # Log error if unsuccess patch
            if response and response.status_code != requests.codes.ok:
                _logger.error('Error: %d', response.status_code)
                return False
        except:
            return False

    ################
    # API : DELETE #
    ################
    def delete_article(self, iri_article):
        try:
            # Request
            response = self.env['res.config.settings'].make_delete_call(iri_article)
        except:
            return False

        # Log error if unsuccess delete
        if response and response.status_code != requests.codes.no_content:
            _logger.error('Error: %d', response.status_code)
            return False

        return True

    ######################
    # SET VALUES TO SEND #
    ######################
    def set_values(self, article):
        article_type = article['detailed_type']
        values = {
            "name": article['name'],
            "externalReference": str(article['id']),
            "internalReference": "ODOO_PRODUCT_TEMPLATE_" + str(article['id']),
        }

        # Check if all categories exists in mobinome
        if self.env['product.category'].search(
                ['|', '|', '|', ('id_article_mobinome', '=', False), ('id_article_mobinome', '=', 0),
                 ('id_consumable_mobinome', '=', False), ('id_consumable_mobinome', '=', 0)]):
            # Sync categories
            self.env['product.category'].sync_categories_article(False)

        if article_type == 'product':
            values['costSale'] = float(article['list_price'])
            values['category'] = self.env['res.config.settings'].make_api_call("GET", 'application/json', {}, (
                    '/api/article_categories/?externalReference=' + str(article['categ_id']['id']))).json()[
                'hydra:member'][0]['@id']
        elif article_type == 'consu':
            values['category'] = self.env['res.config.settings'].make_api_call("GET", 'application/json', {}, (
                    '/api/consumable_categories/?externalReference=' + str(article['categ_id']['id']))).json()[
                'hydra:member'][0]['@id']

        return values

    def send_mobinome(self):
        if self['id_mobinome']:
            self.mobinome_patch(self)
        else:
            json_mobinome = self.mobinome_post(self)

            if json_mobinome:
                self['id_mobinome'] = json_mobinome['id']
                self['iri_mobinome'] = json_mobinome['@id']
        return True
