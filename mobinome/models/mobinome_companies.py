# -*- coding: utf-8 -*-
import json
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class MobinomeCompanies(models.Model):
    # Model name
    _name = 'mobinome.companies'
    _description = 'Mobinome companies'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    iri_mobinome = fields.Char(string='IRI Mobinome')
