# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields
from isodate import parse_duration
from dateutil import parser
import logging
import base64

_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    # Model inherit
    _inherit = 'account.analytic.line'

    # Custom fields
    id_mobinome = fields.Integer(string='ID Mobinome')
    iri_mobinome = fields.Char(string='IRI Mobinome')

    def sync_services(self, sale_order_id=None, project_task_id=None):
        if sale_order_id or project_task_id:
            project_task_ids = False
            if sale_order_id:
                # Get sale order object
                sale_order = self.env['sale.order'].search([('id', '=', sale_order_id)])
                project_task_ids = sale_order['tasks_ids']
            if project_task_id:
                # Get sale order object
                project_task_ids = self.env['project.task'].search([('id', '=', project_task_id)])

            # Get project mobinome Id
            for project_task in project_task_ids:
                if project_task['id_mobinome']:
                    # Get services of project without events from Mobinome api call
                    mobinome_services = self.env['sale.order'].get_services('pagination=false&exported=false&exists[durationValidate]=1&state[gte]=1&exists[event]=false&project='
                                                                             + project_task['iri_mobinome'])
                    # Create timesheet in Odoo
                    for mobinome_service in mobinome_services:
                        self.create_service(mobinome_service, project_task)
                    self.env['sale.order'].stock_notification(services=mobinome_services, project_task=project_task)
                    # Get services of project with events and without internalReferenceEventCart from Mobinome api call
                    mobinome_services = self.env['sale.order'].get_services('pagination=false&exported=false&exists[durationValidate]=1&state[gte]=1&exists[event]=true&exists[event.internalReferenceEventCart]=false&project='
                                                                             + project_task['iri_mobinome'])
                    # Create timesheet in Odoo
                    for mobinome_service in mobinome_services:
                        self.create_service(mobinome_service, project_task)
                    self.env['sale.order'].stock_notification(services=mobinome_services, project_task=project_task)
                    # Loop on each task of project
                    for task in project_task['child_ids']:
                        if task['id_mobinome']:
                            # Get services of task from Mobinome api call
                            mobinome_internal_ref = 'ODOO_PROJECT_TASK_' + str(task['id'])
                            # mobinome_services = self.env['sale.order'].get_services('exported=false&pagination=false&exists[durationValidate]=1&state[gte]=1&event'
                            #                                                         '.internalReferenceEventCart=' + mobinome_internal_ref)
                            mobinome_services = self.env['sale.order'].get_services('exported=false&pagination=false&exists[durationValidate]=1&event'
                                                                                    '.internalReferenceEventCart=' + mobinome_internal_ref)
                            # Create timesheet in Odoo
                            for mobinome_service in mobinome_services:
                                self.create_service(mobinome_service, project_task)
                            self.env['sale.order'].stock_notification(services=mobinome_services, project_task=project_task)

        return True

    def sync_events(self, sale_order_id=None, project_task_id=None):
        if sale_order_id or project_task_id:
            project_tasks = False

            if sale_order_id:
                # Get sale order object
                sale_order = self.env['sale.order'].search([('id', '=', sale_order_id)])
                project_tasks = sale_order['tasks_ids']
            if project_task_id:
                # Get project object
                project_tasks = self.env['project.task'].search([('id', '=', project_task_id)])

            # Get project mobinome Id
            for project_task in project_tasks:
                if project_task['id_mobinome']:
                    mobinome_event_start = None
                    mobinome_event_end = None
                    mobinome_events = []
                    event_custom_states = []
                    event_dates = []

                    mobinome_events_project = self.env['sale.order'].get_events('exported=false&pagination=false&exists[internalReferenceEventCart]=false&project=' 
                                                                        + project_task['iri_mobinome'])
                    if mobinome_events_project:
                        mobinome_events = mobinome_events_project
                    # Loop on each task of project
                    for task in project_task['child_ids']:
                        if task['id_mobinome']:
                            # Get events from event cart in mobinome
                            mobinome_internal_ref = 'ODOO_PROJECT_TASK_' + str(task['id'])
                            mobinome_events_task = self.env['sale.order'].get_events('exported=false&pagination=false&internalReferenceEventCart='
                                                                                      + mobinome_internal_ref)
                            if mobinome_events_task:
                                # Concatenate events
                                mobinome_events += mobinome_events_task
                    # Create timesheet in Odoo
                    for mobinome_event in mobinome_events:
                        #Check if key exists
                        if 'eventCustomState' in mobinome_event:
                            # Get status of task
                            status = mobinome_event['eventCustomState']
                            if status not in event_custom_states:
                                event_custom_states.append(status)

                        # cut string to keep only date and hours
                        utc_start_string = mobinome_event['start'][:19]

                        # Get datetime object
                        start = datetime.strptime(utc_start_string, '%Y-%m-%dT%H:%M:%S')

                        # Update mobinome_event_start if it's None or greater than the new start
                        if mobinome_event_start is None or start < mobinome_event_start:
                            mobinome_event_start = start

                        # format start for d/m/Y H:i
                        date = start.strftime('%d/%m/%Y %H:%M')

                        if 'end' in mobinome_event:
                            # cut string to keep only date and hours
                            utc_end_string = mobinome_event['end'][:19]

                            # Get datetime object
                            end = datetime.strptime(utc_end_string, '%Y-%m-%dT%H:%M:%S')

                            # format end for d/m/Y H:i and concat to date
                            date += ' -> ' + end.strftime('%d/%m/%Y %H:%M')

                            # Update mobinome_event_end if it's None or less than the new end and greater than start
                            if (mobinome_event_end is None or end > mobinome_event_end) and (mobinome_event_start <= end):
                                mobinome_event_end = end

                        event_dates.append(date)

                    # Send messages to odoo chat project & fill planned_date_begin field
                    if len(event_dates) > 0:
                        # Sort the event_dates list by start date
                        event_dates.sort(key=lambda date: datetime.strptime(date.split(' -> ')[0], '%d/%m/%Y %H:%M'))
                        # Chat message
                        body = '<ul>'
                        for date in event_dates:
                            body += '<li>' + date + '</li>'
                        body += '</ul>'

                        # Note in project task
                        self.send_notification('project.task', body, project_task['id'])

                        # Update project
                        if mobinome_event_start and (not project_task.planned_date_begin or (project_task.planned_date_begin and mobinome_event_start < project_task.planned_date_begin)):
                            project_task.write({
                                'planned_date_begin': mobinome_event_start,
                            })
                        if mobinome_event_end and (not project_task.date_deadline or (project_task.date_deadline and mobinome_event_end > project_task.date_deadline)):
                            project_task.write({
                                'date_deadline': mobinome_event_end
                            })
                        self.env.cr.commit()
                        for mobinome_event in mobinome_events:
                            self.env['sale.order'].patch_event(mobinome_event)

        return True

    ####################
    # CREATE : service #
    ####################
    def create_service(self, service, project_from_service=None):
        try:
            mobiner = service.get('mobiner', {})
            mobiner_id = mobiner.get('@id', False)
            mobinome_project = service.get('project', {})
            mobinome_project_id = mobinome_project.get('id', False)
            mobinome_event = service.get('event', {})
            mobinome_task_id = mobinome_event.get('externalReferenceEventCart', False)

            employee = self.env['hr.employee'].search([('iri_mobinome', '=', mobiner_id)], limit=1)
            project_task = project_from_service if project_from_service else self.env['project.task'].search(
                [('id_mobinome', '=', mobinome_project_id)], limit=1)
            task = self.env['project.task'].search([('id', '=', int(mobinome_task_id))], limit=1) if mobinome_task_id else False
          
            materials = service.get('materials')
            for service_material in materials:
                # Set values of timesheet
                if service_material.get('material').get('internalReference') and 'ODOO_EMPLOYEE_' in service_material.get('material').get('internalReference'):
                    employee_id = self.extract_employee_number(service_material.get('material').get('internalReference'))
                    mat_employee = self.env['hr.employee'].search([('id', '=', employee_id)])
                    if mat_employee:
                        account_analytic_line_values = {
                            'task_id': task.id if task else None,
                            'project_id': project_task.project_id.id,
                            'employee_id': mat_employee.id,
                            'name': service.get('comment', '/'),
                            'date': parser.parse(service['inputDate']),
                            'unit_amount': parse_duration(
                                service['durationValidateWithTravelAndOvertimeAndBreakAndOther']).total_seconds() / 3600,
                            'id_mobinome': service_material.get('id'),
                            'iri_mobinome': service_material.get('@id')
                        }
                        # Create or update timesheet in Odoo
                        account_analytic_line = self.env['account.analytic.line'].sudo().search([('iri_mobinome', '=', service_material.get('@id'))])
                        if account_analytic_line:
                            account_analytic_line.sudo().write(account_analytic_line_values)
                        else:
                            self.env['account.analytic.line'].sudo().create(account_analytic_line_values)
                        self.env.cr.commit()
                        self.env['sale.order'].patch_service(service)
            if employee and project_task:
                # Set values of timesheet
                account_analytic_line_values = {
                    'task_id': task.id if task else None,
                    'project_id': project_task.project_id.id,
                    'employee_id': employee.id,
                    'name': service.get('comment', '/'),
                    'date': parser.parse(service['inputDate']),
                    'unit_amount': parse_duration(
                        service['durationValidateWithTravelAndOvertimeAndBreakAndOther']).total_seconds() / 3600,
                    'id_mobinome': service['id'],
                    'iri_mobinome': service['@id']
                }

                # Create or update timesheet in Odoo
                account_analytic_line = self.env['account.analytic.line'].sudo().search([('iri_mobinome', '=', service['@id'])])
                if account_analytic_line:
                    account_analytic_line.sudo().write(account_analytic_line_values)
                else:
                    self.env['account.analytic.line'].sudo().create(account_analytic_line_values)
                if self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_default_end_stage_id') and task.stage_id and task.stage_id.id != int(self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_default_end_stage_id')):
                    task.write({'stage_id': int(self.env['ir.config_parameter'].sudo().get_param('mobinome.mobinome_default_end_stage_id'))})
                self.env.cr.commit()
                self.env['sale.order'].patch_service(service)
        except Exception as e:
            _logger.error(e)

        return True

    #######################
    # SEND : notification #
    #######################
    def send_notification(self, model, body, res_id):
        return self.env['mail.message'].create({
            'subject': 'Mobinome Event planned :',
            'body': body,
            'model': model,
            'res_id': res_id,
            'message_type': 'notification',
            'author_id': 2,  # Odoo bot
        })

    def extract_employee_number(self, internal_reference):
        # Search for the substring "ODOO_EMPLOYEE_" in internal_reference
        index = internal_reference.find("ODOO_EMPLOYEE_")
        if index == -1:
            return None
        # Calculate the start index of the employee number
        start_index = index + len("ODOO_EMPLOYEE_")
        # Extract the employee number
        employee_number = internal_reference[start_index:]
        return int(employee_number)
