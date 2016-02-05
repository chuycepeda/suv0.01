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


class AdminLogoutHandler(BaseHandler):
    def get(self):
        self.redirect(g_users.create_logout_url(dest_url=self.uri_for('landing')))

class AdminSendEmailListHandler(BaseHandler):
    def get(self):
        email_id=self.request.get('email_id')
        params = {
            "recipent": email_id,
        }        
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_send_email.html', **params)
            
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
            self.add_message('Emails sent !', 'success')
        
        except Exception as e:
            logging.info('error in form: %s' % e)
            self.add_message('Something went wrong.', 'danger')
            pass
        
        return self.get()

class AdminSummaryHandler(BaseHandler):
    def get(self):
        params = {}
        reports = models.Report.query()
        users = self.user_model.query()
        params['sum_users'] = users.count()
        params['sum_reports'] = reports.count()
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_summary.html', **params)

