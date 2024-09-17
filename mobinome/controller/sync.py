# -*- coding: utf-8 -*-
from odoo.http import Controller, route, request
from werkzeug.urls import url_encode
import logging

_logger = logging.getLogger(__name__)


class SyncController(Controller):
    @route('/mobinome/synchronization/sync_partners', auth='public')
    def route_sync_partners(self):
        self.sync_contacts()

        return request.redirect("/")

    @route('/mobinome/synchronization/sync_project_tasks', auth='public')
    def route_sync_project_tasks(self):
        self.sync_project_tasks()

        return request.redirect("/")

    @route('/mobinome/synchronization/sync_employees', auth='public')
    def route_sync_employees(self):
        self.sync_employees()

        return request.redirect("/")

    @route('/mobinome/synchronization/sync_categories_article', auth='public')
    def route_sync_categories_article(self):
        self.sync_categories_article()

        return request.redirect("/")

    @route('/mobinome/synchronization/sync_articles', auth='public')
    def route_sync_articles(self):
        self.sync_articles()

        return request.redirect("/")

    @route('/mobinome/synchronization/sync_services', auth='public')
    def route_sync_services(self):
        self.sync_services()

        return request.redirect("/")

    @route('/mobinome/synchronization/sync_services_from_timesheet', auth='public')
    def sync_services_from_timesheet(self):
        self.sync_services()

        action_id = request.env.ref('hr_timesheet.timesheet_action_all')
        return request.redirect('/web?&#min=1&limit=80&view_type=grid&model=account.analytic.line&action=%s' % (action_id))

    @route('/mobinome/synchronization/sync_stock', auth='public')
    def route_sync_stock(self):
        request.env['sale.order'].sync_stock()

        return request.redirect("/")

    ###################
    # Sync : contacts #
    ###################
    def sync_contacts(self):
        try:
            # Get all partners
            partners = request.env['res.partner'].with_context(active_test=False).search([])

            # Sync contacts
            return self.sync_from_odoo_to_mobinome(partners)
        except:
            _logger.error("Error during sync contacts")
            return False

    ###################
    # Sync : project_tasks #
    ###################
    def sync_project_tasks(self):
        try:
            # Get all project_tasks
            project_tasks = request.env['project.task'].with_context(active_test=False).search([])

            # Sync project_tasks
            self.sync_from_odoo_to_mobinome(project_tasks)

            # Sync tasks
            for project_task in project_tasks:
                if project_task['id_mobinome']:
                    for task in project_task['child_ids']:
                        self.sync_from_odoo_to_mobinome(task)

            return True
        except:
            _logger.error("Error during sync project_tasks")
            return False

    ###################
    # Sync : employees #
    ###################
    def sync_employees(self):
        try:
            # Get all employees
            employees = request.env['hr.employee'].with_context(active_test=False).search([])

            # Sync employees
            return self.sync_from_odoo_to_mobinome(employees)

        except:
            _logger.error("Error during sync employees")
            return False

    #############################
    # Sync : categories article #
    #############################
    def sync_categories_article(self):
        return request.env['product.category'].sync_categories_article()

    ###################
    # Sync : articles #
    ###################
    def sync_articles(self):
        try:
            # Get all articles
            articles = request.env['product.template'].with_context(active_test=False).search(
                [('type', '!=', 'service')])

            # Sync articles
            return self.sync_from_odoo_to_mobinome(articles)

        except:
            _logger.error("Error during sync articles")
            return False

    ########################################
    # Sync : Objects from Odoo to Mobinome #
    ########################################
    def sync_from_odoo_to_mobinome(self, odoo_objects):
        # Loop on each objects
        index = 0
        for odoo_object in odoo_objects:
            index = index + 1
            # Patch if already exists
            if odoo_object['iri_mobinome']:
                odoo_object.mobinome_patch(odoo_object)
            # Post otherwise (only if active)
            elif (hasattr(odoo_object, 'active') and odoo_object.active) or not hasattr(odoo_object, 'active'):
                # Get json returned by Mobinome
                json_mobinome = odoo_object.mobinome_post(odoo_object)

                # Update odoo object
                if json_mobinome:
                    odoo_object['id_mobinome'] = json_mobinome['id']
                    odoo_object['iri_mobinome'] = json_mobinome['@id']

            # Send infos to database for 300 objects
            if index % 300 == 0:
                request.env.cr.commit()

        return True

    ###################
    # Sync : services #
    ###################
    def sync_services(self):
        for task in request.env['project.task'].search([('iri_mobinome', '!=', False), ('parent_id', '=', False)]):
            task.sync_all()
        return True
