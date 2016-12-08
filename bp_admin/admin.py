# -*- coding: utf-8 -*-
import webapp2, json
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb
from collections import OrderedDict, Counter
from wtforms import fields  
from bp_includes import forms, models, handlers, messages
from bp_includes.lib.basehandler import BaseHandler
from datetime import datetime, date, time, timedelta
import logging
from google.appengine.api import taskqueue
from google.appengine.api import users as g_users #https://cloud.google.com/appengine/docs/python/refdocs/modules/google/appengine/api/users#get_current_user


class AdminRequestHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_base.html', **params)

class AdminStatsReportsHandler(BaseHandler):
    def get(self):
        params = {}
        reports = models.Report.query()
        users = self.user_model.query()
        params['sum_users'] = users.count()
        params['sum_reports'] = reports.count()
        params['nickname'] = g_users.get_current_user().email().lower()
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['has_cic'] = self.app.config.get('has_cic')
        params['cartodb_cic_user'] = self.app.config.get('cartodb_cic_user')
        params['cartodb_cic_reports_table'] = self.app.config.get('cartodb_cic_reports_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        return self.render_template('stats/admin_summary.html', **params)

class AdminStatsOrganizationHandler(BaseHandler):
    """
    Handler to show the organization visualization page
    """
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')        
        return self.render_template('stats/admin_orgview.html', **params)

class AdminSendEmailListHandler(BaseHandler):
    def get(self):
        email_id=self.request.get('email_id')
        params = {
            "recipent": email_id,
        }        
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('emails/admin_send_email.html', **params)
            
    def post(self):
        
        def sendEmail (recipent,subject,body):
            email_url = self.uri_for('taskqueue-send-email')
            taskqueue.add(url=email_url, params={
                'to': recipent,
                'subject': subject,
                'body': body
            })
        
        body = self.request.get('emailbody')
        subject = self.request.get('subject')
        to = self.request.get('recipents')

        try:
            if 'ALLUSERS' in to:
                _users = self.user_model.query()
                for user in _users:
                    logging.info("raising taskqueue for user id %s to email %s" % (user.key.id(),user.email))
                    sendEmail (user.email,subject,body)
            else:
                for recipents in to.split(','):
                    sendEmail (recipents.strip(),subject,body)
            self.add_message('Correos enviados !', 'success')
        
        except Exception as e:
            logging.info('error in form: %s' % e)
            self.add_message('Algo ha ocurrido mal, por favor intenta de nuevo.', 'danger')
            pass
        
        return self.get()

class AdminManualHandler(BaseHandler):
    """
    Handler to show the manuals page
    """
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_manual.html', **params)

class AdminLogoutHandler(BaseHandler):
    def get(self):
        self.redirect(g_users.create_logout_url(dest_url=self.uri_for('landing')))

class AdminElectoralHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['zoom'] = self.configuration['map_zoom']
        params['zoom_mobile'] = self.configuration['map_zoom_mobile']
        params['lat'] = self.configuration['map_center_lat']
        params['lng'] = self.configuration['map_center_lng']
        params['right_sidenav_msg'] = self.app.config.get('right_sidenav_msg')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.configuration['cartodb_polygon_name']
        params['cartodb_polygon_full_name'] = self.configuration['cartodb_polygon_full_name']
        params['cartodb_polygon_cve_ent'] = self.configuration['cartodb_polygon_cve_ent']
        params['has_cic'] = self.app.config.get('has_cic')
        params['cartodb_cic_user'] = self.app.config.get('cartodb_cic_user')
        params['cartodb_cic_reports_table'] = self.app.config.get('cartodb_cic_reports_table')
        params['cartodb_markers_url'] = self.uri_for("landing", _full=True)+"default/materialize/images/markers/"
        
        return self.render_template('admin_electoral.html', **params)