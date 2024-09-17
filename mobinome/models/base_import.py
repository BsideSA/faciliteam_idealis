from odoo import models

class CustomImport(models.TransientModel):
    _inherit = 'base_import.import'

    def execute_import(self, fields, columns, options, dryrun=False):
        if dryrun:
            self.env.context = dict(self.env.context, is_test_import=True)
        return super(CustomImport, self).execute_import(fields, columns, options, dryrun)
