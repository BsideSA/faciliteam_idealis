# -*- coding: utf-8 -*-
{
    'name': "Mobinome",
    'license': 'LGPL-3',
    'summary': "Connector between Odoo and Mobinome",
    'description': """
        The connector allows you to synchronize the data in Odoo to Mobinome.
        Several elements can be synchronized:
            - Contacts
            - Projects
            - Project Tasks
            - Employees
        After configuration, at each creation/modification/deletion/archiving/unarchiving/..., your data will be updated in Mobinome.
    """,
    'author': "Bside S.A.",
    'website': "https://www.mobinome.com",
    'category': 'Technical',
    'version': '17.01',
    'images': ['static/image/cover.jpg'],
    'depends': ['base', 'contacts', 'project', 'hr_timesheet', 'sale_project', 'stock', 'base_import', 'sale_stock', 'fac_fsm'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee.xml',
        'views/product_category.xml',
        'views/product_template.xml',
        'views/project_task.xml',
        'views/project_tasks_kanban.xml',
        'views/res_config_settings.xml',
        'views/res_partner_form.xml',
        'views/sale_order_form.xml',
        'views/stock_picking_form.xml',
    ],
}
