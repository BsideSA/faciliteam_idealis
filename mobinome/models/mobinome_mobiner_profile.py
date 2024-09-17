# -*- coding: utf-8 -*-
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class MobinomeMobinerProfile(models.Model):
    # Model name
    _name = 'mobinome.mobiner.profile'
    _description = 'Mobinome Mobiner profile'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    iri_mobinome = fields.Char(string='IRI Mobinome')
