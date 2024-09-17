# -*- coding: utf-8 -*-
import logging
import requests

from odoo import models
import collections.abc

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    # Model inherit
    _inherit = 'sale.order'

    def import_mobinome(self):
        self.env['res.config.settings'].sync_mobinome()
        return True

    def sync_all(self):
        self.env['account.analytic.line'].sync_services(self.id)
        self.env['account.analytic.line'].sync_events(self.id)
        return True

    ################
    # Sync : Stock #
    ################
    def sync_stock(self, project_task_id=None):
        try:
            if project_task_id:
                project_tasks = self.env['project.task'].search([('id', '=', project_task_id)])
            else:
                # Loop on each project of sale order and check if only one project
                if len(self['tasks_ids']) == 1:
                    project_tasks = [self['tasks_ids']]
                else:
                    project_tasks = self['tasks_ids']
            for project_task in project_tasks:
                self.env['account.analytic.line'].sync_services(sale_order_id=None, project_task_id=project_task.id)
            return True
        except:
            return False

    ################
    # Stock : Notif #
    ################
    def stock_notification(self, services=None, project_task=None):
        try:
            if services and project_task:
                has_service_articles = False
                body = '<ol>'
                # Loop on each service to get real GMAO used
                for service in services:
                    if service.get('articles'):
                        has_service_articles = True
                        # Init Body of message
                        body += '<li><strong><a target="_blank" href="https://' + self.env[
                            'ir.config_parameter'].sudo().get_param('mobinome.mobinome_url') + '/fr/service/' + str(service[
                                                                                                                        'id']) + '/edit' + '">' + \
                                service['event']['title'] + ' : </a></strong></li>'

                        body += '<ul>'
                        for article in service['articles']:
                            body += '<li>' + str(article['quantity']) + 'x ' + article['article']['name'] + '</li>'

                        body += '</ul>'
                body += '</ol>'

                # Note in project
                if has_service_articles:
                    self.send_notification('project.task', body, project_task['id'])

                # Get sale order
                sale_order = project_task['sale_order_id']
                if sale_order:
                    # Get stock pickings
                    stock_pickings = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)])
                    # Note in sale order
                    self.send_notification('sale.order', body, sale_order['id'])

                    # Note in each stock picking of sale order
                    for stock_picking in stock_pickings:
                        self.send_notification('stock.picking', body, stock_picking['id'])
            return True
        except:
            return False

    ##################
    # GET : services #
    ##################
    def get_services(self, filters):
        # Request to Mobinome
        response = self.env['res.config.settings'].make_api_call("GET", '', {}, '/api/services?' + filters)

        services = []
        if response:
            # Check if multiple pages
            if hasattr(response.json()['hydra:view'], 'hydra:last'):
                for page in response.json()['hydra:member']:
                    for service in page:
                        services.append(service)
            else:
                services = response.json()['hydra:member']
        return services

    ##################
    # PATCH : service #
    ##################
    def patch_service(self, service):
        if service and service['@id']:
            # Request
            response = self.env['res.config.settings'].make_patch_call({"exported": True}, service['@id'])

            # Log error if unsuccess patch
            if response and response.status_code != requests.codes.ok:
                _logger.error('Error: %d', response.status_code)
                return False

        return True

    ###############
    # GET : event #
    ###############
    def get_events(self, filters):
        # Request to Mobinome
        response = self.env['res.config.settings'].make_api_call("GET", '', {}, '/api/events?' + filters)

        events = []
        if response:
            # Check if multiple pages
            if hasattr(response.json()['hydra:view'], 'hydra:last'):
                for page in response.json()['hydra:member']:
                    for event in page:
                        events.append(event)
            else:
                events = response.json()['hydra:member']
        return events

    ##################
    # PATCH : event #
    ##################
    def patch_event(self, event):
        if event and event['@id']:
            # Request
            response = self.env['res.config.settings'].make_patch_call({"exported": True}, event['@id'])

            # Log error if unsuccess patch
            if response and response.status_code != requests.codes.ok:
                _logger.error('Error: %d', response.status_code)
                return False

        return True

    #######################
    # SEND : notification #
    #######################
    def send_notification(self, model, body, res_id):
        return self.env['mail.message'].create({
            'subject': 'Mobinome Services registred :',
            'body': body,
            'model': model,
            'res_id': res_id,
            'message_type': 'notification',
            'author_id': 2,  # Odoo bot
        })
