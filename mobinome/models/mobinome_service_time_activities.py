# -*- coding: utf-8 -*-
import json
import logging

import requests

from odoo import models, fields

_logger = logging.getLogger(__name__)


class MobinomeServiceTimeActivities(models.Model):
    # Model name
    _name = 'mobinome.service.time.activities'
    _description = 'Mobinome service time activities'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    iri_mobinome = fields.Char(string='IRI Mobinome')
    color = fields.Char(string="Color")

    def refresh(self):
        response = self.env['res.config.settings'].make_api_call("GET", 'application/json', {}, '/api'
                                                                                                '/service_time_activities?pagination=false')
        if response and response.status_code == requests.codes.ok:
            for service_time_activity in self.env['mobinome.service.time.activities'].search([]):
                service_time_activity.unlink()

            json_data = response.json()
            for service_time_activity in json_data['hydra:member']:
                self.env['mobinome.service.time.activities'].create({
                    'name': service_time_activity['name'],
                    'iri_mobinome': service_time_activity['@id'],
                    'color': service_time_activity['color'],
                })
        elif response and response.status_code:
            _logger.error('Error: %d', response.status_code)
