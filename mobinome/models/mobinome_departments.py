# -*- coding: utf-8 -*-
import json
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class MobinomeDepartments(models.Model):
    # Model name
    _name = 'mobinome.departments'
    _description = 'Mobinome departments'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    iri_mobinome = fields.Char(string='IRI Mobinome')
