# -*- coding: utf-8 -*-
import logging

import requests

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    # Model inherit
    _inherit = 'product.category'

    # Custom fields
    id_article_mobinome = fields.Integer(string='ID article')
    id_consumable_mobinome = fields.Integer(string='ID consumable')
    iri_article_mobinome = fields.Char(string='IRI article')
    iri_consumable_mobinome = fields.Char(string='IRI consumable')
    lvl_mobinome = fields.Integer(string='LVL')

    ###############
    # ODOO : POST #
    ###############
    @api.model
    def create(self, vals):
        # Call parent
        res = super(ProductCategory, self).create(vals)

        # Get all articles categories from mobinome
        mobinome_article_categories = self.env['res.config.settings'].make_api_call("GET", 'application/json', {}, (
            '/api/article_categories?pagination=false')).json()['hydra:member']

        # Get all articles categories from mobinome
        mobinome_consumable_categories = self.env['res.config.settings'].make_api_call("GET", 'application/json', {}, (
            '/api/consumable_categories?pagination=false')).json()['hydra:member']

        # Post category on mobinome
        json_response = self.mobinome_post(res, mobinome_article_categories, mobinome_consumable_categories)

        # save mobinome infos
        self.sync_mobinome(json_response)

        # Return resource
        return res

    ################
    # ODOO : PATCH #
    ################
    def write(self, vals):
        # Call parent
        res = super(ProductCategory, self).write(vals)

        # Get all articles categories from mobinome
        mobinome_article_categories = self.env['res.config.settings'].make_api_call("GET", 'application/json', {}, (
            '/api/article_categories?pagination=false')).json()['hydra:member']

        # Get all articles categories from mobinome
        mobinome_consumable_categories = self.env['res.config.settings'].make_api_call("GET", 'application/json', {}, (
            '/api/consumable_categories?pagination=false')).json()['hydra:member']

        # Patch category on mobinome
        for category in self:
            if category['iri_article_mobinome'] or category['iri_consumable_mobinome']:
                self.mobinome_patch(category, mobinome_article_categories, mobinome_consumable_categories)

        # Return resource
        return res

    #################
    # ODOO : DELETE #
    #################
    def unlink(self):
        # Delete category on mobinome
        for category in self:
            if category['iri_article_mobinome']:
                self.delete_category(category['iri_article_mobinome'])
            elif category['iri_consumable_mobinome']:
                self.delete_category(category['iri_consumable_mobinome'])

        # Call parent
        res = super().unlink()

        # Return resource
        return res

    ##############
    # API : POST #
    ##############
    def mobinome_post(self, category, mobinome_article_categories, mobinome_consumable_categories):
        try:
            # Set values to send
            values = self.set_values(category, mobinome_article_categories)

            # Request
            response_article = self.env['res.config.settings'].make_post_call(values, '/api/article_categories')

            # Set values to send
            values = self.set_values(category, mobinome_consumable_categories)

            # Request
            response_consumable = self.env['res.config.settings'].make_post_call(values, '/api/consumable_categories')

            # If success, return data
            data = {
                'article': None,
                'consumable': None,
            }
            if response_article and response_article.status_code == requests.codes.created:
                data['article'] = response_article.json()
            if response_consumable and response_consumable.status_code == requests.codes.created:
                data['consumable'] = response_consumable.json()

            return data

        except:
            return False

    ###############
    # API : PATCH #
    ###############
    def mobinome_patch(self, category, mobinome_article_categories, mobinome_consumable_categories):
        try:
            # Request
            if category['iri_article_mobinome']:
                # Set values to send
                values = self.set_values(category, mobinome_article_categories)

                # Request
                response = self.env['res.config.settings'].make_patch_call(values, category['iri_article_mobinome'])
            if category['iri_consumable_mobinome']:
                # Set values to send
                values = self.set_values(category, mobinome_consumable_categories)

                # Request
                response = self.env['res.config.settings'].make_patch_call(values, category['iri_consumable_mobinome'])

            # Log error if unsuccess patch
            if response and response.status_code != requests.codes.ok:
                _logger.error('Error: %d', response.status_code)
                return False
        except:
            return False

    ################
    # API : DELETE #
    ################
    def delete_category(self, iri_category):
        try:
            # Request
            response = self.env['res.config.settings'].make_delete_call(iri_category)
        except:
            return False

        # Log error if unsuccess delete
        if response and response.status_code != requests.codes.no_content:
            _logger.error('Error: %d', response.status_code)
            return False

        return True

    ########################
    # GET LEVEL CATEGORIES #
    ########################
    def get_level(self, category):
        # init level
        lvl_mobinome = 1

        if hasattr(category, 'parent_id'):
            # get first parent category
            parent = category.parent_id
            # count level
            while parent.id:
                parent = parent.parent_id
                lvl_mobinome += 1
        return lvl_mobinome

    ######################
    # SET VALUES TO SEND #
    ######################
    def set_values(self, category, mobinome_categories):
        values = {
            "name": category['name'],
            "lvl": self.get_level(category),
            "externalReference": str(category['id']),
            "internalReference": "ODOO_PRODUCT_CATEGORY_" + str(category['id']),
        }
        if hasattr(category, 'parent_id') and category['parent_id'].id:
            # Search parent in mobinome categories
            for mc in mobinome_categories:
                if 'externalReference' in mc and mc['externalReference'] == str(category['parent_id']['id']):
                    if '@id' in mc:
                        values['parent'] = mc['@id']
                        break
        else:
            # Search Root category from mobinome
            for mc in mobinome_categories:
                if mc['lvl'] == 0:
                    values['parent'] = mc['@id']
                    break

        return values

    #######################
    # BIND MOBINOME INFOS #
    #######################
    def sync_mobinome(self, json_response):
        # Save Infos of Article Category
        if json_response['article']:
            self.write({
                'id_article_mobinome': json_response['article']['id'],
                'iri_article_mobinome': json_response['article']['@id'],
            })
        # Save Infos of Consumable Category
        if json_response['consumable']:
            self.write({
                'id_consumable_mobinome': json_response['consumable']['id'],
                'iri_consumable_mobinome': json_response['consumable']['@id'],
            })

    #######################
    # SYNC ALL CATEGORIES #
    #######################
    def sync_categories_article(self, patch=True):
        try:
            # Get all article categories from Odoo
            categories = self.env['product.category'].search([], 0, None, order='complete_name asc')

            # Get all articles categories from mobinome
            mobinome_article_categories = \
                self.env['res.config.settings'].make_api_call("GET", 'application/json', {}, (
                    '/api/article_categories?pagination=false')).json()['hydra:member']

            # Get all articles categories from mobinome
            mobinome_consumable_categories = \
                self.env['res.config.settings'].make_api_call("GET", 'application/json', {}, (
                    '/api/consumable_categories?pagination=false')).json()['hydra:member']

            # Sync article categories
            for category in categories:
                # Patch if already exists. Post if not.
                if category['iri_article_mobinome'] and category['iri_consumable_mobinome']:
                    # PATCH
                    if patch:
                        category.mobinome_patch(category, mobinome_article_categories, mobinome_consumable_categories)
                else:
                    # POST
                    json_response = self.mobinome_post(category, mobinome_article_categories,
                                                       mobinome_consumable_categories)

                    # Update mobinome infos
                    mobinome_article_categories.append(json_response['article'])
                    mobinome_consumable_categories.append(json_response['consumable'])
                    category.sync_mobinome(json_response)

            return True
        except:
            _logger.error("Error during sync articles categories")
            return False
