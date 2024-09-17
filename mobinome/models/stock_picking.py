# -*- coding: utf-8 -*-
import logging

import requests

from odoo import models, api

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    # Model inherit
    _inherit = 'stock.picking'

    ################
    # ODOO : PATCH #
    ################
    def write(self, vals):
        # Call parent
        res = super(StockPicking, self).write(vals)

        # Patch stock on mobinome event cart
        for stock in self:
            # Link stock on mobinome event cart
            self.mobinome_update(stock)

        # Return resource
        return res

    #################
    # ODOO : DELETE #
    #################
    def unlink(self):
        # Delete stock on mobinome
        for stock in self:
            if stock.iri_mobinome:
                self.delete_stock(stock.iri_mobinome)

        # Call parent
        res = super().unlink()

        # Return resource
        return res

    ###################################
    # API : CREATE EVENT CART ARTICLE #
    ###################################
    def mobinome_update(self, stock):
        try:
            # Take only stock with sales
            sale_order = stock['sale_id'] if stock['sale_id'] else None

            # Check if sale order linked to delivery order and stockable article linked to sale order
            if sale_order:
                for line in sale_order['order_line']:
                    if line['product_id'] and line['product_id']['detailed_type'] == 'product':
                        # Check if article is exist in mobinome
                        if not line['product_id']['id_mobinome']:
                            # Create article on mobinome
                            json_mobinome = self.env['product.template'].mobinome_post(line['product_id'])

                            # Update odoo object
                            if json_mobinome:
                                line['product_id']['id_mobinome'] = json_mobinome['id']
                                line['product_id']['iri_mobinome'] = json_mobinome['@id']

                        # Get tasks linked to sale order
                        project_tasks = self.env['project.task'].search([('sale_order_id', '=', sale_order['id'])])

                        # Get all event cart from Mobinome project tasks
                        event_carts = []
                        for task in project_tasks:
                            if task['iri_mobinome']:
                                # Request
                                event_cart_response = self.env['res.config.settings'].make_api_call("GET", 'application/Id+json', {}, (
                                        task['iri_mobinome']))

                                if event_cart_response.ok:
                                    event_carts.append(event_cart_response.json())

                        # Link articles to event_cart
                        for event_cart in event_carts:
                            can_post = True
                            for article in event_cart['articles']:
                                # Check if event_cart_article is exist in mobinome
                                if article['article']['id'] == line['product_id']['id_mobinome']:
                                    can_post = False
                                    break

                            if can_post:
                                # Post request
                                self.env['res.config.settings'].make_post_call(
                                    self.set_values(line, event_cart), '/api/event_cart_articles')
                return True
        except:
            return False

    ################
    # API : DELETE #
    ################
    def delete_stock(self, iri_stock):
        try:
            # Request
            response = self.env['res.config.settings'].make_delete_call(iri_stock)
        except:
            return False

        # Log error if unsuccess delete
        if response and response.status_code != requests.codes.no_content:
            _logger.error('Error: %d', response.status_code)
            return False

        return True

    ####################
    # API : SET VALUES #
    ####################
    def set_values(self, article, event_cart):
        return {
            "eventCart": event_cart['@id'],
            "article": article['product_id']['iri_mobinome'],
            "quantity": article['product_uom_qty']
        }

    def sync_stock(self):
        self.env['sale.order'].sync_stock()

        return True
