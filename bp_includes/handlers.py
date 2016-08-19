# -*- coding: utf-8 -*-
"""
    A real simple app for using webapp2 with auth and session.
    Routes are setup in routes.py and added in main.py
"""

# ------------------------------------------------------------------------------------------- #
"""                                     LIBRARY IMPORTS                                     """
# ------------------------------------------------------------------------------------------- #
#PYTHON
import logging
import json
import requests
from datetime import date, timedelta, datetime
import time
from collections import OrderedDict, Counter

#APPENGINE
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.i18n import gettext as _
from webapp2_extras.appengine.auth.models import Unique
from google.appengine.ext import ndb, blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import taskqueue, users, images
from google.appengine.api.datastore_errors import BadValueError
from google.appengine.runtime import apiproxy_errors
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext.webapp.mail_handlers import BounceNotificationHandler

#LOCAL
import models, messages, forms
from lib import utils, captcha, bitly
from lib.cartodb import CartoDBAPIKey, CartoDBException
from lib.basehandler import BaseHandler
from lib.decorators import user_required, taskqueue_method


# ------------------------------------------------------------------------------------------- #
"""                                     GLOBAL METHODS                                      """
# ------------------------------------------------------------------------------------------- #

#CAPTCHA
def captchaBase(self):
    if self.app.config.get('captcha_public_key') == "" or \
                    self.app.config.get('captcha_private_key') == "":
        chtml = '<div class="alert alert-danger"><strong>Error</strong>: You have to ' \
                '<a href="http://www.google.com/recaptcha/" target="_blank">sign up ' \
                'for API keys</a> in order to use reCAPTCHA.</div>' \
                '<input type="hidden" name="recaptcha_challenge_field" value="manual_challenge" />' \
                '<input type="hidden" name="recaptcha_response_field" value="manual_challenge" />'
    else:
        chtml = captcha.displayhtml(public_key=self.app.config.get('captcha_public_key'))
    return chtml

#USER INFO
def disclaim(_self, **kwargs):
    """
        This method is used as a validator previous to loading a get handler for most of user's screens.
        It can either redirect user to login, edit cfe data and edit home data, or
        return required params, user_info and user_home values.
    """
    _params = {}
    user_info = _self.user_model.get_by_id(long(_self.user_id))        
    
    #0: FOR PERSONALIZATION MEANS WE TAKE CARE OF BEST DATA TO ADDRESS USER
    _params['email'] = user_info.email
    _params['last_name'] = user_info.last_name
    _params['last_name2'] = user_info.last_name2 if user_info.last_name2 != None else ""
    _params['last_name_i'] = user_info.last_name[0] + "." if len(user_info.last_name) >= 1 else ""
    _params['name'] = user_info.name
    _params['name_i'] = user_info.name[0].upper()
    _params['role'] = 'Administrator' if user_info.role == 'Admin' else 'Member'
    _params['phone'] = user_info.phone if user_info.phone != None else ""
    _params['gender'] = user_info.gender if user_info.gender != None else ""
    _params['scholarity'] = user_info.scholarity if user_info.scholarity != None else ""
    _params['birth'] = user_info.birth.strftime("%Y-%m-%d") if user_info.birth != None else ""
    _params['has_picture'] = True if user_info.get_image_url() != -1 else False
    _params['has_address'] = True if user_info.address is not None else False
    _params['address_from'] = False
    if _params['has_address']:
        if user_info.address.address_from_coord is not None:
            lat = str(user_info.address.address_from_coord.lat)
            lng = str(user_info.address.address_from_coord.lon)
            _params['address_from_coord'] = lat + "," + lng
        _params['address_from'] = user_info.address.address_from
    if not _params['has_picture']:
        _params['disclaim'] = True
    else:
        _params['user_picture_url'] = user_info.get_image_url()
    _params['link_referral'] = user_info.link_referral
    _params['date'] = date.today().strftime("%Y-%m-%d")

    return _params, user_info

#EMAIL NOTIFICATION TO STAKEHOLDERS
def notifyOrganization(self, report):
    if self.app.config.get('send_org_notifications'):
        emails = ''
        group = models.GroupCategory.get_by_name(report.group_category)
        logging.info('group: %s' % group)
        if group:
            agency = models.Agency.get_by_group_id(group.key.id())
            emails = "%s" % agency.admin_email
            if agency:
                secretary = models.Secretary.get_by_id(long(agency.secretary_id))
                if secretary.admin_email not in emails:
                    emails += ", %s" % (secretary.admin_email)
                operators = models.Operator.query(models.Operator.agency_id == agency.key.id())
                for operator in operators:
                    if operator.email not in emails:
                        emails += ", %s" % operator.email

        logging.info('sending notification emails to: %s' % emails)

        if report.is_manual:
            contact = report.contact_info
            assignee = "%s (%s)" % (report.get_user_name(), report.get_user_email())
        else:
            contact = "%s %s; %s; %s; %s" % (report.get_user_name(), report.get_user_lastname(), report.get_user_address(), report.get_user_phone(), report.get_user_email())
            assignee = report.get_last_log()
        
        template_val = {
            "_url": self.uri_for("landing", _full=True),
            "cdb_id": report.cdb_id,
            "contact_info": contact,
            "category": report.sub_category,
            "description": report.description,
            "address": report.address_from,
            "address_detail": report.address_detail,
            "when": report.get_formatted_date(),
            "stakeholder": report.get_stakeholder(),
            "last_log": assignee,
            "brand_logo": self.brand['brand_logo'],
            "brand_color": self.brand['brand_color'],
            "brand_secondary_color": self.brand['brand_secondary_color'],
            "support_url": self.uri_for("contact", _full=True),
            "twitter_url": self.app.config.get('twitter_url'),
            "facebook_url": self.app.config.get('facebook_url'),
            "faq_url": self.uri_for("faq", _full=True)
        }
        body_path = "emails/notify_organization.txt"
        body = self.jinja2.render_template(body_path, **template_val)

        email_url = self.uri_for('taskqueue-send-email')
        taskqueue.add(url=email_url, params={
            'to': emails,
            'subject': messages.notification_org,
            'body': body,
        })
    else:
        logging.info('sending notification is disabled by configuration')

#REPORTS RELATED
def cartoInsert(self, report_id, manual, notify_organization):
    #PUSH TO CARTODB
    from google.appengine.api import urlfetch
    import urllib
    api_key = self.app.config.get('cartodb_apikey')
    cartodb_domain = self.app.config.get('cartodb_user')
    cartodb_table = self.app.config.get('cartodb_reports_table')
    report_info = models.Report.get_by_id(long(report_id))
    private = models.SubCategory.query(models.SubCategory.name == report_info.sub_category).get()
    if private is not None:
        private = private.private
    else:
        private = False
    if report_info.cdb_id == -1:
        #INSERT
        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=INSERT INTO %s (created, pvt, the_geom, _when, title, description, status, address_from, folio, image_url, group_category, sub_category, follows, rating, via, man, uuid) VALUES ('%s', %s, ST_GeomFromText('POINT(%s %s)', 4326),'%s','%s','%s','%s','%s','%s','%s','%s','%s',%s,%s,'%s', %s, '%s')&api_key=%s" % (cartodb_domain, cartodb_table, report_info.created.strftime("%Y-%m-%d %H:%M:%S"), private, report_info.address_from_coord.lon, report_info.address_from_coord.lat, report_info.when.strftime("%Y-%m-%d"),report_info.title,report_info.description,report_info.status,report_info.address_from,report_info.folio,report_info.image_url,report_info.group_category,report_info.sub_category,report_info.follows,report_info.rating,report_info.via,manual,report_info.key.id(),api_key)).encode('utf8')
        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
        try:
            t = urlfetch.fetch(url)
            logging.info("insert request to cartodb responded: %s" % t.content)
            #SELECT CARTODB_ID & ASSIGN
            cl = CartoDBAPIKey(api_key, cartodb_domain)
            response = cl.sql("select cartodb_id from %s where uuid = '%s'" % (cartodb_table, report_info.key.id()))
            report_info.cdb_id = response['rows'][0]['cartodb_id']
            report_info.put()
            if notify_organization:
                notifyOrganization(self, report_info)
            if manual:
                message = _(messages.report_success)
                self.add_message(message, 'success')
                return self.redirect_to("materialize-organization-report-success", ticket = report_info.cdb_id, report_key = report_info.key.id())
        except Exception as e:
            logging.info('error in cartodb INSERT request: %s' % e)
            if manual:
                message = _(messages.report_success)
                self.add_message(message, 'success')
                return self.redirect_to("materialize-organization-report-success", ticket = report_info.cdb_id, report_key = report_info.key.id())
            pass

def cartoUpdate(self, report_id, notify_organization):
    #PUSH TO CARTODB
    from google.appengine.api import urlfetch
    import urllib
    api_key = self.app.config.get('cartodb_apikey')
    cartodb_domain = self.app.config.get('cartodb_user')
    cartodb_table = self.app.config.get('cartodb_reports_table')
    report_info = models.Report.get_by_id(long(report_id))
    private = models.SubCategory.query(models.SubCategory.name == report_info.sub_category).get()
    if private is not None:
        private = private.private
    else:
        private = False
    if report_info.cdb_id != -1:
        #UPDATE
        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET terminated = '%s', pvt = %s ,the_geom = ST_GeomFromText('POINT(%s %s)', 4326), _when = '%s', title = '%s', description = '%s', status = '%s', address_from = '%s', folio = '%s', image_url = '%s', group_category = '%s', sub_category = '%s', follows = %s, rating = %s, via = '%s', uuid = '%s' WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table,report_info.terminated.strftime("%Y-%m-%d %H:%M:%S"), private, report_info.address_from_coord.lon, report_info.address_from_coord.lat, report_info.when.strftime("%Y-%m-%d"),report_info.title,report_info.description,report_info.status,report_info.address_from,report_info.folio,report_info.image_url,report_info.group_category,report_info.sub_category,report_info.follows,report_info.rating,report_info.via,report_info.key.id(),report_info.cdb_id,api_key)).encode('utf8')
        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
        try:
            t = urlfetch.fetch(url)
            logging.info("update request to cartodb responded: %s" % t.content)
        except Exception as e:
            logging.info('error in cartodb UPDATE request: %s' % e)
            pass
    if notify_organization:
        notifyOrganization(self, report_info)

def archiveReport(self, user_info, report_id, handler):
    from google.appengine.api import urlfetch
    import urllib
    api_key = self.app.config.get('cartodb_apikey')
    cartodb_domain = self.app.config.get('cartodb_user')
    cartodb_table = self.app.config.get('cartodb_reports_table')
    report_info = models.Report.get_by_id(long(report_id))

    #ASSIGN AS IS
    report_info.status = 'archived'
    report_info.terminated = datetime.now()
    
    #LOG CHANGES
    log_info = models.LogChange()
    log_info.user_email = user_info.email.lower()
    log_info.report_id = int(report_id)
    log_info.kind = 'status'
    log_info.title = "Ha archivado este reporte."
    log_info.contents = self.request.get('contents')
    log_info.put()

    #PUSH TO CARTODB
    if report_info.cdb_id != -1:
        #UPDATE
        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET status = '%s', terminated = '%s' WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, report_info.status, report_info.terminated.strftime("%Y-%m-%d %H:%M:%S"), report_info.cdb_id, api_key)).encode('utf8')
        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
        try:
            t = urlfetch.fetch(url)
            logging.info("t: %s" % t.content)
        except Exception as e:
            logging.info('error in cartodb status UPDATE request: %s' % e)
            pass
    report_info.put()

    self.add_message(messages.saving_success, 'success')
    return self.redirect_to(handler, report_id=report_id)

def editReport(self, user_info, report_id, handler):
    from google.appengine.api import urlfetch
    import urllib
    api_key = self.app.config.get('cartodb_apikey')
    cartodb_domain = self.app.config.get('cartodb_user')
    cartodb_table = self.app.config.get('cartodb_reports_table')
    report_info = models.Report.get_by_id(long(report_id))
    notify_organization = False

    #UPDATED VALUES
    address_detail = self.request.get('address_detail')
    address_from = self.request.get('address_from')
    address_from_coord = self.request.get('address_from_coord')
    catGroup = self.request.get('catGroup')
    subCat = self.request.get('subCat')
    description = self.request.get('description')
    when = self.request.get('when')
    folio = self.request.get('folio')
    status = self.request.get('status')
    note = self.request.get('note')
    comment = self.request.get('comment')
    title = self.request.get('title')
    kind = self.request.get('kind')
    changes = ""
    private = models.SubCategory.query(models.SubCategory.name == subCat).get()
    if private is not None:
        private = private.private
    else:
        report_info.group_category = '---'
        report_info.sub_category = '---'
        report_info.put()
        self.add_message(messages.reselect, 'warning')
        return self.redirect_to(handler, report_id=report_id)

    #ASSIGN AS IS
    status = status if status != 'undefined' else report_info.status
    
    if report_info.address_from != address_from or report_info.address_detail != address_detail:
        report_info.address_detail = address_detail
        report_info.address_from = address_from
        report_info.address_from_coord = ndb.GeoPt(address_from_coord)
        changes += "el domicilio, "
    if report_info.address_from_coord != ndb.GeoPt(address_from_coord):
        report_info.address_from_coord = ndb.GeoPt(address_from_coord)
    #     changes += "el mapa, "
    if report_info.when.strftime("%Y-%m-%d") != when:
        report_info.when = date(int(when[:4]), int(when[5:7]), int(when[8:]))
        changes += "la fecha, "
    if report_info.title != title:
        report_info.title = title
        changes += "el titulo, "
    if report_info.description != description:
        report_info.description = description
        changes += "la descripcion, "
    
    if status != report_info.status:
        #increment credibility
        if ((status != 'spam' and report_info.status == 'spam') or (status == 'solved' and report_info.status != 'solved')) and report_info.user_id != -1:
            _user = self.user_model.get_by_id(long(report_info.user_id))
            if _user:
                _user.credibility += 1
                _user.put()
        #decrement credibility
        elif (status == 'spam' and report_info.status != 'spam') and report_info.user_id != -1:
            _user = self.user_model.get_by_id(long(report_info.user_id))
            if _user:
                _user.credibility -= 1
                _user.put()
        
        #set terminated
        if (status == 'solved' and report_info.status != 'solved') or (status == 'failed' and report_info.status != 'failed'):
            report_info.terminated = datetime.now()
        else:
            #J-DAY
            report_info.terminated = datetime(1997, 8, 29)
                       
        report_info.status = status
        changes += "el estado, "
        if report_info.status == 'assigned':
            notify_organization = True
                        
    if report_info.folio != folio:
        report_info.folio = folio
        changes += "el folio, "
    if report_info.group_category != catGroup:
        report_info.group_category = catGroup
        changes += "el grupo de categoria, "
    if report_info.sub_category != subCat:
        report_info.sub_category = subCat
        changes += "la subcategoria, "

    if report_info.terminated is None:
        report_info.terminated = datetime(1997, 8, 29)

    """
        --------------------------------------------------
        CONDITIONAL OVERRIDES FOR AUTOMATIC STATUS CHANGE
        --------------------------------------------------

        CASES FOR ADMIN
        1.- If report is OPEN and admin does a COMMENT action: status -> HALTED
        2.- If report is ARCHIVED and admin does a COMMENT action: status -> HALTED
        3.- If report is SPAM and admin does a COMMENT action: status -> HALTED
        4.- If report is REJECTED and admin does a COMMENT action: status -> HALTED

        CASES FOR OPERATOR
        1.- If report is ASSIGNED and operator does a COMMENT action: status -> WORKING

        OTHER CASES
        *.- If report is HALTED for more than 30 days a cronjob will set: status -> FORGOT
        *.- If report is HALTED and citizen does a COMMENT action: status -> OPEN

        NOTE THAT:
            -ADMIN CAN ONLY SET STATUS TO ASSIGNED (dropdown), ARCHIVED (button), OR SPAM (button).
            -OPERATOR CAN ONLY SET STATUS TO REJECTED (dropdown), SOLVED (button), OR FAILED (button).
            -THERE ARE FOUR STATUSES THAT ARE AUTOMATICALLY SET: OPEN, HALTED, WORKING AND FORGOT.

    """
    if kind == 'comment' and report_info.status in ['open','archived','rejected', 'spam']:
        report_info.status = 'halted'
    if kind == 'comment' and report_info.status == 'assigned':
        report_info.status = 'working'

    #LOG CHANGES
    log_info = models.LogChange()
    log_info.user_email = user_info.email.lower()
    log_info.report_id = int(report_id)
    log_info.kind = kind
    if kind == 'status' and report_info.status == 'archived':
        log_info.title = "Ha archivado este reporte."
        log_info.contents = self.request.get('contents')
    elif kind == 'status' and report_info.status == 'spam':
        log_info.title = "Ha marcado como spam este reporte."
        log_info.contents = self.request.get('contents')
    elif kind == 'status' and report_info.status == 'solved':
        log_info.title = "Ha marcado este reporte como resuelto."
        log_info.contents = self.request.get('contents')
    elif kind == 'status' and report_info.status == 'failed':
        log_info.title = "Ha marcado este reporte como fallido."
        log_info.contents = self.request.get('contents')
    elif kind == 'status' and report_info.status == 'rejected':
        log_info.title = "Ha rechazado este reporte."
        log_info.contents = self.request.get('contents')
    elif kind == 'comment':
        log_info.title = "Ha enviado un comentario al ciudadano."
        log_info.contents = self.request.get('contents')
    elif kind == 'note':
        log_info.title = "Ha agregado una nota interna en este reporte."
        log_info.contents = self.request.get('contents')
    elif changes != "":
        log_info.title = "Ha hecho algunos cambios en este reporte."
        log_info.contents = "Fue modificado %s de este reporte." % changes[0:-2]
    if log_info.title and log_info.contents:
        log_info.put()

    report_info.put()

    #PUSH TO CARTODB
    if report_info.cdb_id == -1:
        #INSERT
        cartoInsert(self, report_info.key.id(), False, notify_organization)
    else:
        #UPDATE
        cartoUpdate(self, report_info.key.id(), notify_organization)


    #NOTIFY APPROPRIATELY
    """
        --------------------------------------------------
        EMAIL NOTIFICATIONS COME WITH DIFFERENT REASONS
        --------------------------------------------------
        
        @CRONJOB
        1.- AUTOMATIC EMAIL IF REPORT STATUS IS OPEN AND MORE THAN 3 DAYS HAVE PASSED. (template: auto_72.txt)
        2.- AUTOMATIC EMAIL IF REPORT STATUS IS AUTOMATICALLY CHANGED TO FORGOT. (template: change_notification.txt)
        
        @ADMIN
        3.- ADMIN SENDS A MODIFICATION OF KIND COMMENT. (template: change_notification.txt)
        4.- ADMIN SENDS A MODIFICATION OF KIND STATUS WITH STATUS ASSIGNED. (template: change_notification.txt)
        5.- ADMIN SENDS A MODIFICATION OF REPORT PROPERTIES. (template: change_notification.txt)
        
        @OPERATOR
        6.- OPERATOR A MODIFICATION OF KIND STATUS WITH STATUS SOLVED. (template: change_notification.txt)
        7.- OPERATOR A MODIFICATION OF KIND STATUS WITH STATUS FAILED. (template: change_notification.txt)
        8.- OPERATOR SENDS A MODIFICATION OF KIND COMMENT. (template: change_notification.txt)

    """
    if not report_info.is_manual and kind != 'note' and report_info.status != 'archived' and report_info.status != 'spam' and report_info.status != 'rejected':
        reason = ""
        if kind == 'comment':
            reason = unicode('Tu reporte está siendo resuelto pero hacen falta algunas aclaraciones para poder seguir avanzando en su solución. Por favor visita tu sección de reportes y envíanos tus comentarios.','utf-8')
        elif kind == 'status' and report_info.status == 'solved':
            if report_info.get_agency() != '':
                _r = u'Tu reporte ha sido resuelto por la %s, parte de la %s. Visita tu sección de reportes para ver su solución y calificarla.'
                reason = _r % (report_info.get_agency(), report_info.get_secretary())
            else:
                reason = unicode('Tu reporte ha sido resuelto. Visita tu sección de reportes para ver su solución y calificarla.', 'utf-8')
        elif kind == 'status' and report_info.status == 'failed':
            if report_info.get_agency() != '':
                _r = u'Tu reporte ha sido cerrado sin resolver por la %s, parte de la %s. Visita tu sección de reportes para ver los detalles.'
                reason = _r % (report_info.get_agency(), report_info.get_secretary())
            else:
                reason = unicode('Tu reporte ha sido cerrado sin resolver. Visita tu sección de reportes para ver los detalles.', 'utf-8')
        else:
            reason = unicode('Tu reporte ha sido modificado en algunos campos y estamos avanzando en solucionarlo. Por favor visita tu sección de reportes y si tienes algún comentario por favor háznoslo saber.','utf-8')

        template_val = {
            "name": report_info.get_user_name(),
            "_url": self.uri_for("materialize-reports", _full=True),
            "cdb_id": report_info.cdb_id,
            "reason": reason,
            "brand_logo": self.brand['brand_logo'],
            "brand_color": self.brand['brand_color'],
            "brand_secondary_color": self.brand['brand_secondary_color'],
            "support_url": self.uri_for("contact", _full=True),
            "twitter_url": self.app.config.get('twitter_url'),
            "facebook_url": self.app.config.get('facebook_url'),
            "faq_url": self.uri_for("faq", _full=True)
        }
        body_path = "emails/change_notification.txt"
        body = self.jinja2.render_template(body_path, **template_val)

        email_url = self.uri_for('taskqueue-send-email')
        taskqueue.add(url=email_url, params={
            'to': str(report_info.get_user_email()),
            'subject': messages.notification,
            'body': body,
        })

    self.add_message(messages.saving_success, 'success')
    return self.redirect_to(handler, report_id=report_id)

def editReportParams(self, report_info):
    params = {
        'report': report_info
    }
    logs = models.LogChange.query(models.LogChange.report_id == report_info.key.id())
    logs = logs.order(-models.LogChange.created)
    params['logs'] = []
    for log in logs:
        user = log.get_user()            
        if user:
            image = user.get_image_url()
            initial_letter = user.name[1]
            name = user.name
        else:
            image = -1
            initial_letter = log.user_email[1]
            name = ''
        params['logs'].append((log.key.id(), log.get_formatted_date(), image, initial_letter, name, log.user_email, log.title, log.contents))
    
    params['has_logs'] = True if len(params['logs']) > 0 else False
    params['atts'] = models.Attachment.query(models.Attachment.report_id == report_info.key.id())
    params['atts'] = params['atts'].order(-models.Attachment.created)
    params['has_atts'] = True if params['atts'].count() > 0 else False
    params['zoom'] = self.app.config.get('map_zoom')
    params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
    params['lat'] = self.app.config.get('map_center_lat')
    params['lng'] = self.app.config.get('map_center_lng')

    params['cartodb_user'] = self.app.config.get('cartodb_user')
    params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
    params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
    params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
    params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')

    return params

def get_or_404(self, report_id):
    if self.user_is_secretary or self.user_is_agent or self.user_is_operator or self.user_is_callcenter:
        try:
            report = models.Report.get_by_id(long(report_id))
            if report:
                return report
            else:
                self.abort(404)
        except ValueError:
            pass
    self.abort(403)

def get_status(_stat):
    if _stat == 'open':
        return 'Abierto'        
    if _stat == 'halted':
        return 'En espera'
    if _stat == 'assigned':
        return 'Asignado'
    if _stat == 'spam':
        return 'Spam'
    if _stat == 'archived':
        return 'Archivado'
    if _stat == 'forgot':
        return 'Olvidado'
    if _stat == 'rejected':
        return 'Rechazado'
    if _stat == 'working':
        return 'En proceso'
    if _stat == 'answered':
        return 'Respondido'
    if _stat == 'solved':
        return 'Resuelto'
    if _stat == 'failed':
        return 'Fallo'
    if _stat == 'pending':
        return 'Pendientes'

# ------------------------------------------------------------------------------------------- #
"""                                     ACCOUNT HANDLERS                                    """
# ------------------------------------------------------------------------------------------- #

#LOGIN
class LoginRequiredHandler(BaseHandler):
    def get(self):
        continue_url = self.request.get_all('continue')
        self.redirect(users.create_login_url(dest_url=continue_url))

class MaterializeLoginRequestHandler(BaseHandler):
    """
    Handler for authentication
    """

    def get(self):
        """ Returns a simple HTML form for login """

        if self.user:
            user_info = self.user_model.get_by_id(long(self.user_id))        
            if not user_info.address:
                return self.redirect_to('materialize-settings-profile')
            self.redirect_to('materialize-welcome')

        params = {
            'captchahtml': captchaBase(self),
        }
        continue_url = self.request.get('continue').encode('ascii', 'ignore')
        params['continue_url'] = continue_url
        return self.render_template('materialize/landing/login.html', **params)

    def post(self):
        """
        email: Get the email from POST dict
        password: Get the password from POST dict
        """

        if not self.form.validate():
            _message = _(messages.post_error)
            self.add_message(_message, 'danger')
            return self.get()
        email = self.form.email.data.lower()
        continue_url = self.request.get('continue').encode('ascii', 'ignore')

        try:
            if utils.is_email_valid(email):
                user = self.user_model.get_by_email(email)
                if user:
                    auth_id = user.auth_ids[0]
                else:
                    raise InvalidAuthIdError
            else:
                auth_id = "own:%s" % email
                user = self.user_model.get_by_auth_id(auth_id)
            
            password = self.form.password.data.strip()
            remember_me = True if str(self.request.POST.get('remember_me')) == 'on' else False

            # Password to SHA512
            password = utils.hashing(password, self.app.config.get('salt'))

            # Try to login user with password
            # Raises InvalidAuthIdError if user is not found
            # Raises InvalidPasswordError if provided password
            # doesn't match with specified user
            self.auth.get_user_by_password(
                auth_id, password, remember=remember_me)

            # if user account is not activated, logout and redirect to home
            if (user.activated == False):
                # logout
                self.auth.unset_session()

                # redirect to home with error message
                resend_email_uri = self.uri_for('resend-account-activation', user_id=user.get_id(),
                                                token=self.user_model.create_resend_token(user.get_id()))
                message = _(messages.inactive_account) + ' ' + resend_email_uri
                self.add_message(message, 'danger')
                return self.redirect_to('login')
            else:
                try:
                    user.last_login = utils.get_date_time()
                    user.put()
                except (apiproxy_errors.OverQuotaError, BadValueError):
                    logging.error("Error saving Last Login in datastore")
            

            if self.app.config['log_visit']:
                try:
                    logVisit = models.LogVisit(
                        user=user.key,
                        uastring=self.request.user_agent,
                        ip=self.request.remote_addr,
                        timestamp=utils.get_date_time()
                    )
                    logVisit.put()
                except (apiproxy_errors.OverQuotaError, BadValueError):
                    logging.error("Error saving Visit Log in datastore")
            if continue_url:
                self.redirect(continue_url)
            else:
                message = _('Bienvenido nuevamente, %s! ' % user.name)
                self.add_message(message, 'success')
                if not user.address:
                    return self.redirect_to('materialize-settings-profile')
                self.redirect_to('materialize-welcome')
        except (InvalidAuthIdError, InvalidPasswordError), e:
            # Returns error message to self.response.write in
            # the BaseHandler.dispatcher
            message = _(messages.user_pass_mismatch)
            self.add_message(message, 'danger')
            self.redirect_to('login', continue_url=continue_url) if continue_url else self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.LoginForm(self)

class MaterializeLogoutRequestHandler(BaseHandler):
    """
    Destroy user session and redirect to login
    """

    def get(self):
        if self.user:
            message = _(messages.logout)
            self.add_message(message, 'info')

        self.auth.unset_session()
        # User is logged out, let's try redirecting to login page
        try:
            self.redirect_to('landing')
        except (AttributeError, KeyError), e:
            logging.error("Error logging out: %s" % e)
            message = _(messages.logout_error)
            self.add_message(message, 'danger')
            return self.redirect_to('landing')

#REGISTER
class MaterializeRegisterReferralHandler(BaseHandler):
    """
    Handler to process the link of referrals for a given user_id
    """

    def get(self, user_id):
        if self.user:
            self.redirect_to('landing')
        user = self.user_model.get_by_id(long(user_id))

        if user is not None:
            params = {
                'captchahtml': captchaBase(self),
                '_username': user.name,
                '_email': user.email,
                'is_referral' : True
            }
            return self.render_template('materialize/landing/register.html', **params)
        else:
            return self.redirect_to('landing')

    def post(self, user_id):
        """ Get fields from POST dict """

        # check captcha
        response = self.request.POST.get('g-recaptcha-response')
        remote_ip = self.request.remote_addr

        cResponse = captcha.submit(
            response,
            self.app.config.get('captcha_private_key'),
            remote_ip)

        if cResponse.is_valid:
            # captcha was valid... carry on..nothing to see here
            pass
        else:
            _message = _(messages.captcha_error)
            self.add_message(_message, 'danger')
            return self.get(user_id)

        if not self.form.validate():
            _message = _(messages.saving_error)
            logging.info("Form did not passed.")
            self.add_message(_message, 'danger')
            return self.get(user_id)
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        email = self.form.email.data.lower()
        username = email
        password = self.form.password.data.strip()


        aUser = self.user_model.get_by_email(email)
        if aUser is not None:
            message = _("Sorry, email %s is already in use." % email)
            self.add_message(message, 'danger')
            return self.redirect_to('landing')


        # Password to SHA512
        password = utils.hashing(password, self.app.config.get('salt'))

        # Passing password_raw=password so password will be hashed
        # Returns a tuple, where first value is BOOL.
        # If True ok, If False no new user is created
        unique_properties = ['username', 'email']
        auth_id = "own:%s" % username
        referred_user = self.auth.store.user_model.create_user(
            auth_id, unique_properties, password_raw=password,
            username=username, name=name, last_name=last_name, email=email,
            ip=self.request.remote_addr
        )

        if not referred_user[0]: #user is a tuple
            if "username" in str(referred_user[1]):
                message = _(messages.username_exists).format(username)
            elif "email" in str(referred_user[1]):
                message = _(messages.email_exists).format(email)
            else:
                message = _(messages.user_exists)
            self.add_message(message, 'danger')
            return self.redirect_to('register-referral',user_id=user_id, _full = True)
        else:
            # User registered successfully
            # But if the user registered using the form, the user has to check their email to activate the account ???
            try:
                if not referred_user[1].activated:
                    # send email
                    subject = _(messages.email_activation_subject)
                    confirmation_url = self.uri_for("account-activation-referral",
                                                    ref_user_id=referred_user[1].get_id(),
                                                    token=self.user_model.create_auth_token(referred_user[1].get_id()),
                                                    user_id =  user_id,
                                                    _full=True)
                    if name != '':
                        _username = str(name)
                    else:
                        _username = str(username)
                    # load email's template
                    template_val = {
                        "app_name": self.app.config.get('app_name'),
                        "username": _username,
                        "confirmation_url": confirmation_url,
                        "brand_logo": self.brand['brand_logo'],
                        "brand_color": self.brand['brand_color'],
                        "brand_secondary_color": self.brand['brand_secondary_color'],
                        "support_url": self.uri_for("contact", _full=True),
                        "twitter_url": self.app.config.get('twitter_url'),
                        "facebook_url": self.app.config.get('facebook_url'),
                        "faq_url": self.uri_for("faq", _full=True)
                    }
                    body_path = "emails/account_activation.txt"
                    body = self.jinja2.render_template(body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url=email_url, params={
                        'to': str(email),
                        'subject': subject,
                        'body': body,
                    })

                    
                    #unlock rewards status for the user who referred this referred_user
                    already_invited = False;
                    user = self.user_model.get_by_id(long(user_id))
                    for reward in user.rewards:
                        if reward.content == email:
                            already_invited = True;
                            break

                    if not already_invited:
                        reward = models.Rewards(amount = 0,earned = True, category = 'invite',
                            content = email,timestamp = utils.get_date_time(),status = 'invited')                 
                        user.rewards.append(reward)
                        user.put()

                    message = _(messages.register_success)
                    self.add_message(message, 'success')
                    return self.redirect_to('landing')
                
                message = _(messages.logged).format(username)
                self.add_message(message, 'success')
                return self.redirect_to('landing')
            except (AttributeError, KeyError), e:
                logging.error('Unexpected error creating the user %s: %s' % (username, e ))
                message = _(messages.user_creation_error).format(username)
                self.add_message(message, 'danger')
                return self.redirect_to('register-referral',user_id=user_id, _full = True)

    @webapp2.cached_property
    def form(self):
        f = forms.RegisterForm(self)
        return f

class MaterializeRegisterRequestHandler(BaseHandler):
    """
    Handler for Sign Up Users
    """

    def get(self):
        """ Returns a simple HTML form for create a new user """

        if self.user:
            self.redirect_to('landing')

        params = {
            'captchahtml': captchaBase(self),
        }
        return self.render_template('materialize/landing/register.html', **params)

    def post(self):
        """ Get fields from POST dict """

        # check captcha
        response = self.request.POST.get('g-recaptcha-response')
        remote_ip = self.request.remote_addr

        cResponse = captcha.submit(
            response,
            self.app.config.get('captcha_private_key'),
            remote_ip)

        if cResponse.is_valid:
            # captcha was valid... carry on..nothing to see here
            pass
        else:
            _message = _(messages.captcha_error)
            self.add_message(_message, 'danger')
            return self.redirect_to('register')

        if not self.form.validate():
            logging.info("Form did not passed.")
            _message = _(messages.saving_error)
            self.add_message(_message, 'danger')
            return self.get()
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        email = self.form.email.data.lower()
        username = email
        password = self.form.password.data.strip()


        aUser = self.user_model.get_by_email(email)
        if aUser is not None:
            message = _("Sorry, email %s is already in use." % email)
            self.add_message(message, 'danger')
            return self.redirect_to('landing')

        # Password to SHA512
        password = utils.hashing(password, self.app.config.get('salt'))

        # Passing password_raw=password so password will be hashed
        # Returns a tuple, where first value is BOOL.
        # If True ok, If False no new user is created
        unique_properties = ['username', 'email']
        auth_id = "own:%s" % username
        user = self.auth.store.user_model.create_user(
            auth_id, unique_properties, password_raw=password,
            username=username, name=name, last_name=last_name, email=email,
            ip=self.request.remote_addr
        )

        if not user[0]: #user is a tuple
            if "username" in str(user[1]):
                message = _(messages.username_exists).format(username)
            elif "email" in str(user[1]):
                message = _(messages.email_exists).format(email)
            else:
                message = _(messages.user_exists)
            self.add_message(message, 'danger')
            return self.redirect_to('register')
        else:
            # User registered successfully
            # But if the user registered using the form, the user has to check their email to activate the account ???
            try:
                if not user[1].activated:
                    # send email
                    #subject = _("%s Account Verification" % self.app.config.get('app_name'))
                    subject = _(messages.email_activation_subject)
                    confirmation_url = self.uri_for("account-activation",
                                                    user_id=user[1].get_id(),
                                                    token=self.user_model.create_auth_token(user[1].get_id()),
                                                    _full=True)

                    # load email's template
                    template_val = {
                        "app_name": self.app.config.get('app_name'),
                        "username": name,
                        "confirmation_url": confirmation_url,
                        "brand_logo": self.brand['brand_logo'],
                        "brand_color": self.brand['brand_color'],
                        "brand_secondary_color": self.brand['brand_secondary_color'],
                        "support_url": self.uri_for("contact", _full=True),
                        "twitter_url": self.app.config.get('twitter_url'),
                        "facebook_url": self.app.config.get('facebook_url'),
                        "faq_url": self.uri_for("faq", _full=True)
                    }
                    body_path = "emails/account_activation.txt"
                    body = self.jinja2.render_template(body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url=email_url, params={
                        'to': str(email),
                        'subject': subject,
                        'body': body,
                    })

                    message = _(messages.register_success)
                    self.add_message(message, 'success')
                    return self.redirect_to('landing')

                # If the user didn't register using registration form ???
                db_user = self.auth.get_user_by_password(user[1].auth_ids[0], password)

                message = _(messages.logged).format(username)
                self.add_message(message, 'success')
                return self.redirect_to('landing')
            except (AttributeError, KeyError), e:
                logging.error('Unexpected error creating the user %s: %s' % (username, e ))
                message = _(messages.user_creation_error).format(username)
                self.add_message(message, 'danger')
                return self.redirect_to('landing')

    @webapp2.cached_property
    def form(self):
        f = forms.RegisterForm(self)
        return f

#EMAILS
class SendEmailHandler(BaseHandler):
    """
    Core Handler for sending Emails
    Use with TaskQueue
    """

    @taskqueue_method
    def post(self):

        from google.appengine.api import mail, app_identity
        
        to = self.request.get("to")
        subject = self.request.get("subject")
        body = self.request.get("body")
        sender = self.request.get("sender")

        if sender != '' or not utils.is_email_valid(sender):
            if utils.is_email_valid(self.app.config.get('contact_sender')):
                sender = self.app.config.get('contact_sender')
            else:
                app_id = app_identity.get_application_id()
                sender = "%s Mail <no-reply@%s.appspotmail.com>" % (self.app.config.get('app_name'),app_id)                

        if self.app.config['log_email']:
            try:
                logEmail = models.LogEmail(
                    sender=sender,
                    to=to,
                    subject=subject,
                    body=body,
                    when=utils.get_date_time("datetimeProperty")
                )
                logEmail.put()
            except (apiproxy_errors.OverQuotaError, BadValueError):
                logging.error("Error saving Email Log in datastore")
                pass

        if self.app.config.get('sendgrid_priority'):
            #using sendgrid
            from lib import sendgrid
            from lib.sendgrid import SendGridError, SendGridClientError, SendGridServerError 
            try:
                sg = sendgrid.SendGridClient(self.app.config.get('sendgrid_login'), self.app.config.get('sendgrid_passkey'))
                logging.info("sending with sendgrid client: %s" % sg)
                message = sendgrid.Mail()
                message.add_to(to.split(','))
                message.set_subject(subject)
                message.set_html(body)
                message.set_text(body)
                message.set_from(sender)
                status, msg = sg.send(message)
            except Exception, e:
                logging.error("Error sending email with sendgrid: %s" % e)
                try:            
                    message = mail.EmailMessage()
                    message.sender = sender
                    message.to = to
                    message.subject = subject
                    message.html = body
                    message.send()
                    logging.info("...attempting google, sending email to: %s ..." % to)
                except Exception, e:
                    logging.error("Error sending email: %s" % e)
                    pass
        else:
            #using appengine email 
            try:            
                message = mail.EmailMessage()
                message.sender = sender
                message.to = to
                message.subject = subject
                message.html = body
                message.send()
                logging.info("... sending email to: %s ..." % to)
            except Exception, e:
                logging.error("Error sending email: %s" % e)
                pass  

class LogBounceHandler(BounceNotificationHandler):
    def receive(self, bounce_message):
        logging.info('Received bounce post ... [%s]', self.request)
        logging.info('Bounce original: %s', bounce_message.original)
        logging.info('Bounce notification: %s', bounce_message.notification)

#ACTIVATION
class MaterializeAccountActivationHandler(BaseHandler):
    """
    Handler for account activation
    """

    def get(self, user_id, token):
        try:
            if not self.user_model.validate_auth_token(user_id, token):
                message = _(messages.used_activation_link)
                self.add_message(message, 'danger')
                return self.redirect_to('login')

            user = self.user_model.get_by_id(long(user_id))
            # activate the user's account
            user.activated = True
            user.last_login = utils.get_date_time()
            
            # create unique url for sharing & referrals purposes
            long_url = self.uri_for("register-referral",user_id=user.get_id(),_full=True)
            logging.info("Long URL: %s" % long_url)
            short_url = long_url
            
            #The goo.gl way:
            # post_url = 'https://www.googleapis.com/urlshortener/v1/url'            
            # payload = {'longUrl': long_url}
            # headers = {'content-type': 'application/json'}
            # r = requests.post(post_url, data=json.dumps(payload), headers=headers)
            # j = json.loads(r.text)
            # logging.info("Google response: %s" % j)
            # short_url = j['id']

            #The bit.ly way:
            try:
                api = bitly.Api(login=self.app.config.get('bitly_login'), apikey=self.app.config.get('bitly_apikey'))
                short_url=api.shorten(long_url)
                logging.info("Bitly response: %s" % short_url)
            except:
                pass

            user.link_referral = short_url
            reward = models.Rewards(amount = 100,earned = True, category = 'configuration',
                content = 'Activation',timestamp = utils.get_date_time(),status = 'completed')                 
            user.rewards.append(reward)

            #Role init
            user.role = 'Admin'

            #Datastore allocation
            user.put()

            # Login User
            self.auth.get_user_by_token(int(user_id), token)

            # Delete token
            self.user_model.delete_auth_token(user_id, token)

            # Slack Incoming WebHooks
            try:
                from google.appengine.api import urlfetch            
                urlfetch.fetch(self.app.config.get('slack_webhook_url'), payload='{"channel": "#general", "username": "webhookbot", "text": "just got a new user at '+self.app.config.get('app_id')+'! Go surprise him at '+user.email+'", "icon_emoji": ":bowtie:"}', method='POST')
            except Exception as e:
                pass

            message = _(messages.activation_success).format(
                user.email)
            self.add_message(message, 'success')
            self.redirect_to('materialize-settings-profile')

        except (AttributeError, KeyError, InvalidAuthIdError, NameError), e:
            logging.error("Error activating an account: %s" % e)
            message = _(messages.post_error)
            self.add_message(message, 'danger')
            return self.redirect_to('landing')

class MaterializeAccountActivationReferralHandler(BaseHandler):
    """
    Handler for account activation
    """

    def get(self, ref_user_id, token, user_id):
        try:
            if not self.user_model.validate_auth_token(ref_user_id, token):
                message = _(messages.used_activation_link)
                self.add_message(message, 'danger')
                return self.redirect_to('login')


            user = self.user_model.get_by_id(long(user_id))
            referred_user = self.user_model.get_by_id(long(ref_user_id))
            
            # activate the user's account            
            referred_user.activated = True
            referred_user.last_login = utils.get_date_time()
            
            # create unique url for sharing & referrals purposes
            long_url = self.uri_for("register-referral",user_id=referred_user.get_id(),_full=True)
            logging.info("Long URL: %s" % long_url)
            short_url = long_url
            
            #The goo.gl way:
            # post_url = 'https://www.googleapis.com/urlshortener/v1/url'            
            # payload = {'longUrl': long_url}
            # headers = {'content-type': 'application/json'}
            # r = requests.post(post_url, data=json.dumps(payload), headers=headers)
            # j = json.loads(r.text)
            # logging.info("Google response: %s" % j)
            # short_url = j['id']

            #The bit.ly way:
            try:
                api = bitly.Api(login=self.app.config.get('bitly_login'), apikey=self.app.config.get('bitly_apikey'))
                short_url=api.shorten(long_url)
                logging.info("Bitly response: %s" % short_url)
            except:
                pass


            referred_user.link_referral = short_url
            reward = models.Rewards(amount = 100,earned = True, category = 'configuration',
                content = 'Activation',timestamp = utils.get_date_time(),status = 'completed')                 
            referred_user.rewards.append(reward)
            reward = models.Rewards(amount = 20,earned = True, category = 'invite',
                content = 'Invitee by: ' + user.email,timestamp = utils.get_date_time(),status = 'completed')                 
            referred_user.rewards.append(reward)


            #Role init
            referred_user.role = 'Admin'

            #Datastore allocation
            referred_user.put()
            
            # assign the referral reward
            for reward in user.rewards:
                if reward.content == referred_user.email:
                    reward.amount = 50;
                    reward.status = 'joined';
                    user.put()
                    break

            # Login User
            self.auth.get_user_by_token(int(ref_user_id), token)

            # Delete token
            self.user_model.delete_auth_token(ref_user_id, token)

            # Slack Incoming WebHooks
            try:
                from google.appengine.api import urlfetch
                urlfetch.fetch(self.app.config.get('slack_webhook_url'), payload='{"channel": "#general", "username": "webhookbot", "text": "Just got a new referred user at '+self.app.config.get('app_id')+'! Go surprise him at '+referred_user.email+' and remember to thank '+ user.email +'", "icon_emoji": ":bowtie:"}', method='POST')
            except Exception as e:
                pass

            message = _(messages.activation_success).format(
                referred_user.email)
            self.add_message(message, 'success')
            self.redirect_to('materialize-settings-profile')

        except (AttributeError, KeyError, InvalidAuthIdError, NameError), e:
            logging.error("Error activating an account: %s" % e)
            message = _(messages.post_error)
            self.add_message(message, 'danger')
            return self.redirect_to('login')

class ResendActivationEmailHandler(BaseHandler):
    """
    Handler to resend activation email
    """

    def get(self, user_id, token):
        try:
            if not self.user_model.validate_resend_token(user_id, token):
                message = _(messages.used_activation_link)
                self.add_message(message, 'danger')
                return self.redirect_to('login')

            user = self.user_model.get_by_id(long(user_id))
            email = user.email

            if (user.activated == False):
                # send email
                subject = _(messages.email_activation_subject)
                confirmation_url = self.uri_for("account-activation",
                                                user_id=user.get_id(),
                                                token=self.user_model.create_auth_token(user.get_id()),
                                                _full=True)
                # load email's template
                template_val = {
                    "app_name": self.app.config.get('app_name'),
                    "username": user.name,
                    "confirmation_url": confirmation_url,
                    "brand_logo": self.brand['brand_logo'],
                    "brand_color": self.brand['brand_color'],
                    "brand_secondary_color": self.brand['brand_secondary_color'],
                    "support_url": self.uri_for("contact", _full=True),
                    "twitter_url": self.app.config.get('twitter_url'),
                    "facebook_url": self.app.config.get('facebook_url'),
                    "faq_url": self.uri_for("faq", _full=True)
                }
                body_path = "emails/account_activation.txt"
                body = self.jinja2.render_template(body_path, **template_val)

                email_url = self.uri_for('taskqueue-send-email')
                taskqueue.add(url=email_url, params={
                    'to': str(email),
                    'subject': subject,
                    'body': body,
                })

                self.user_model.delete_resend_token(user_id, token)

                message = _(messages.resend_success).format(email)
                self.add_message(message, 'success')
                return self.redirect_to('login')
            else:
                message = _(messages.activation_success)
                self.add_message(message, 'warning')
                return self.redirect_to('landing')

        except (KeyError, AttributeError), e:
            logging.error("Error resending activation email: %s" % e)
            message = _(messages.post_error)
            self.add_message(message, 'danger')
            return self.redirect_to('login')

#PASSWORD RESET
class PasswordResetHandler(BaseHandler):
    """
    Password Reset Handler with Captcha
    """

    def get(self):
        if self.user:
            self.auth.unset_session()
        params = {
            'captchahtml': captchaBase(self),
        }
        return self.render_template('materialize/landing/password_reset.html', **params)

    def post(self):
        # check captcha
        response = self.request.POST.get('g-recaptcha-response')
        remote_ip = self.request.remote_addr

        cResponse = captcha.submit(
            response,
            self.app.config.get('captcha_private_key'),
            remote_ip)

        if cResponse.is_valid:
            # captcha was valid... carry on..nothing to see here
            pass
        else:
            _message = _(messages.captcha_error)
            self.add_message(_message, 'danger')
            return self.redirect_to('password-reset')

        #check if we got an email or username
        email_or_username = str(self.request.POST.get('email_or_username')).lower().strip()
        if utils.is_email_valid(email_or_username):
            user = self.user_model.get_by_email(email_or_username)
        else:
            auth_id = "own:%s" % email_or_username
            user = self.user_model.get_by_auth_id(auth_id)

        if user is not None:
            user_id = user.get_id()
            token = self.user_model.create_auth_token(user_id)
            email_url = self.uri_for('taskqueue-send-email')
            reset_url = self.uri_for('password-reset-check', user_id=user_id, token=token, _full=True)
            subject = _(messages.email_passwordassist_subject)

            # load email's template
            template_val = {
                "username": user.name,
                "email": user.email,
                "reset_password_url": reset_url,
                "brand_logo": self.brand['brand_logo'],
                "brand_color": self.brand['brand_color'],
                "brand_secondary_color": self.brand['brand_secondary_color'],
                "support_url": self.uri_for("contact", _full=True),
                "twitter_url": self.app.config.get('twitter_url'),
                "facebook_url": self.app.config.get('facebook_url'),
                "faq_url": self.uri_for("faq", _full=True),
                "app_name": self.app.config.get('app_name'),
            }

            body_path = "emails/reset_password.txt"
            body = self.jinja2.render_template(body_path, **template_val)
            taskqueue.add(url=email_url, params={
                'to': user.email,
                'subject': subject,
                'body': body,
                'sender': self.app.config.get('contact_sender'),
            })
            _message = _(messages.password_reset)
            self.add_message(_message, 'success')
        else:
            _message = _(messages.password_reset_invalid_email)
            self.add_message(_message, 'warning')

        return self.redirect_to('login')

class PasswordResetCompleteHandler(BaseHandler):
    """
    Handler to process the link of reset password that received the user
    """

    def get(self, user_id, token):
        verify = self.user_model.get_by_auth_token(int(user_id), token)
        params = {}
        if verify[0] is None:
            message = _(messages.password_reset_invalid_link)
            self.add_message(message, 'warning')
            return self.redirect_to('password-reset')

        else:
            user = self.user_model.get_by_id(long(user_id))
            params = {
                '_username':user.name
            }
            return self.render_template('materialize/landing/password_reset_complete.html', **params)

    def post(self, user_id, token):
        verify = self.user_model.get_by_auth_token(int(user_id), token)
        user = verify[0]
        password = self.form.password.data.strip()
        if user and self.form.validate():
            # Password to SHA512
            password = utils.hashing(password, self.app.config.get('salt'))

            user.password = security.generate_password_hash(password, length=12)
            user.put()
            # Delete token
            self.user_model.delete_auth_token(int(user_id), token)
            # Login User
            self.auth.get_user_by_password(user.auth_ids[0], password)
            self.add_message(_(messages.passwordchange_success), 'success')
            return self.redirect_to('landing')

        else:
            self.add_message(_(messages.passwords_mismatch), 'danger')
            return self.redirect_to('password-reset-check', user_id=user_id, token=token)

    @webapp2.cached_property
    def form(self):
        return forms.PasswordResetCompleteForm(self)


# ------------------------------------------------------------------------------------------- #
"""                                 NON-USER, LANDING HANDLERS                              """
# ------------------------------------------------------------------------------------------- #

class MaterializeLandingRequestHandler(BaseHandler):
    """
    Handler to show the landing page
    """

    def get(self):
        """ Returns a simple HTML form for landing """
        params = {}
        if not self.user:
            params['captchahtml'] = captchaBase(self)
        else:
            params, user_info = disclaim(self)    
            message = _(messages.welcome_message)
            self.add_message(message, 'success')     
        params['video_url'] = self.app.config.get('video_url')
        params['video_playlist'] = self.app.config.get('video_playlist')
        users = models.User.query()
        params['total_users'] = users.count()

        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')

        if self.app.config.get('landing_skin') == 'a' or self.request.get('skin') == 'a':
            return self.render_template('materialize/landing/landing_a.html', **params)
        else:
            return self.render_template('materialize/landing/landing.html', **params)

class MaterializeLandingMapRequestHandler(BaseHandler):
    """
    Handler to show the landing page
    """
    def get(self):
        """ Returns a simple HTML form for landing """

        if not self.has_reports:
            self.abort(403)

        params = {}
        if self.user:
            params, user_info = disclaim(self)   
        
        params['captchahtml'] = captchaBase(self)

        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')  
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['has_cic'] = self.app.config.get('has_cic')
        params['cartodb_cic_user'] = self.app.config.get('cartodb_cic_user')
        params['cartodb_cic_reports_table'] = self.app.config.get('cartodb_cic_reports_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        params['cartodb_markers_url'] = self.uri_for("landing", _full=True)+"default/materialize/images/markers/"

        return self.render_template('materialize/landing/base.html', **params)
        
class MaterializeLandingBlogRequestHandler(BaseHandler):
    """
        Handler for materialized blog
    """
    def get(self):
        """ returns simple html for a get request """
        if self.user_id:
            params, user_info = disclaim(self)
        else:
            params = {}        
        params['captchahtml'] = captchaBase(self)
        posts = models.BlogPost.query()
        params['total'] = posts.count()
        params['posts'] = []
        for post in posts:
            categories = ""
            for category in post.category:
                categories += str(category) + ", "
            params['posts'].append((post.key.id(), post.updated.strftime("%Y-%m-%d"), post.title, post.subtitle, post.blob_key, post.author, post.brief, categories[0:-2]))
        return self.render_template('materialize/landing/blog.html', **params)

class MaterializeLandingBlogPostRequestHandler(BaseHandler):
    """
        Handler for materialized privacy policy
    """
    def get(self, post_id):
        """ returns simple html for a get request """
        if self.user_id:
            params, user_info = disclaim(self)
        else:
            params = {} 
        params['captchahtml'] = captchaBase(self)
        blog = models.BlogPost.get_by_id(long(post_id))
        if blog is not None:
            params['title'] = blog.title
            params['subtitle'] = blog.subtitle
            params['blob_key'] = blog.blob_key
            params['author'] = blog.author
            params['content'] = blog.content
            return self.render_template('materialize/landing/blogpost.html', **params)
        else:
            return self.error(404)

class MaterializeLandingFaqRequestHandler(BaseHandler):
    """
        Handler for materialized frequented asked questions
    """
    def get(self):
        """ returns simple html for a get request """
        if self.user_id:
            params, user_info = disclaim(self)
        else:
            params = {} 
        params['captchahtml'] = captchaBase(self)
        return self.render_template('materialize/landing/faq.html', **params)

class MaterializeLandingTouRequestHandler(BaseHandler):
    """
        Handler for materialized terms of use
    """
    def get(self):
        """ returns simple html for a get request """
        if self.user_id:
            params, user_info = disclaim(self)
        else:
            params = {} 
        params['captchahtml'] = captchaBase(self)
        return self.render_template('materialize/landing/tou.html', **params)

class MaterializeLandingPrivacyRequestHandler(BaseHandler):
    """
        Handler for materialized privacy policy
    """
    def get(self):
        """ returns simple html for a get request """
        if self.user_id:
            params, user_info = disclaim(self)
        else:
            params = {} 
        params['captchahtml'] = captchaBase(self)
        return self.render_template('materialize/landing/privacy.html', **params)

class MaterializeLandingLicenseRequestHandler(BaseHandler):
    """
        Handler for materialized privacy policy
    """
    def get(self):
        """ returns simple html for a get request """
        if self.user_id:
            params, user_info = disclaim(self)
        else:
            params = {} 
        params['captchahtml'] = captchaBase(self)
        return self.render_template('materialize/landing/license.html', **params)

class MaterializeLandingContactRequestHandler(BaseHandler):
    """
        Handler for materialized contact us
    """
    def get(self):
        """ returns simple html for a get request """
        if self.user_id:
            params, user_info = disclaim(self)
        else:
            params = {} 
        params['captchahtml'] = captchaBase(self)
        if self.user:
            user_info = self.user_model.get_by_id(long(self.user_id))
            if user_info.name or user_info.last_name:
                self.form.name.data = user_info.name + " " + user_info.last_name
            if user_info.email:
                self.form.email.data = user_info.email
        params['exception'] = self.request.get('exception')

        params['t'] = str(self.request.get('t')) if len(self.request.get('t')) > 1 else 'no'

        return self.render_template('materialize/landing/contact.html', **params)

    def post(self):
        """ validate contact form """
        if not self.form.validate():
            _message = _(messages.post_error)
            self.add_message(_message, 'danger')
            return self.get()

        import bp_includes.lib.i18n as i18n
        from bp_includes.external import httpagentparser

        remote_ip = self.request.remote_addr
        city = i18n.get_city_code(self.request)
        region = i18n.get_region_code(self.request)
        country = i18n.get_country_code(self.request)
        coordinates = i18n.get_city_lat_long(self.request)
        user_agent = self.request.user_agent
        exception = self.request.POST.get('exception')
        name = self.form.name.data.strip()
        email = self.form.email.data.lower()
        message = self.form.message.data.strip()
        template_val = {
            "name": name,
            "email": email,
            "ip": remote_ip,
            "city": city,
            "region": region,
            "country": country,
            "coordinates": coordinates,
            "message": message,
            "brand_logo": self.brand['brand_logo'],
            "brand_color": self.brand['brand_color'],
            "brand_secondary_color": self.brand['brand_secondary_color']
        }
        try:
            # parsing user_agent and getting which os key to use
            # windows uses 'os' while other os use 'flavor'
            ua = httpagentparser.detect(user_agent)
            _os = ua.has_key('flavor') and 'flavor' or 'os'

            operating_system = str(ua[_os]['name']) if "name" in ua[_os] else "-"
            if 'version' in ua[_os]:
                operating_system += ' ' + str(ua[_os]['version'])
            if 'dist' in ua:
                operating_system += ' ' + str(ua['dist'])

            browser = str(ua['browser']['name']) if 'browser' in ua else "-"
            browser_version = str(ua['browser']['version']) if 'browser' in ua else "-"

            template_val = {
                "name": name,
                "email": email,
                "ip": remote_ip,
                "city": city,
                "region": region,
                "country": country,
                "coordinates": coordinates,
                "brand_logo": self.brand['brand_logo'],
                "brand_color": self.brand['brand_color'],
                "brand_secondary_color": self.brand['brand_secondary_color'],
                "browser": browser,
                "browser_version": browser_version,
                "operating_system": operating_system,
                "message": message
            }
        except Exception as e:
            logging.error("error getting user agent info: %s" % e)

        try:
            subject = _("Alguien ha enviado un mensaje")
            # exceptions for error pages that redirect to contact
            if exception != "":
                subject = "{} (Exception error: {})".format(subject, exception)

            body_path = "emails/contact.txt"
            body = self.jinja2.render_template(body_path, **template_val)

            email_url = self.uri_for('taskqueue-send-email')
            taskqueue.add(url=email_url, params={
                'to': self.app.config.get('contact_recipient'),
                'subject': subject,
                'body': body,
                'sender': self.app.config.get('contact_sender'),
            })

            message = _(messages.contact_success)
            self.add_message(message, 'success')
            return self.redirect_to('contact')

        except (AttributeError, KeyError), e:
            logging.error('Error sending contact form: %s' % e)
            message = _(messages.post_error)
            self.add_message(message, 'danger')
            return self.redirect_to('contact')

    @webapp2.cached_property
    def form(self):
        return forms.ContactForm(self)


# ------------------------------------------------------------------------------------------- #
"""                                 REGISTERED USERS HANDLERS                               """
# ------------------------------------------------------------------------------------------- #

class MaterializeWelcomeRequestHandler(BaseHandler):
    """
        Handler for materialized terms of use
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        if self.user_id:
            params, user_info = disclaim(self)
        else:
            params = {} 
        params['captchahtml'] = captchaBase(self)
        return self.render_template('materialize/users/sections/welcome.html', **params)

class MaterializeProfileRequestHandler(BaseHandler):
    """
        Handler for materialized user public profile
    """
    @user_required
    def get(self, profile_id):
        """ returns simple html for a get request """
        params, user_info = disclaim(self)
        params['captchahtml'] = captchaBase(self)
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')

        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')

        try:
            p_id = long(profile_id)
            user_profile = models.User.get_by_id(p_id)
            params['profile_name'] = user_profile.name
            params['profile_lastname'] = user_profile.last_name
            params['profile_img'] = user_profile.get_image_url()
            reports = models.Report.query(ndb.AND(models.Report.user_id == int(p_id), models.Report.cdb_id != -1))
            params['reports'] = reports
            follows = models.Followers.query(models.Followers.user_id == int(p_id))
            params['follows'] = follows
            params['profile_reports']=reports.count()
            params['profile_petitions'] = models.Petition.query(models.Petition.user_id == int(p_id)).count()
            params['profile_follows']=models.Followers.query(models.Followers.user_id == int(p_id)).count() + models.Votes.query(models.Votes.user_id == int(p_id)).count()

        except ValueError:
            logging.log("profile_id not a number, attempt to get from unique url")
            pass

        return self.render_template('materialize/users/sections/citizen.html', **params)

class MaterializeReferralsRequestHandler(BaseHandler):
    """
        Handler for materialized referrals
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        params, user_info = disclaim(self)
        params['link_referral'] = user_info.link_referral
        params['google_clientID'] = self.app.config.get('google_clientID')

        if user_info.link_referral is None:
            # create unique url for sharing & referrals purposes
            long_url = self.uri_for("register-referral",user_id=user_info.get_id(),_full=True)
            logging.info("Long URL: %s" % long_url)
            short_url = long_url
            
            #The goo.gl way:
            # post_url = 'https://www.googleapis.com/urlshortener/v1/url'            
            # payload = {'longUrl': long_url}
            # headers = {'content-type': 'application/json'}
            # r = requests.post(post_url, data=json.dumps(payload), headers=headers)
            # j = json.loads(r.text)
            # logging.info("Google response: %s" % j)
            # short_url = j['id']

            #The bit.ly way:
            try:
                api = bitly.Api(login=self.app.config.get('bitly_login'), apikey=self.app.config.get('bitly_apikey'))
                short_url=api.shorten(long_url)
                logging.info("Bitly response: %s" % short_url)
            except:
                pass

            user_info.link_referral = short_url
            reward = models.Rewards(amount = 100,earned = True, category = 'configuration',
                content = 'Activation',timestamp = utils.get_date_time(),status = 'completed')                 
            user_info.rewards.append(reward)
            user_info.put()
            params['link_referral'] = user_info.link_referral



        return self.render_template('materialize/users/sections/referrals.html', **params)

    def post(self):
        """ Get fields from POST dict """
        user_info = self.user_model.get_by_id(long(self.user_id))
        message = ''

        if not self.form.validate():
            message += messages.saving_error
            self.add_message(message, 'danger')
            return self.get()

        _emails = self.form.emails.data.replace('"','').replace('[','').replace(']','')
        logging.info("Referrals' email addresses: %s" % _emails)

        try:
            # send email
            subject = _(messages.email_referral_subject)
            if user_info.name != '':
                _username = user_info.name
            else:
                _username = user_info.username
             # load email's template
            template_val = {
                "app_name": self.app.config.get('app_name'),
                "user_email": user_info.email,
                "user_name": _username,
                "link_referral" : user_info.link_referral,
                "brand_logo": self.brand['brand_logo'],
                "brand_color": self.brand['brand_color'],
                "brand_secondary_color": self.brand['brand_secondary_color'],
                "support_url": self.uri_for("contact", _full=True),
                "twitter_url": self.app.config.get('twitter_url'),
                "facebook_url": self.app.config.get('facebook_url'),
                "faq_url": self.uri_for("faq", _full=True)
            }
            body_path = "emails/referrals.txt"
            body = self.jinja2.render_template(body_path, **template_val)

            email_url = self.uri_for('taskqueue-send-email')
            _email = _emails.split(",")
            _email = list(set(_email)) #removing duplicates

            for _email_ in _email:

                aUser = self.user_model.get_by_email(_email_)
                if aUser is not None:
                    reward = models.Rewards(amount = 0,earned = True, category = 'invite',content = _email_,
                                            timestamp = utils.get_date_time(),status = 'inelegible')                 
                    edited_userinfo = False
                    for rewards in user_info.rewards:
                        if 'invite' in rewards.category and rewards.content == reward.content:
                            user_info.rewards[user_info.rewards.index(rewards)] = reward
                            edited_userinfo = True
                    if not edited_userinfo:
                        user_info.rewards.append(reward)
                else:
                    taskqueue.add(url=email_url, params={
                        'to': str(_email_),
                        'subject': subject,
                        'body': body,
                    })
                    logging.info('Sent referral invitation to %s' % str(_email_))
                    reward = models.Rewards(amount = 0,earned = True, category = 'invite',content = _email_,
                                            timestamp = utils.get_date_time(),status = 'invited')                 
                    edited_userinfo = False
                    for rewards in user_info.rewards:
                        if 'invite' in rewards.category and rewards.content == reward.content:
                            user_info.rewards[user_info.rewards.index(rewards)] = reward
                            edited_userinfo = True
                    if not edited_userinfo:
                        user_info.rewards.append(reward)
                    
            user_info.put()

            message += " " + _(messages.invite_success)
            self.add_message(message, 'success')
            return self.get()
           
        except (KeyError, AttributeError), e:
            logging.error("Error resending invitation email: %s" % e)
            message = _(messages.post_error)
            self.add_message(message, 'danger')
            return self.redirect_to('home')
         
    @webapp2.cached_property
    def form(self):
        f = forms.ReferralsForm(self)
        return f

class MaterializeSettingsProfileRequestHandler(BaseHandler):
    """
        Handler for materialized settings profile
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        params, user_info = disclaim(self)
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')

        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')

        if not params['address_from']:
            params['address_from'] = ''

        return self.render_template('materialize/users/settings/profile.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            message = _(messages.saving_error)
            self.add_message(message, 'danger')
            return self.get()
        name = self.request.get('name')
        last_name = self.request.get('last_name')
        last_name2 = self.request.get('last_name2')
        gender = self.request.get('gender')
        scholarity = self.request.get('scholarity')
        phone = self.request.get('phone')
        birth = self.request.get('birth')
        address_from = self.request.get('address_from') if len(self.request.get('address_from'))>4 else None
        address_from_coord = self.request.get('address_from_coord')
        picture = self.request.get('picture') if len(self.request.get('picture'))>1 else None

        try:
            user_info = self.user_model.get_by_id(long(self.user_id))

            try:
                message = ''
                user_info.name = name
                user_info.last_name = last_name
                user_info.last_name2 = last_name2
                if (len(birth) > 9):
                    user_info.birth = date(int(birth[:4]), int(birth[5:7]), int(birth[8:]))
                if 'male' in gender:
                    user_info.gender = gender
                if scholarity in ('elementary','middleschool','highschool','technical','undergraduate','graduate'):
                    user_info.scholarity = scholarity
                user_info.phone = phone
                if picture is not None:
                    user_info.picture = images.resize(picture, width=180, height=180, crop_to_fit=True, quality=100)
                if address_from is not None:
                    user_info.address = models.Address()
                    user_info.address.address_from = address_from
                    if len(address_from_coord.split(',')) == 2:
                        user_info.address.address_from_coord = ndb.GeoPt(address_from_coord)
                else:
                    user_info.address = None
                user_info.put()
                message += " " + _(messages.saving_success)
                self.add_message(message, 'success')
                return self.get()

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating profile: %s ' % e)
                message = _(messages.saving_error)
                self.add_message(message, 'danger')
                return self.get()

        except (AttributeError, TypeError), e:
            login_error_message = _(messages.expired_session)
            logging.error('Error updating profile: %s' % e)
            self.add_message(login_error_message, 'danger')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        f = forms.SettingsProfileForm(self)
        return f

class MaterializeSettingsSocialRequestHandler(BaseHandler):
    @user_required
    def post(self):
        _user_id = int(self.request.get('user_id'))

        if not self.user_id or int(self.user_id) != _user_id:
            self.abort(403)

        reportDict = {}

        kind = self.request.get('kind')
        first_name = self.request.get('first_name')
        last_name = self.request.get('last_name')
        gender = self.request.get('gender')
        picture = self.request.get('picture')
        cover = self.request.get('cover')
        social_id = self.request.get('id')

        try:
            if kind == 'google':
                social = models.UserGOOG.query(models.UserGOOG.user_id == _user_id).get()
                if social is None:
                    social = models.UserGOOG()
                if social_id != 'none':
                    user_info = self.user_model.get_by_id(long(self.user_id))
                    user_info.google_ID = str(social_id)
                    user_info.put()

            if kind == 'facebook':
                social = models.UserFB.query(models.UserFB.user_id == _user_id).get()
                if social is None:
                    social = models.UserFB()
                if social_id != 'none':
                    user_info = self.user_model.get_by_id(long(self.user_id))
                    user_info.facebook_ID = str(social_id)
                    user_info.put()
                age_range = self.request.get('age_range')
                social.age_range = int(age_range) if age_range != 'none' else social.age_range

            social.user_id = _user_id

            social.first_name = first_name if first_name != 'none' else social.first_name
            social.last_name = last_name if last_name != 'none' else social.last_name
            social.gender = gender if gender != 'none' else social.gender
            social.picture = picture if picture != 'none' else social.picture
            social.cover = cover if cover != 'none' else social.cover
            social.put()
            reportDict['status'] = 'success'
            reportDict['contents'] = 'user social profile for kind %s has been saved' % kind

        except Exception as e:
            reportDict['status'] = 'error'
            reportDict['contents'] = '%s' % e
            pass

        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeSettingsAddressRequestHandler(BaseHandler):
    """
        Handler for materialized settings home
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        params, user_info = disclaim(self)
        params['zipcode'] = ''
        params['neighborhood'] = False
        params['latlng'] = 'null'
            
        return self.render_template('materialize/users/settings/address.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            message = _(messages.saving_error)
            message += "Tip: Asegura que el marcador en el mapa se encuentre en tu zona."
            self.add_message(message, 'danger')
            return self.get()
        zipcode = int(self.form.zipcode.data)
        ageb = self.form.ageb.data
        latlng = self.form.latlng.data
        neighborhood = self.form.neighborhood.data
        municipality = self.form.municipality.data
        state = self.form.state.data
        region = self.form.region.data

        try:
            user_info = self.user_model.get_by_id(long(self.user_id))
            try:
                
                user_info.address.zipcode = int(zipcode)
                user_info.address.ageb = ageb
                user_info.address.neighborhood = neighborhood
                user_info.address.municipality = municipality
                user_info.address.state = state
                user_info.address.region = region
                user_info.address.latlng = ndb.GeoPt(latlng)
                user_info.put()

                message = ''                
                message += " " + _(messages.saving_success)
                self.add_message(message, 'success')
                return self.get()

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating address: ' + e)
                message = _(messages.saving_error)
                self.add_message(message, 'danger')
                return self.get()

        except (AttributeError, TypeError), e:
            login_error_message = _(messages.expired_session)
            self.add_message(login_error_message, 'danger')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        f = forms.AddressForm(self)
        return f

class MaterializeSettingsReferralsRequestHandler(BaseHandler):
    """
        Handler for materialized settings referrals
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        params, user_info = disclaim(self)
        params['referrals'] = []
        rewards = user_info.rewards
        rewards.reverse
        unique_emails = []
        page = 1
        if self.request.get('p') != '':
            page = 1 + int(self.request.get('p'))
        offset = (page - 1)*51
        last = page*51
        if last > len(rewards):
            last = len(rewards)
        for i in range(offset, last):
            if 'invite' in rewards[i].category and rewards[i].content != '' and 'Invitado Invictus' not in rewards[i].content and rewards[i].content not in unique_emails:
                params['referrals'].append(rewards[i])
                unique_emails.append(rewards[i].content)
                if rewards[i].status == 'invited':
                    aUser = self.user_model.get_by_email(rewards[i].content)
                    if aUser is not None:
                        params['referrals'][params['referrals'].index(rewards[i])].status = 'inelegible'

        params['page'] = page
        params['last_page'] = int(len(rewards)/50)
        params['total'] = len(params['referrals'])
        params['grand_total'] = int(len(rewards))
        params['properties'] = ['timestamp','content','status']

        return self.render_template('materialize/users/settings/referrals.html', **params)

    def post(self):
        """ Get fields from POST dict """
        user_info = self.user_model.get_by_id(long(self.user_id))
        message = ''

        if not self.form.validate():
            message += messages.saving_error
            self.add_message(message, 'error')
            return self.get()

        _emails = self.form.emails.data.replace('"','').replace('[','').replace(']','')
        logging.info("Referrals' email addresses: %s" % _emails)

        try:
            # send email
            subject = _(messages.email_referral_subject)
            if user_info.name != '':
                _username = user_info.name
            else:
                _username = user_info.username
             # load email's template
            template_val = {
                "app_name": self.app.config.get('app_name'),
                "user_email": user_info.email,
                "user_name": _username,
                "link_referral" : user_info.link_referral,
                "brand_logo": self.brand['brand_logo'],
                "brand_color": self.brand['brand_color'],
                "brand_secondary_color": self.brand['brand_secondary_color'],
                "support_url": self.uri_for("contact", _full=True),
                "twitter_url": self.app.config.get('twitter_url'),
                "facebook_url": self.app.config.get('facebook_url'),
                "faq_url": self.uri_for("faq", _full=True)
            }
            body_path = "emails/referrals.txt"
            body = self.jinja2.render_template(body_path, **template_val)

            email_url = self.uri_for('taskqueue-send-email')
            _email = _emails.split(",")

            for _email_ in _email:
                taskqueue.add(url=email_url, params={
                    'to': str(_email_),
                    'subject': subject,
                    'body': body,
                })
                reward = models.Rewards(amount = 0,earned = True, category = 'invite',content = _email_,
                                        timestamp = utils.get_date_time(),status = 'invited')    
                
                edited_userinfo = False
                for rewards in user_info.rewards:
                    if 'invite' in rewards.category and rewards.content == reward.content:
                        user_info.rewards[user_info.rewards.index(rewards)] = reward
                        edited_userinfo = True
                if not edited_userinfo:
                    user_info.rewards.append(reward)

                user_info.put()

            message += " " + _(messages.invite_success)
            self.add_message(message, 'success')
            return self.get()
           
        except (KeyError, AttributeError), e:
            logging.error("Error resending invitation email: %s" % e)
            message = _(messages.post_error)
            self.add_message(message, 'danger')
            return self.redirect_to('home')

          
    @webapp2.cached_property
    def form(self):
        f = forms.ReferralsForm(self)
        return f

class MaterializeSettingsAccountRequestHandler(BaseHandler):
    @user_required
    def get(self):
        """ returns simple html for a get request """
        params, user_info = disclaim(self)
        params['captchahtml'] = captchaBase(self)
        for auth_id in user_info.auth_ids:
            logging.info("auth id: %s" % auth_id)
        return self.render_template('materialize/users/settings/account.html', **params)

class MaterializeSettingsEmailRequestHandler(BaseHandler):
    """
        Handler for materialized settings email
    """
    @user_required
    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            _message = _(messages.saving_error)
            self.add_message(_message, 'danger')
            return self.redirect_to('materialize-settings-account')
        new_email = self.form.new_email.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = self.user_model.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username
            # Password to SHA512
            password = utils.hashing(password, self.app.config.get('salt'))

            try:
                # authenticate user by its password
                user = self.user_model.get_by_auth_password(auth_id, password)

                # if the user change his/her email address
                if new_email != user.email:

                    # check whether the new email has been used by another user
                    aUser = self.user_model.get_by_email(new_email)
                    if aUser is not None:
                        message = _("Sorry, email %s is already in use." % new_email)
                        self.add_message(message, 'danger')
                        return self.redirect_to('materialize-settings-account')

                    # send email
                    subject = _(messages.email_emailchanged_subject)
                    user_token = self.user_model.create_auth_token(self.user_id)
                    confirmation_url = self.uri_for("materialize-email-changed-check",
                                                    user_id=user_info.get_id(),
                                                    encoded_email=utils.encode(new_email),
                                                    token=user_token,
                                                    _full=True)
                    if user.name != '':
                        _username = user.name
                    else:
                        _username = user.email
                    # load email's template
                    template_val = {
                        "app_name": self.app.config.get('app_name'),
                        "username": _username,
                        "new_email": new_email,
                        "confirmation_url": confirmation_url,
                        "brand_logo": self.brand['brand_logo'],
                        "brand_color": self.brand['brand_color'],
                        "brand_secondary_color": self.brand['brand_secondary_color'],
                        "support_url": self.uri_for("contact", _full=True),
                        "twitter_url": self.app.config.get('twitter_url'),
                        "facebook_url": self.app.config.get('facebook_url'),
                        "faq_url": self.uri_for("faq", _full=True)
                    }

                    old_body_path = "emails/email_changed_notification_old.txt"
                    old_body = self.jinja2.render_template(old_body_path, **template_val)

                    new_body_path = "emails/email_changed_notification_new.txt"
                    new_body = self.jinja2.render_template(new_body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url=email_url, params={
                        'to': user.email,
                        'subject': subject,
                        'body': old_body,
                    })
                    taskqueue.add(url=email_url, params={
                        'to': new_email,
                        'subject': subject,
                        'body': new_body,
                    })

                    # display successful message
                    msg = _(messages.emailchanged_success)
                    self.add_message(msg, 'success')
                    return self.redirect_to('materialize-settings-account')

                else:
                    self.add_message(_(messages.emailchanged_error), "warning")
                    return self.redirect_to('materialize-settings-account')


            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _(messages.password_wrong)
                self.add_message(message, 'danger')
                return self.redirect_to('materialize-settings-account')

        except (AttributeError, TypeError), e:
            login_error_message = _(messages.expired_session)
            self.add_message(login_error_message, 'danger')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditEmailForm(self)

class MaterializeEmailChangedCompleteHandler(BaseHandler):
    """
    Handler for completed email change
    Will be called when the user click confirmation link from email
    """

    @user_required
    def get(self, user_id, encoded_email, token):
        verify = self.user_model.get_by_auth_token(int(user_id), token)
        email = utils.decode(encoded_email)
        if verify[0] is None:
            message = _(messages.used_activation_link)
            self.add_message(message, 'warning')
            self.redirect_to('landing')

        else:
            # save new email
            user = verify[0]
            x = ndb.Key("Unique", "User.username:%s" % user.email).get()
            y = ndb.Key("Unique", "User.auth_id:own:%s" % user.email).get()
            z = ndb.Key("Unique", "User.email:%s" % user.email).get()
            ndb.Key("Unique", "User.username:%s" % user.email).delete_async()
            ndb.Key("Unique", "User.auth_id:own:%s" % user.email).delete_async()
            ndb.Key("Unique", "User.email:%s" % user.email).delete_async()

            for i in range(0,len(user.auth_ids)):
                if user.auth_ids[i] == "own:%s" % user.email:
                    user.auth_ids[i] = "own:%s" % email
                    break
            user.email = email
            user.username = email
            user.put()

            x.key = ndb.Key("Unique", "User.username:%s" % user.email)
            y.key = ndb.Key("Unique", "User.auth_id:own:%s" % user.email)
            z.key = ndb.Key("Unique", "User.email:%s" % user.email)
            x.put()
            y.put()
            z.put()


            # delete token
            self.user_model.delete_auth_token(int(user_id), token)
            # add successful message and redirect
            message = _(messages.emailchanged_confirm)
            self.add_message(message, 'success')
            self.redirect_to('landing')

class MaterializeSettingsPasswordRequestHandler(BaseHandler):
    """
        Handler for materialized settings password
    """
    @user_required
    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            self.add_message(_(messages.passwords_mismatch), 'danger')
            return self.redirect_to('materialize-settings-account')

        current_password = self.form.current_password.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = self.user_model.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username

            # Password to SHA512
            current_password = utils.hashing(current_password, self.app.config.get('salt'))
            try:
                user = self.user_model.get_by_auth_password(auth_id, current_password)
                # Password to SHA512
                password = utils.hashing(password, self.app.config.get('salt'))
                user.password = security.generate_password_hash(password, length=12)
                user.put()

                # send email
                subject = messages.email_passwordchanged_subject
                if user.name != '':
                    _username = user.name
                else:
                    _username = user.email
                # load email's template
                template_val = {
                    "app_name": self.app.config.get('app_name'),
                    "username": _username,
                    "email": user.email,
                    "reset_password_url": self.uri_for("password-reset", _full=True),
                    "brand_logo": self.brand['brand_logo'],
                    "brand_color": self.brand['brand_color'],
                    "brand_secondary_color": self.brand['brand_secondary_color'],
                    "support_url": self.uri_for("contact", _full=True),
                    "twitter_url": self.app.config.get('twitter_url'),
                    "facebook_url": self.app.config.get('facebook_url'),
                    "faq_url": self.uri_for("faq", _full=True)
                }
                email_body_path = "emails/password_changed.txt"
                email_body = self.jinja2.render_template(email_body_path, **template_val)
                email_url = self.uri_for('taskqueue-send-email')
                taskqueue.add(url=email_url, params={
                    'to': user.email,
                    'subject': subject,
                    'body': email_body,
                    'sender': self.app.config.get('contact_sender'),
                })

                #Login User
                self.auth.get_user_by_password(user.auth_ids[0], password)
                self.add_message(_(messages.passwordchange_success), 'success')
                return self.redirect_to('materialize-settings-account')
            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _(messages.password_wrong)
                self.add_message(message, 'danger')
                return self.redirect_to('materialize-settings-account')
        except (AttributeError, TypeError), e:
            login_error_message = _(messages.expired_session)
            self.add_message(login_error_message, 'danger')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditPasswordForm(self)

class MaterializeSettingsDeleteRequestHandler(BaseHandler):
    """
        Handler for materialized settings delete account
    """
    @user_required
    def post(self, **kwargs):
        # check captcha
        response = self.request.POST.get('g-recaptcha-response')
        remote_ip = self.request.remote_addr

        cResponse = captcha.submit(
            response,
            self.app.config.get('captcha_private_key'),
            remote_ip)

        if cResponse.is_valid:
            # captcha was valid... carry on..nothing to see here
            pass
        else:
            _message = _(messages.captcha_error)
            self.add_message(_message, 'danger')
            return self.redirect_to('materialize-settings-account')

        if not self.form.validate():
            message = _(messages.password_wrong)
            self.add_message(message, 'danger')
            return self.redirect_to('materialize-settings-account')

        password = self.form.password.data.strip()

        try:

            user_info = self.user_model.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username
            password = utils.hashing(password, self.app.config.get('salt'))

            try:
                # authenticate user by its password
                user = self.user_model.get_by_auth_password(auth_id, password)
                if user:
                    # Delete Social Login
                    # for social in models_boilerplate.SocialUser.get_by_user(user_info.key):
                    #     social.key.delete()

                    user_info.key.delete()

                    ndb.Key("Unique", "User.username:%s" % user.username).delete_async()
                    ndb.Key("Unique", "User.auth_id:own:%s" % user.username).delete_async()
                    ndb.Key("Unique", "User.email:%s" % user.email).delete_async()

                    #TODO: Delete UserToken objects, Delete Home if Admin

                    self.auth.unset_session()

                    # display successful message
                    msg = _(messages.account_delete_success)
                    self.add_message(msg, 'success')
                    return self.redirect_to('landing')
                else:
                    message = _(messages.password_wrong)
                    self.add_message(message, 'danger')
                    return self.redirect_to('materialize-settings-account')

            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _(messages.password_wrong)
                self.add_message(message, 'danger')
                return self.redirect_to('materialize-settings-account')

        except (AttributeError, TypeError), e:
            login_error_message = _(messages.expired_session)
            self.add_message(login_error_message, 'danger')
            self.redirect_to('landing')

    @webapp2.cached_property
    def form(self):
        return forms.DeleteAccountForm(self)

class MaterializeTutorialsRequestHandler(BaseHandler):
    """
        Handler for materialized terms of use
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        params, user_info = disclaim(self)
        return self.render_template('materialize/users/sections/tutorials.html', **params)


# ------------------------------------------------------------------------------------------- #
"""                                 REGISTERED OPERATORS HANDLERS                           """
# ------------------------------------------------------------------------------------------- #

#ORGANIZATION ACCESS
class MaterializeOrganizationDashboardRequestHandler(BaseHandler):
    @user_required
    def get(self):
        if self.has_reports and (self.user_is_callcenter or self.user_is_secretary or self.user_is_agent or self.user_is_operator): #modified for every special access to be able to see it
            params = {}
            reports = models.Report.query()
            users = self.user_model.query()
            params['sum_users'] = users.count()
            params['sum_reports'] = reports.count()
            params['cartodb_user'] = self.app.config.get('cartodb_user')
            params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
            params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
            params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
            return self.render_template('materialize/users/operators/dashboard.html', **params)
        self.abort(403)

class MaterializeOrganizationNewReportHandler(BaseHandler):
    """
    Handler for materialized home
    """  
    @user_required
    def get(self):
        """ Returns a simple HTML form for materialize home """

        if not self.has_reports:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####

        names=['---']
        if not self.user_is_callcenter:
            if self.user_is_secretary:    
                #If secretary            
                secretaries = models.Secretary.get_admin_by_email(user_info.email)
                if secretaries is not None:
                    names[0]=secretaries.name
            elif self.user_is_operator:
                #If operator
                operators = models.Operator.get_by_email(user_info.email)
                agencyList=[]
                for operator in operators:
                    agencyList.append(ndb.Key(models.Agency, operator.agency_id))
                agencies = ndb.get_multi(agencyList)
            elif self.user_is_agent: 
                #If agent
                agencies = models.Agency.get_admin_by_email(user_info.email)
            if self.user_is_operator or self.user_is_agent:
                #Process
                secretaries = []
                for agency in agencies:
                    if agency.secretary_id is not None:
                        secretaries.append(agency.secretary_id)
                secretaries = list(set(secretaries))
                if len(secretaries)>0:
                    for secretaryID in secretaries:
                        _secretary = models.Secretary.get_by_id(long(secretaryID))
                        if _secretary:
                            names[0]=_secretary.name
                            break
           
        params['secs']= names[0]
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')

        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')


        if self.user_is_secretary or self.user_is_agent or self.user_is_operator or self.user_is_callcenter:
            return self.render_template('materialize/users/operators/new_report.html', **params)
        self.abort(403)
        
    @user_required
    def post(self):

        """ Get fields from POST dict """
        if not self.has_reports:
            self.abort(403)
                        
        address_from = self.request.get('address_from')
        address_detail = self.request.get('address_detail')
        address_from_coord = self.request.get('address_from_coord')
        catGroup = self.request.get('catGroup')
        subCat = self.request.get('subCat')
        description = self.request.get('description')
        when = self.request.get('when')
        via = self.request.get('via')
        contact_info = self.request.get('usercontact')
        folio = self.request.get('folio') if self.request.get('folio') != "" else "-1"
        
        try:
            user_report = models.Report()
            user_report.user_id = int(self.user_id) if int(self.user_id) is not None else -1
            user_report.address_from_coord = ndb.GeoPt(address_from_coord)
            user_report.address_from = address_from
            user_report.address_detail = address_detail
            user_report.when = date(int(when[:4]), int(when[5:7]), int(when[8:]))
            user_report.title = u'%s #%s' % (self.app.config.get('app_name'),subCat)
            user_report.description = description
            user_report.group_category = catGroup
            user_report.sub_category  = subCat
            user_report.via  = via
            user_report.contact_info  = contact_info
            user_report.status = 'assigned'
            user_report.folio = folio
            user_report.is_manual = True
            user_report.put()

            if hasattr(self.request.POST['file'], 'filename'):
                #create attachment
                from google.appengine.api import urlfetch
                from poster.encode import multipart_encode, MultipartParam
                
                urlfetch.set_default_fetch_deadline(45)

                payload = {}
                upload_url = blobstore.create_upload_url('/report/image/upload/%s' %(user_report.key.id()))
                file_data = self.request.POST['file']
                payload['file'] = MultipartParam('file', filename=file_data.filename,
                                                         filetype=file_data.type,
                                                         fileobj=file_data.file)
                data,headers= multipart_encode(payload)
                t = urlfetch.fetch(url=upload_url, payload="".join(data), method=urlfetch.POST, headers=headers)
                
                logging.info('t.content: %s' % t.content)
                
                if t.content == 'success':
                    cartoInsert(self, user_report.key.id(), True, True)
                else:
                    message = _(messages.attach_error)
                    self.add_message(message, 'danger')            
                    return self.get()                    
            else:
                cartoInsert(self, user_report.key.id(), True, True)

        except Exception as e:
            logging.info('error in post: %s' % e)
            message = _(messages.saving_error)
            self.add_message(message, 'danger')
            return self.get()

class MaterializeOrganizationNewReportSuccessHandler(BaseHandler):
    """
    Handler for materialized home
    """  
    @user_required
    def get(self):
        """ Returns a simple HTML form for materialize home """
        if not self.has_reports:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####

        params['ticket'] = self.request.get('ticket')
        params['report_key'] = self.request.get('report_key')

        if self.user_is_secretary:
            params['level'] = 'materialize-secretary-report'
            params['inbox'] = 'materialize-secretary-inbox'
        if self.user_is_agent:
            params['level'] = 'materialize-agent-report'
            params['inbox'] = 'materialize-agent-inbox'
        if self.user_is_operator:
            params['level'] = 'materialize-operator-report'
            params['inbox'] = 'materialize-operator-inbox'
        if self.user_is_callcenter:
            params['level'] = 'materialize-callcenter-report'
            params['inbox'] = 'materialize-callcenter-inbox'
        
        return self.render_template('materialize/users/operators/new_report_success.html', **params)
        
class MaterializeOrganizationManualHandler(BaseHandler):
    """
        Handler for materialized operators manual
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        params, user_info = disclaim(self)
        return self.render_template('materialize/users/operators/manual.html', **params)

class MaterializeOrganizationUsersHandler(BaseHandler):
    """
        Handler for materialized operators users list
    """
    @user_required
    def get(self):
        if self.has_reports and (self.user_is_secretary or self.user_is_agent or self.user_is_operator or self.user_is_callcenter):
            """ returns simple html for a get request """
            params, user_info = disclaim(self)
            p = self.request.get('p')
            q = self.request.get('q')
            c = self.request.get('c')
            forward = True if p not in ['prev'] else False
            cursor = Cursor(urlsafe=c)

            if q:
                try:
                    qry = self.user_model.get_by_id(long(q.lower()))
                    count = 1 if qry else 0
                except Exception as e:
                    logging.info('Exception at query: %s; trying with email' % e)
                    qry = self.user_model.get_by_email(q.lower())
                    count = 1 if qry else 0
                users = []
                if qry:
                    users.append(qry)
            else:
                qry = self.user_model.query()
                count = qry.count()

                PAGE_SIZE = 50
                if forward:
                    users, next_cursor, more = qry.order(-self.user_model.last_login, self.user_model.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
                    if next_cursor and more:
                        self.view.next_cursor = next_cursor
                    if c:
                        self.view.prev_cursor = cursor.reversed()
                else:
                    users, next_cursor, more = qry.order(self.user_model.last_login, self.user_model.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
                    users = list(reversed(users))
                    if next_cursor and more:
                        self.view.prev_cursor = next_cursor
                    self.view.next_cursor = cursor.reversed()
                
            def pager_url(p, cursor):
                params = OrderedDict()
                if q:
                    params['q'] = q
                if p in ['prev']:
                    params['p'] = p
                if cursor:
                    params['c'] = cursor.urlsafe()
                return self.uri_for('materialize-organization-users', **params)

            self.view.pager_url = pager_url
            self.view.q = q

            params["list_columns"] = [('username', 'Email'),
                                 ('name', 'Nombre'),
                                 ('last_name', 'Apellido'),
                                 ('last_login', u'Último ingreso')
                                 ]
            params["users"] = users
            params["count"] = count
            return self.render_template('materialize/users/operators/users.html', **params)

        self.abort(403)

class MaterializeOrganizationExportUsersHandler(BaseHandler):
    """
        Handler for materialized operators export users list
    """
    @user_required
    def get(self):
        if self.user_is_secretary or self.user_is_agent or self.user_is_operator or self.user_is_callcenter:
            import csv, json
            from google.appengine.api import urlfetch
            urlfetch.set_default_fetch_deadline(45)
            url = self.app.config.get('users_export_url')
            result = urlfetch.fetch(url)
            if result.status_code == 200:
                data = json.loads(result.content)                
                writer = csv.writer(self.response.out)
                writer.writerow(["name", "last_name","credibility", "created_at", "address", "phone", "last_login", "birth", "gender", "image_url", "identifier", "email"])
                for item in data['items']:
                    writer.writerow([ item['name'].encode('utf8'), item['last_name'].encode('utf8'), item['credibility'], item['created_at'], item['address'].replace(',',';').encode('utf8'), item['phone'], item['last_login'], item['birth'], item['gender'], item['image_url'], "'%s"%item['identifier'], item['email'].encode('utf8') ])
                        
            self.response.headers['Content-Type'] = 'application/csv'
            self.response.headers['Content-Disposition'] = 'attachment; filename=usuarios.csv'
            writer = csv.writer(self.response.out)
        else:
            self.abort(403)

class MaterializeOrganizationExportReportsHandler(BaseHandler):
    """
        Handler for materialized operators export users list
    """
    @user_required
    def get(self):
        if self.has_reports and (self.user_is_secretary or self.user_is_agent or self.user_is_operator or self.user_is_callcenter):
            import csv, json
            from google.appengine.api import urlfetch
            urlfetch.set_default_fetch_deadline(45)
            url = self.app.config.get('reports_export_url')
            result = urlfetch.fetch(url)
            if result.status_code == 200:
                data = json.loads(result.content)                
                writer = csv.writer(self.response.out)
                writer.writerow(["rating", "via", "sub_category", "contact_info", "urgent", "req_deletion", "address_lon", "terminated", "folio", "user_id", "title", "cdb_id", "group_category", "when", "address_lat", "status", "updated", "address_from", "description", "created", "follows", "emailed_72", "image_url"])
                for item in data['items']:
                    writer.writerow([ item['rating'], item['via'], item['sub_category'].encode('utf8'), item['contact_info'].encode('utf8'), item['urgent'], item['req_deletion'], item['address_lon'], item['terminated'], item['folio'], "'%s"%item['user_id'], item['title'].encode('utf8'), item['cdb_id'], item['group_category'].encode('utf8'), item['when'], item['address_lat'], item['status'], item['updated'], item['address_from'].encode('utf8'), item['description'].encode('utf8'), item['created'], item['follows'], item['emailed_72'], str(item['image_url'])  ])
                        
            self.response.headers['Content-Type'] = 'application/csv'
            self.response.headers['Content-Disposition'] = 'attachment; filename=reportes.csv'
            writer = csv.writer(self.response.out)
        else:
            self.abort(403)

class MaterializeOrganizationDirectoryRequestHandler(BaseHandler):
    @user_required
    def get(self):
        params, user_info = disclaim(self)

        return self.render_template('materialize/users/sections/directory.html', **params)

#REPORTS INBOXES
class MaterializeOrganizationUrgentsHandler(BaseHandler):
    @user_required
    def get(self):
        if self.has_reports and (self.user_is_secretary or self.user_is_agent or self.user_is_operator or self.user_is_callcenter):
            params={}
            user_info = self.user_model.get_by_id(long(self.user_id))            
            if self.user_is_callcenter:
                names = []
                _group = models.GroupCategory.query()
                for group in _group:
                    if group.get_agencies().count() > 0:
                        names.append(group.name)
            elif self.user_is_secretary:
                secretary = models.Secretary.get_admin_by_email(user_info.email)
                agencies = models.Agency.query(models.Agency.secretary_id == secretary.key.id())
                group_categories = []
                for agency in agencies:
                    if agency.group_category_id is not None:
                        group_categories.append(agency.group_category_id)
                group_categories = list(set(group_categories))
                names=[]
                if len(group_categories)>0:
                    for groupID in group_categories:
                        names.append(models.GroupCategory.get_by_id(long(groupID)).name)
                else:
                    names.append('---')
            elif self.user_is_agent:
                agencies = models.Agency.get_admin_by_email(user_info.email)
                group_categories = []
                for agency in agencies:
                    if agency.group_category_id is not None:
                        group_categories.append(agency.group_category_id)
                group_categories = list(set(group_categories))
                names=[]
                if len(group_categories)>0:
                    for groupID in group_categories:
                        _group = models.GroupCategory.get_by_id(long(groupID))
                        if _group:
                            names.append(_group.name)
                else:
                    names.append('---')
            elif self.user_is_operator:
                operators = models.Operator.get_by_email(user_info.email)
                agencies=[]
                for operator in operators:
                    agencies.append(operator.agency_id)
                group_categories = []
                for agencyID in agencies:
                    agency = models.Agency.get_by_id(long(agencyID))
                    if agency.group_category_id is not None:
                        group_categories.append(agency.group_category_id)
                group_categories = list(set(group_categories))
                names=[]
                if len(group_categories)>0:
                    for groupID in group_categories:
                        _group = models.GroupCategory.get_by_id(long(groupID))
                        if _group:
                            names.append(_group.name)
                else:
                    names.append('---') 

            status = self.request.get('status') if (self.request.get('status') or self.request.get('status') != "") else False
            ticket = int(self.request.get('ticket')) if (self.request.get('ticket') or self.request.get('ticket') != "") else False
            folio = self.request.get('folio') if (self.request.get('folio') or self.request.get('folio') != "") else False
            groupCat = self.request.get('cat') if (self.request.get('groupCat') or self.request.get('cat') != "") else False
                        
            p = self.request.get('p')
            q = self.request.get('q')
            c = self.request.get('c')
            forward = True if p not in ['prev'] else False
            cursor = Cursor(urlsafe=c)

            if q:
                reports = models.Report.query(models.Report.group_category == names[0])            
                count = reports.count()
            else:
                if groupCat:
                    reports = models.Report.query(models.Report.group_category == groupCat)
                    params['ddfill'] = groupCat
                else:
                    if self.user_is_callcenter:
                        reports = models.Report.query()
                        params['ddfill'] = 'TODOS'
                    else:
                        if names[0]=='---':
                            reports = models.Report.query(models.Report.group_category == 'inexistent')
                        else:
                            reports = models.Report.query(models.Report.group_category == names[0])
                        params['ddfill'] = names[0]
                if status:
                    reports = reports.filter(models.Report.status == status) if status != 'pending' else reports.filter(models.Report.status.IN(['assigned', 'halted', 'answered', 'working']))
                    params['ddfillstat'] = get_status(status)
                else:
                    if self.user_is_callcenter:
                        params['ddfillstat'] = 'TODOS'
                    else:
                        reports = reports.filter(models.Report.status.IN(['assigned', 'halted', 'answered', 'working']))
                        params['ddfillstat'] = get_status('pending')
                if ticket:    
                    reports = reports.filter(models.Report.cdb_id == ticket)
                if folio:     
                    reports = reports.filter(models.Report.folio == folio)
               
                reports = reports.filter(models.Report.urgent == True)
                count = reports.count()
                PAGE_SIZE = 50
                if forward:
                    reports, next_cursor, more = reports.order(-models.Report.created, models.Report.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
                    if next_cursor and more:
                        self.view.next_cursor = next_cursor
                    if c:
                        self.view.prev_cursor = cursor.reversed()
                else:
                    reports, next_cursor, more = reports.order(models.Report.created, models.Report.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
                    reports = list(reversed(reports))
                    if next_cursor and more:
                        self.view.prev_cursor = next_cursor
                    self.view.next_cursor = cursor.reversed()

            def pager_url(p, cursor):
                params = OrderedDict()
                if q:
                    params['q'] = q
                if status:
                    params['status'] = status
                if ticket:
                    params['ticket'] = ticket
                if folio:
                    params['folio'] = folio
                if groupCat:
                    params['cat'] = groupCat
                if p in ['prev']:
                    params['p'] = p
                if cursor:
                    params['c'] = cursor.urlsafe()
                return self.uri_for('materialize-organization-urgents', **params)
                

            self.view.pager_url = pager_url
            self.view.q = q

            params['statusval'] = get_status(status) if status else ""
            params['ticketval'] = ticket if ticket else ""
            params['folioval'] = folio if folio else ""
            params['catGroup'] = groupCat if groupCat else ""
            params['reports'] = reports
            params['count'] = count
            params['cats'] = sorted(names) if names else names
            if self.user_is_callcenter:
                params['level'] = 'materialize-callcenter-report'
            elif self.user_is_secretary:
                params['level'] = 'materialize-secretary-report'
            elif self.user_is_agent:
                params['level'] = 'materialize-agent-report'
            elif self.user_is_operator: 
                params['level'] = 'materialize-operator-report'
            params['inbox'] = 'materialize-organization-urgents'
            return self.render_template('materialize/users/operators/inbox.html', **params)
        
        self.abort(403)

class MaterializeOrganizationUserReportsHandler(BaseHandler):
    @user_required
    def get(self, user_id):
        if self.has_reports and (self.user_is_secretary or self.user_is_agent or self.user_is_operator or self.user_is_callcenter):
            params={}
            user_info = self.user_model.get_by_id(long(self.user_id))            
            if self.user_is_callcenter:
                names = []
                _group = models.GroupCategory.query()
                for group in _group:
                    if group.get_agencies().count() > 0:
                        names.append(group.name)
            elif self.user_is_secretary:
                secretary = models.Secretary.get_admin_by_email(user_info.email)
                agencies = models.Agency.query(models.Agency.secretary_id == secretary.key.id())
                group_categories = []
                for agency in agencies:
                    if agency.group_category_id is not None:
                        group_categories.append(agency.group_category_id)
                group_categories = list(set(group_categories))
                names=[]
                if len(group_categories)>0:
                    for groupID in group_categories:
                        names.append(models.GroupCategory.get_by_id(long(groupID)).name)
                else:
                    names.append('---')
            elif self.user_is_agent:
                agencies = models.Agency.get_admin_by_email(user_info.email)
                group_categories = []
                for agency in agencies:
                    if agency.group_category_id is not None:
                        group_categories.append(agency.group_category_id)
                group_categories = list(set(group_categories))
                names=[]
                if len(group_categories)>0:
                    for groupID in group_categories:
                        _group = models.GroupCategory.get_by_id(long(groupID))
                        if _group:
                            names.append(_group.name)
                else:
                    names.append('---')
            elif self.user_is_operator:
                operators = models.Operator.get_by_email(user_info.email)
                agencies=[]
                for operator in operators:
                    agencies.append(operator.agency_id)
                group_categories = []
                for agencyID in agencies:
                    agency = models.Agency.get_by_id(long(agencyID))
                    if agency.group_category_id is not None:
                        group_categories.append(agency.group_category_id)
                group_categories = list(set(group_categories))
                names=[]
                if len(group_categories)>0:
                    for groupID in group_categories:
                        _group = models.GroupCategory.get_by_id(long(groupID))
                        if _group:
                            names.append(_group.name)
                else:
                    names.append('---') 

            status = self.request.get('status') if (self.request.get('status') or self.request.get('status') != "") else False
            ticket = int(self.request.get('ticket')) if (self.request.get('ticket') or self.request.get('ticket') != "") else False
            folio = self.request.get('folio') if (self.request.get('folio') or self.request.get('folio') != "") else False
            groupCat = self.request.get('cat') if (self.request.get('groupCat') or self.request.get('cat') != "") else False
                        
            p = self.request.get('p')
            q = self.request.get('q')
            c = self.request.get('c')
            forward = True if p not in ['prev'] else False
            cursor = Cursor(urlsafe=c)

            if q:
                reports = models.Report.query(models.Report.group_category == names[0])            
                count = reports.count()
            else:
                if groupCat:
                    reports = models.Report.query(models.Report.group_category == groupCat)
                    params['ddfill'] = groupCat
                else:
                    if self.user_is_callcenter:
                        reports = models.Report.query()
                        params['ddfill'] = 'TODOS'
                    else:
                        if names[0]=='---':
                            reports = models.Report.query(models.Report.group_category == 'inexistent')
                        else:
                            reports = models.Report.query(models.Report.group_category == names[0])
                        params['ddfill'] = names[0]
                if status:
                    reports = reports.filter(models.Report.status == status) if status != 'pending' else reports.filter(models.Report.status.IN(['assigned', 'halted', 'answered', 'working']))
                    params['ddfillstat'] = get_status(status)
                else:
                    if self.user_is_callcenter:
                        params['ddfillstat'] = 'TODOS'
                    else:
                        reports = reports.filter(models.Report.status.IN(['assigned', 'halted', 'answered', 'working']))
                        params['ddfillstat'] = get_status('pending')
                if ticket:    
                    reports = reports.filter(models.Report.cdb_id == ticket)
                if folio:     
                    reports = reports.filter(models.Report.folio == folio)
               
                reports = reports.filter(models.Report.user_id == int(user_id))
                count = reports.count()
                PAGE_SIZE = 50
                if forward:
                    reports, next_cursor, more = reports.order(-models.Report.created, models.Report.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
                    if next_cursor and more:
                        self.view.next_cursor = next_cursor
                    if c:
                        self.view.prev_cursor = cursor.reversed()
                else:
                    reports, next_cursor, more = reports.order(models.Report.created, models.Report.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
                    reports = list(reversed(reports))
                    if next_cursor and more:
                        self.view.prev_cursor = next_cursor
                    self.view.next_cursor = cursor.reversed()

            def pager_url(p, cursor):
                params = OrderedDict()
                if q:
                    params['q'] = q
                if status:
                    params['status'] = status
                if ticket:
                    params['ticket'] = ticket
                if folio:
                    params['folio'] = folio
                if groupCat:
                    params['cat'] = groupCat
                if p in ['prev']:
                    params['p'] = p
                if cursor:
                    params['c'] = cursor.urlsafe()
                return self.uri_for('materialize-organization-user-reports', user_id = user_id, **params)
                

            self.view.pager_url = pager_url
            self.view.q = q

            params['statusval'] = get_status(status) if status else ""
            params['ticketval'] = ticket if ticket else ""
            params['folioval'] = folio if folio else ""
            params['catGroup'] = groupCat if groupCat else ""
            params['reports'] = reports
            params['count'] = count
            params['cats'] = sorted(names) if names else names
            if self.user_is_callcenter:
                params['level'] = 'materialize-callcenter-report'
            elif self.user_is_secretary:
                params['level'] = 'materialize-secretary-report'
            elif self.user_is_agent:
                params['level'] = 'materialize-agent-report'
            elif self.user_is_operator: 
                params['level'] = 'materialize-operator-report'
            params['inbox'] = 'materialize-organization-user-reports'
            params['rep_user_id'] = user_id
            return self.render_template('materialize/users/operators/inbox.html', **params)
        
        self.abort(403)

class MaterializeOrganizationInboxRequestHandler(BaseHandler):
    @user_required
    def get(self):
        if self.has_reports:
            s = self.request.path.startswith('/user/secretary/inbox')
            a = self.request.path.startswith('/user/agent/inbox')
            o = self.request.path.startswith('/user/operator/inbox')
            cc = self.request.path.startswith('/user/callcenter/inbox')
            params={}
            names=[]
            user_info = self.user_model.get_by_id(long(self.user_id))            
            
            if cc and self.user_is_callcenter:
                page='callcenter'
                
                group_categories = models.GroupCategory.query()
                if group_categories.count() > 0:
                    if group_categories.count() > 1:
                        names.append('TODOS')
                    for group in group_categories:
                        if group is not None and group.get_agencies().count() > 0:
                            names.append(group.name)
                else:
                    names.append('---')

            else:
                if s and self.user_is_secretary:
                    page = 'secretary'
                    secretary = models.Secretary.get_admin_by_email(user_info.email)
                    agencies = models.Agency.query(models.Agency.secretary_id == secretary.key.id())            
                elif a and self.user_is_agent:
                    page = 'agent'
                    agencies = models.Agency.get_admin_by_email(user_info.email)            
                elif o and self.user_is_operator:
                    page = 'operator'
                    operators = models.Operator.get_by_email(user_info.email)
                    agencies = ndb.get_multi([ndb.Key(models.Agency, operator.agency_id) for operator in operators])             
                else: 
                    self.abort(403)
                
                group_categories_ids = []            
                for agency in agencies:
                    if agency is not None:
                        if agency.group_category_id is not None:
                            group_categories_ids.append(agency.group_category_id)
                group_categories_ids = list(set(group_categories_ids))
                
                if len(group_categories_ids)>0:
                    if len(group_categories_ids)>1:
                        names.append('TODOS')
                    group_categories = ndb.get_multi([ndb.Key(models.GroupCategory, groupID) for groupID in group_categories_ids])
                    for group in group_categories:
                        if group is not None:
                            names.append(group.name)            
                else:
                    names.append('---')
            
            status = self.request.get('status') if (self.request.get('status') or self.request.get('status') != "") else False
            ticket = self.request.get('ticket') if (self.request.get('ticket') or self.request.get('ticket') != "") else False
            folio = self.request.get('folio') if (self.request.get('folio') or self.request.get('folio') != "") else False
            groupCat = self.request.get('cat') if (self.request.get('cat') or self.request.get('cat') != "") else False

            if ticket:
                if ticket.isdigit():
                   ticket = int(ticket)
                else:
                   self.add_message('Tu ticket debe contener solamente numeros', 'warning')
                   return self.get()
                        
            p = self.request.get('p')
            q = self.request.get('q')
            c = self.request.get('c')
            forward = True if p not in ['prev'] else False
            cursor = Cursor(urlsafe=c)

            if q:
                reports = models.Report.query()         

                if len(q.split(',')) > 3:
                    if 'u_name' in q and 'u_lastname' in q and 'u_phone' in q:
                        reports = reports.filter(ndb.AND(models.Report.contact_name.IN([q.split(',')[1].strip(),q.split(',')[1].strip().lower(),q.split(',')[1].strip().upper(),q.split(',')[1].strip().title()]), models.Report.contact_lastname.IN([q.split(',')[3].strip(),q.split(',')[3].strip().lower(),q.split(',')[3].strip().upper(), q.split(',')[3].strip().title()]), models.Report.contact_phone.IN([q.split(',')[5]])))
                    if 'u_name' in q and 'u_lastname' in q and 'u_phone' not in q:
                        reports = reports.filter(ndb.AND(models.Report.contact_name.IN([q.split(',')[1].strip(),q.split(',')[1].strip().lower(),q.split(',')[1].strip().upper(),q.split(',')[1].strip().title()]), models.Report.contact_lastname.IN([q.split(',')[3].strip(),q.split(',')[3].strip().lower(),q.split(',')[3].strip().upper(), q.split(',')[3].strip().title()]) ))
                    if 'u_name' in q and 'u_lastname' not in q and 'u_phone' in q:
                        reports = reports.filter(ndb.AND(models.Report.contact_name.IN([q.split(',')[1].strip(),q.split(',')[1].strip().lower(),q.split(',')[1].strip().upper(),q.split(',')[1].strip().title()]), models.Report.contact_phone.IN([q.split(',')[3]])))
                    if 'u_name' not in q and 'u_lastname' in q and 'u_phone' in q:
                        reports = reports.filter(ndb.AND(models.Report.contact_lastname.IN([q.split(',')[1].strip(),q.split(',')[1].strip().lower(),q.split(',')[1].strip().upper(), q.split(',')[1].strip().title()]), models.Report.contact_phone.IN([q.split(',')[3]])))
                else:
                    if 'u_name' in q:
                        reports = reports.filter(models.Report.contact_name.IN([q.split(',')[1].strip(),q.split(',')[1].strip().lower(),q.split(',')[1].strip().upper(),q.split(',')[1].strip().title()]))
                    elif 'u_last_name' in q:
                        reports = reports.filter(models.Report.contact_lastname.IN([q.split(',')[1].strip(),q.split(',')[1].strip().lower(),q.split(',')[1].strip().upper(),q.split(',')[0].strip().title()]))
                    elif 'u_phone' in q:
                        reports = reports.filter(models.Report.contact_phone.IN([q.split(',')[1]]))

                count = reports.count()
                PAGE_SIZE = 30
                if forward:
                    reports, next_cursor, more = reports.order(-models.Report.created, models.Report.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
                    if next_cursor and more:
                        self.view.next_cursor = next_cursor
                    if c:
                        self.view.prev_cursor = cursor.reversed()
                else:
                    reports, next_cursor, more = reports.order(models.Report.created, models.Report.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
                    reports = list(reversed(reports))
                    if next_cursor and more:
                        self.view.prev_cursor = next_cursor
                    self.view.next_cursor = cursor.reversed()
            else:
                if groupCat:
                    if groupCat == 'TODOS':
                        reports = models.Report.query(models.Report.group_category.IN(names[1:]))
                    else:
                        reports = models.Report.query(models.Report.group_category == groupCat)
                    params['ddfill'] = groupCat
                else:
                    if names[0]=='---':
                        reports = models.Report.query(models.Report.group_category == 'inexistent')
                    else:
                        if cc:
                            reports = models.Report.query()
                        else:
                            if names[0]== 'TODOS':
                                reports = models.Report.query(models.Report.group_category.IN(names[1:]))
                            else:
                                reports = models.Report.query(models.Report.group_category == names[0])
                    params['ddfill'] = names[0]
                if status:
                    reports = reports.filter(models.Report.status == status) if status != 'pending' else reports.filter(models.Report.status.IN(['assigned', 'halted', 'answered', 'working']))
                    params['ddfillstat'] = get_status(status)
                else:
                    if cc:
                        params['ddfillstat'] = 'TODOS'
                    else:
                        reports = reports.filter(models.Report.status.IN(['assigned', 'halted', 'answered', 'working']))
                        params['ddfillstat'] = get_status('pending')
                if ticket:    
                    reports = reports.filter(models.Report.cdb_id == ticket)
                if folio:     
                    reports = reports.filter(models.Report.folio == folio)
                count = reports.count()
                PAGE_SIZE = 30
                if forward:
                    reports, next_cursor, more = reports.order(-models.Report.created, models.Report.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
                    if next_cursor and more:
                        self.view.next_cursor = next_cursor
                    if c:
                        self.view.prev_cursor = cursor.reversed()
                else:
                    reports, next_cursor, more = reports.order(models.Report.created, models.Report.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
                    reports = list(reversed(reports))
                    if next_cursor and more:
                        self.view.prev_cursor = next_cursor
                    self.view.next_cursor = cursor.reversed()

            def pager_url(p, cursor):
                params = OrderedDict()
                if q:
                    params['q'] = q
                if status:
                    params['status'] = status
                if ticket:
                    params['ticket'] = ticket
                if folio:
                    params['folio'] = folio
                if groupCat:
                    params['cat'] = groupCat
                if p in ['prev']:
                    params['p'] = p
                if cursor:
                    params['c'] = cursor.urlsafe()
                return self.uri_for('materialize-'+page+'-inbox', **params)

            self.view.pager_url = pager_url
            self.view.q = q

            params['statusval'] = get_status(status) if status else ""
            params['ticketval'] = ticket if ticket else ""
            params['folioval'] = folio if folio else ""
            params['catGroup'] = groupCat if groupCat else ""
            params['reports'] = reports
            params['count'] = count
            params['level'] = 'materialize-'+page+'-report'
            params['inbox'] = 'materialize-'+page+'-inbox'
            params['cats'] = sorted(names) if names else names
            return self.render_template('materialize/users/operators/inbox.html', **params)
        
        self.abort(403)

#REPORTS EDIT
class MaterializeSecretaryReportRequestHandler(BaseHandler):
    @user_required
    def edit(self, report_id):
        if not self.has_reports:
            self.abort(403)

        if self.request.POST:
            report_info = get_or_404(self, report_id)
            delete = self.request.get('delete')
            status = self.request.get('status')
            user_info = self.user_model.get_by_id(long(self.user_id))
            
            try:
                if delete == 'confirmed_deletion':
                    archiveReport(self, user_info, report_info.key.id(), "materialize-secretary-report")                    

                elif delete == 'report_edition':
                    editReport(self, user_info, report_info.key.id(), "materialize-secretary-report") 

                elif delete == 'attachment':
                    att = models.Attachment()
                    att.file_name = self.request.get('att_name')
                    att.user_id = int(self.request.get('att_user_id'))
                    att.report_id = int(self.request.get('att_report_id'))
                    att.put()
                    
                    if hasattr(self.request.POST['att_file'], 'filename'):
                        #create attachment
                        from google.appengine.api import urlfetch
                        from poster.encode import multipart_encode, MultipartParam
                        
                        urlfetch.set_default_fetch_deadline(45)

                        payload = {}
                        upload_url = blobstore.create_upload_url('/report/attachment/upload/%s' % (att.key.id()))
                        file_data = self.request.POST['att_file']
                        payload['file'] = MultipartParam('file', filename=file_data.filename,
                                                                 filetype=file_data.type,
                                                                 fileobj=file_data.file)
                        data,headers= multipart_encode(payload)
                        t = urlfetch.fetch(url=upload_url, payload="".join(data), method=urlfetch.POST, headers=headers)
                        
                        logging.info('t.content: %s' % t.content)
                        
                        if t.content == 'success':
                            message = _(messages.saving_success)
                            self.add_message(message, 'success')            
                            
                        else:
                            message = _(messages.attach_error)
                            self.add_message(message, 'danger')            
                            
                        report_info = get_or_404(self, report_id)                   

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating report: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("materialize-secretary-report", report_id=report_id)
        else:
            report_info = get_or_404(self, report_id)

        params = editReportParams(self, report_info)

        return self.render_template('materialize/users/operators/report_edit.html', **params)
        
class MaterializeAgentReportRequestHandler(BaseHandler):
    @user_required
    def edit(self, report_id):
        if not self.has_reports:
            self.abort(403)
        if self.request.POST:
            report_info = get_or_404(self, report_id)
            delete = self.request.get('delete')
            status = self.request.get('status')
            user_info = self.user_model.get_by_id(long(self.user_id))
            try:
                if delete == 'confirmed_deletion':
                    archiveReport(self, user_info, report_info.key.id(), "materialize-agent-report")

                elif delete == 'report_edition':
                    editReport(self, user_info, report_info.key.id(), "materialize-agent-report") 

                elif delete == 'attachment':
                    att = models.Attachment()
                    att.file_name = self.request.get('att_name')
                    att.user_id = int(self.request.get('att_user_id'))
                    att.report_id = int(self.request.get('att_report_id'))
                    att.put()
                    
                    if hasattr(self.request.POST['att_file'], 'filename'):
                        #create attachment
                        from google.appengine.api import urlfetch
                        from poster.encode import multipart_encode, MultipartParam
                        
                        urlfetch.set_default_fetch_deadline(45)

                        payload = {}
                        upload_url = blobstore.create_upload_url('/report/attachment/upload/%s' % (att.key.id()))
                        file_data = self.request.POST['att_file']
                        payload['file'] = MultipartParam('file', filename=file_data.filename,
                                                                 filetype=file_data.type,
                                                                 fileobj=file_data.file)
                        data,headers= multipart_encode(payload)
                        t = urlfetch.fetch(url=upload_url, payload="".join(data), method=urlfetch.POST, headers=headers)
                        
                        logging.info('t.content: %s' % t.content)
                        
                        if t.content == 'success':
                            message = _(messages.saving_success)
                            self.add_message(message, 'success')            
                            
                        else:
                            message = _(messages.attach_error)
                            self.add_message(message, 'danger')            
                            
                        report_info = get_or_404(self, report_id)                   

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating report: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("materialize-agent-report", report_id=report_id)
        else:
            report_info = get_or_404(self, report_id)

        params = editReportParams(self, report_info)

        return self.render_template('materialize/users/operators/report_edit.html', **params)
        
class MaterializeOperatorReportRequestHandler(BaseHandler):
    @user_required
    def edit(self, report_id):
        if not self.has_reports:
            self.abort(403)

        if self.request.POST:
            report_info = get_or_404(self, report_id)
            delete = self.request.get('delete')
            status = self.request.get('status')
            user_info = self.user_model.get_by_id(long(self.user_id))
            try:
                if delete == 'confirmed_deletion':
                    archiveReport(self, user_info, report_info.key.id(), "materialize-operator-report")

                elif delete == 'report_edition':
                    editReport(self, user_info, report_info.key.id(), "materialize-operator-report")

                elif delete == 'attachment':
                    att = models.Attachment()
                    att.file_name = self.request.get('att_name')
                    att.user_id = int(self.request.get('att_user_id'))
                    att.report_id = int(self.request.get('att_report_id'))
                    att.put()
                    
                    if hasattr(self.request.POST['att_file'], 'filename'):
                        #create attachment
                        from google.appengine.api import urlfetch
                        from poster.encode import multipart_encode, MultipartParam
                        
                        urlfetch.set_default_fetch_deadline(45)

                        payload = {}
                        upload_url = blobstore.create_upload_url('/report/attachment/upload/%s' % (att.key.id()))
                        file_data = self.request.POST['att_file']
                        payload['file'] = MultipartParam('file', filename=file_data.filename,
                                                                 filetype=file_data.type,
                                                                 fileobj=file_data.file)
                        data,headers= multipart_encode(payload)
                        t = urlfetch.fetch(url=upload_url, payload="".join(data), method=urlfetch.POST, headers=headers)
                        
                        logging.info('t.content: %s' % t.content)
                        
                        if t.content == 'success':
                            message = _(messages.saving_success)
                            self.add_message(message, 'success')            
                            
                        else:
                            message = _(messages.attach_error)
                            self.add_message(message, 'danger')            
                            
                        report_info = get_or_404(self, report_id)                    
                                
            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating report: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("materialize-operator-report", report_id=report_id)
        else:
            report_info = get_or_404(self, report_id)

        params = editReportParams(self, report_info)

        return self.render_template('materialize/users/operators/report_edit.html', **params)
        
class MaterializeCallCenterReportRequestHandler(BaseHandler):
    @user_required
    def edit(self, report_id):
        if not self.has_reports:
            self.abort(403)

        if self.request.POST:
            report_info = get_or_404(self, report_id)
            delete = self.request.get('delete')
            status = self.request.get('status')
            user_info = self.user_model.get_by_id(long(self.user_id))
            try:
                if delete == 'confirmed_deletion':
                    archiveReport(self, user_info, report_info.key.id(), "materialize-callcenter-report")

                elif delete == 'report_edition':
                    editReport(self, user_info, report_info.key.id(), "materialize-callcenter-report")      
                
                elif delete == 'attachment':
                    att = models.Attachment()
                    att.file_name = self.request.get('att_name')
                    att.user_id = int(self.request.get('att_user_id'))
                    att.report_id = int(self.request.get('att_report_id'))
                    att.put()
                    
                    if hasattr(self.request.POST['att_file'], 'filename'):
                        #create attachment
                        from google.appengine.api import urlfetch
                        from poster.encode import multipart_encode, MultipartParam
                        
                        urlfetch.set_default_fetch_deadline(45)

                        payload = {}
                        upload_url = blobstore.create_upload_url('/report/attachment/upload/%s' % (att.key.id()))
                        file_data = self.request.POST['att_file']
                        payload['file'] = MultipartParam('file', filename=file_data.filename,
                                                                 filetype=file_data.type,
                                                                 fileobj=file_data.file)
                        data,headers= multipart_encode(payload)
                        t = urlfetch.fetch(url=upload_url, payload="".join(data), method=urlfetch.POST, headers=headers)
                        
                        logging.info('t.content: %s' % t.content)
                        
                        if t.content == 'success':
                            message = _(messages.saving_success)
                            self.add_message(message, 'success')            
                            
                        else:
                            message = _(messages.attach_error)
                            self.add_message(message, 'danger')            
                            
                        report_info = get_or_404(self, report_id)


            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating report: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("materialize-callcenter-report", report_id=report_id)
        else:
            report_info = get_or_404(self, report_id)

        params = editReportParams(self, report_info)

        return self.render_template('materialize/users/operators/report_edit.html', **params)
        
#SOCIAL NETWORKS
class MaterializeCallCenterFacebookRequestHandler(BaseHandler):
    @user_required
    def get(self):
        if self.has_social_media and self.user_is_callcenter and self.user_callcenter_role in ['admin', 'callcenter', 'socialnetworks']:
            params = {}
            params['indicoio_apikey'] = self.app.config.get('indicoio_apikey')
            params['facebook_appID'] = self.app.config.get('facebook_appID')
            params['facebook_handle'] = self.app.config.get('facebook_handle')
            return self.render_template('materialize/users/operators/facebook.html', **params)
        self.abort(403)

class MaterializeCallCenterTwitterRequestHandler(BaseHandler):
    @user_required
    def get(self):
        if self.has_social_media and self.user_is_callcenter and self.user_callcenter_role in ['admin', 'callcenter', 'socialnetworks']:
            params = {}
            params['twitter_appID'] = self.app.config.get('twitter_appID')
            params['twitter_handle'] = self.app.config.get('twitter_handle')
            return self.render_template('materialize/users/operators/twitter.html', **params)
        self.abort(403)

#INITIATIVES
def inverse_initiative_status(_stat):
    if _stat == 'Iniciado':
        return 'open'        
    if _stat == 'En progreso':
        return 'measuring'
    if _stat == 'Retrasado':
        return 'delayed'
    if _stat == 'A punto de cumplir':
        return 'near'
    if _stat == 'Cumplido':
        return 'completed'

class MaterializeInitiativesHandler(BaseHandler):
    @user_required
    def get(self):
        if not self.user_is_callcenter or self.user_callcenter_role not in ['admin', 'transparency']:
            self.abort(403)
        params = {}
        params['initiatives'] = models.Initiative.query()
        params['group_color'] = self.app.config.get('brand_secondary_color')
        return self.render_template('materialize/users/operators/callcenter_initiatives.html', **params)        
    
    def post(self):
        try:
            name = self.request.get('name').strip()
            icon_url = self.request.get('subicon')
            description = self.request.get('description')
            lead = self.request.get('lead')
            relevance = self.request.get('relevance')
            area_name = self.request.get('agegroupcat')

            initiative = models.Initiative.query(models.Initiative.name == name).get()
            if initiative is not None:
                self.add_message(messages.nametaken, 'danger')
            else:
                area = models.Area.query(models.Area.name == area_name).get()
                if area is None:
                    logging.info("area is none")
                    self.add_message(messages.saving_error, 'danger')
                    return self.get()  

                initiative = models.Initiative()
                initiative.name = name
                initiative.color = area.color
                initiative.icon_url = icon_url
                initiative.lead = lead
                initiative.description = description
                initiative.relevance = relevance
                initiative.area_id = area.key.id()
                initiative.put()

                self.add_message(messages.saving_success, 'success')
        except Exception as e:
            self.add_message(messages.saving_error, 'danger')
            logging.info("error in post: %s" % e)
        
        return self.get()  

class MaterializeInitiativeEditHandler(BaseHandler):
    def get_or_404(self, init_id):
        try:
            initiative = models.Initiative.get_by_id(long(init_id))
            if initiative:
                return initiative
        except ValueError:
            pass
        self.abort(404)

    @user_required
    def edit(self, init_id):
        if not self.user_is_callcenter or self.user_callcenter_role not in ['admin', 'transparency']:
            self.abort(403)

        if self.request.POST:
            initiative = self.get_or_404(init_id)
            delete = self.request.get('delete')
            
            try:

                if delete == 'confirmed_deletion':
                    #DELETE INITIATIVE 
                    initiative.key.delete()

                    self.add_message(messages.saving_success, 'success')
                elif delete == 'category_edition':
                    #INITIATIVE EDITION
                    name = self.request.get('name').strip()
                    icon_url = self.request.get('subicon')
                    description = self.request.get('description')
                    lead = self.request.get('lead')
                    relevance = self.request.get('relevance')
                    area_name = self.request.get('agegroupcat')
                    value = self.request.get('metric')
                    status = inverse_initiative_status(self.request.get('status'))

                    _initiative = models.Initiative.query(models.Initiative.name == name).get()
                    if _initiative is not None and int(_initiative.key.id()) != int(init_id):
                        self.add_message(messages.nametaken, 'danger')
                    else:
                        area = models.Area.query(models.Area.name == area_name).get()
                        if area is None:
                            self.add_message(messages.saving_error, 'danger')
                            return self.redirect_to("materialize-callcenter-initiative-edit", init_id=init_id) 
                        initiative.name = name
                        initiative.color = area.color
                        initiative.icon_url = icon_url
                        initiative.lead = lead
                        initiative.description = description
                        initiative.relevance = relevance
                        initiative.value = value
                        initiative.status = status
                        initiative.area_id = area.key.id()
                        initiative.put()

                        if hasattr(self.request.POST['file'], 'filename'):
                            #create attachment
                            from google.appengine.api import urlfetch
                            from poster.encode import multipart_encode, MultipartParam
                            
                            urlfetch.set_default_fetch_deadline(45)

                            payload = {}
                            upload_url = blobstore.create_upload_url('/user/callcenter/initiatives/image/upload/%s/' %(initiative.key.id()))
                            file_data = self.request.POST['file']
                            payload['file'] = MultipartParam('file', filename=file_data.filename,
                                                                     filetype=file_data.type,
                                                                     fileobj=file_data.file)
                            data,headers= multipart_encode(payload)
                            t = urlfetch.fetch(url=upload_url, payload="".join(data), method=urlfetch.POST, headers=headers)
                            
                            logging.info('t.content: %s' % t.content)
                            
                            if t.content == 'success':
                                message = _(messages.saving_success)
                                self.add_message(message, 'success')
                                return self.redirect_to("materialize-callcenter-initiative-edit", init_id=init_id)
                                
                            else:
                                message = _(messages.attach_error)
                                self.add_message(message, 'danger')            
                                return self.redirect_to("materialize-callcenter-initiative-edit", init_id=init_id)
                                                  
                        else:
                            message = _(messages.saving_success)
                            self.add_message(message, 'success')
                            return self.redirect_to("materialize-callcenter-initiative-edit", init_id=init_id)
                            


                        self.add_message(messages.saving_success, 'success')

                return self.redirect_to("materialize-callcenter-initiatives")
                
            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating initiative: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("materialize-callcenter-initiative-edit", init_id=init_id)
        else:
            initiative = self.get_or_404(init_id)

        params = {
            'initiative': initiative
        }

        return self.render_template('materialize/users/operators/callcenter_initiative_edit.html', **params)

class MaterializeInitiativeImageUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self, initiative_id):
        try:
            logging.info(self.get_uploads()[0])
            logging.info('attaching file to initiative_id: %s' %initiative_id)
            upload = self.get_uploads()[0]
            initiative = models.Initiative.get_by_id(long(initiative_id))
            # initiative.attachment = upload.key()
            initiative.image_url = self.uri_for('blob-serve', photo_key = upload.key(), _full=True)
            initiative.put()
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('success')
        except Exception as e:
            logging.error('something went wrong: %s' % e)
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('error')

# GEO TRANSPARENCY
class MaterializeGeomHandler(BaseHandler):
    @user_required
    def get(self):
        if not self.user_is_callcenter or self.user_callcenter_role not in ['admin', 'transparency']:
            self.abort(403)
        params = {}
        params['cartodb_pois_table'] = self.app.config.get('cartodb_pois_table')
        params['group_color'] = self.app.config.get('brand_secondary_color')
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')

        return self.render_template('materialize/users/operators/callcenter_geom.html', **params)
    
    def post(self):
        name = self.request.get('name').strip()
        sector = self.request.get('catGroup')
        category = self.request.get('subCat')
        kind = self.request.get('kind')
        locality = self.request.get('locality')
        leader = self.request.get('lead')
        agency = self.request.get('agency')
        fund_source = self.request.get('source')
        amount = self.request.get('amount')
        description = self.request.get('description')
        identifier = self.request.get('identifier')
        exec_date = self.request.get('exec_date')
        address_from = self.request.get('address_from')
        address_from_coord = self.request.get('address_from_coord').split(',')
        image_url = self.request.get('poi_image')

        from google.appengine.api import urlfetch
        import urllib
        api_key = self.app.config.get('cartodb_apikey')
        cartodb_domain = self.app.config.get('cartodb_user')
        cartodb_table = self.app.config.get('cartodb_pois_table')
        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=INSERT INTO %s (the_geom,name,sector,category,kind,locality,leader,agency,fund_source,amount,description,identifier,exec_date,address_from,image_url) VALUES (ST_GeomFromText('POINT(%s %s)', 4326),'%s','%s','%s','%s','%s','%s','%s','%s',%s,'%s','%s','%s','%s','%s')&api_key=%s" % (cartodb_domain, cartodb_table, address_from_coord[1], address_from_coord[0],name,sector,category,kind,locality,leader,agency,fund_source,amount,description,identifier,exec_date,address_from,image_url, api_key)).encode('utf8')
        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
        try:
            t = urlfetch.fetch(url)
            logging.info("t: %s" % t.content)
            message = _(messages.saving_success)
            self.add_message(message, 'success')
        except Exception as e:
            logging.info('error in cartodb INSERT request: %s' % e)
            message = _(messages.saving_error)
            self.add_message(message, 'danger')
            pass

        return self.get()  

class MaterializeGeomEditHandler(BaseHandler):
    @user_required
    def get(self):
        if not self.user_is_callcenter or self.user_callcenter_role not in ['admin', 'transparency']:
            self.abort(403)
        params = {}
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_pois_table'] = self.app.config.get('cartodb_pois_table')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        return self.render_template('materialize/users/operators/callcenter_geom_edit.html', **params)
    
    def post(self):
        name = self.request.get('name').strip()
        sector = self.request.get('catGroup')
        category = self.request.get('subCat')
        kind = self.request.get('kind')
        locality = self.request.get('locality')
        leader = self.request.get('lead')
        agency = self.request.get('agency')
        fund_source = self.request.get('source')
        amount = self.request.get('amount')
        description = self.request.get('description')
        identifier = self.request.get('identifier')
        exec_date = self.request.get('exec_date')
        address_from = self.request.get('address_from')
        address_from_coord = self.request.get('address_from_coord').split(',')
        image_url = self.request.get('poi_image')
        delete = self.request.get('delete')
        cartodb_id = self.request.get('cartodb_id')

        from google.appengine.api import urlfetch
        import urllib
        api_key = self.app.config.get('cartodb_apikey')
        cartodb_domain = self.app.config.get('cartodb_user')
        cartodb_table = self.app.config.get('cartodb_pois_table')
        if delete == "no":
            unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET (the_geom,name,sector,category,kind,locality,leader,agency,fund_source,amount,description,identifier,exec_date,address_from,image_url) = (ST_GeomFromText('POINT(%s %s)', 4326),'%s','%s','%s','%s','%s','%s','%s','%s',%s,'%s','%s','%s','%s','%s') WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, address_from_coord[1], address_from_coord[0],name,sector,category,kind,locality,leader,agency,fund_source,amount,description,identifier,exec_date,address_from,image_url, cartodb_id, api_key)).encode('utf8')
        if delete == "yes":
            unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=DELETE FROM %s WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, cartodb_id, api_key)).encode('utf8')
        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
        try:
            logging.info('carto request: %s' % unquoted_url)
            t = urlfetch.fetch(url)
            logging.info("t: %s" % t.content)
            message = _(messages.saving_success)
            self.add_message(message, 'success')
        except Exception as e:
            logging.info('error in cartodb UPDATE request: %s' % e)
            message = _(messages.saving_error)
            self.add_message(message, 'danger')
            pass

        return self.get() 


# ------------------------------------------------------------------------------------------- #
"""                                     CORE REPORT HANDLERS                                """
# ------------------------------------------------------------------------------------------- #

class MaterializeReportsRequestHandler(BaseHandler):
    """
        Handler for materialized reports
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        if not self.has_reports:
            self.abort(403)

        params, user_info = disclaim(self)

        user_reports = models.Report.query(models.Report.user_id == int(user_info.key.id()))
        user_reports = user_reports.order(-models.Report.created)
        user_reports = user_reports.fetch(50)
        if user_reports is not None:
            try:
                params['reports'] = []
                for report in user_reports:
                    if report.status != 'archived' and report.status != 'spam':
                        params['reports'].append((report.key.id(), report.title, report.when, report.address_from_coord, report.address_from, report.description, report.get_status(), report.image_url, report.group_category, report.sub_category, report.cdb_id, report.req_deletion, report.get_group_color(), report.rating, report.follows, report.get_log_count(), 'own'))
                try:
                    follows = models.Followers.query(models.Followers.user_id == int(user_info.key.id()))
                    for follow in follows:
                        report = models.Report.get_by_cdb(int(follow.report_id))
                        if report:
                            params['reports'].append((report.key.id(), report.title, report.when, report.address_from_coord, report.address_from, report.description, report.get_status(), report.image_url, report.group_category, report.sub_category, report.cdb_id, report.req_deletion, report.get_group_color(), report.rating, report.follows, report.get_log_count(), 'follow'))
                except:
                    pass
            except (AttributeError, TypeError), e:
                login_error_message = _(messages.expired_session)
                logging.error('Error updating profile: %s' % e)
                self.add_message(login_error_message, 'danger')
                self.redirect_to('login')
        
        return self.render_template('materialize/users/sections/reports_user.html', **params)
        

    @user_required
    def post(self):
        delete = self.request.get('delete')
        report_id = self.request.get('report_id')
        
        try:
            report_info = models.Report.get_by_id(long(report_id))
            if delete == 'confirmed_deletion':
                if report_info:
                    report_info.req_deletion = True
            if delete == 'confirmed_cancelation':
                if report_info:
                    report_info.req_deletion = False
            if delete == 'confirmed_comment':
                user_info = self.user_model.get_by_id(long(self.user_id))
                if report_info:
                    report_info.status = 'answered' if report_info.status in ('open', 'halted', 'forgot') else report_info.status
                    log_info = models.LogChange()
                    log_info.user_email = user_info.email.lower()
                    log_info.report_id = int(report_id)
                    log_info.kind =  'comment'
                    log_info.title = "Ha hecho un comentario en su reporte."
                    log_info.contents = self.request.get('comment')
                    log_info.put()
                    
                    #PUSH TO CARTODB
                    if report_info.cdb_id !=-1:
                        cartoUpdate(self, report_info.key.id(), False)
                        
            report_info.put()
            self.add_message(messages.inquiry_success, 'success')
            return self.get()

        except (AttributeError, KeyError, ValueError), e:
            logging.error('Error updating report: %s ' % e)
            self.add_message(messages.saving_error, 'danger')
            return self.get()

class MaterializeReportsEditRequestHandler(BaseHandler):
    """
    Handler for materialized home
    """  
    @user_required
    def get(self, report_id):
        """ Returns a simple HTML form for materialize home """

        if not self.has_reports:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####
        
        user_report = models.Report.get_by_id(long(report_id))
        
        if user_report == None:
            self.abort(404)

        if user_report.user_id != int(self.user_id):
            self.abort(403)

        params['report'] = user_report
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')

        if params['report']:
            if params['report'].user_id == int(self.user_id):
                return self.render_template('materialize/users/sections/report_edit.html', **params)
            else:
                self.abort(403)
        else:
            self.abort(404)

    @user_required
    def post(self, report_id):
        """ Get fields from POST dict """

        if not self.has_reports:
            self.abort(403)

        user_report = models.Report.get_by_id(long(report_id))
        user_info = self.user_model.get_by_id(long(self.user_id))   

        if user_report == None or user_info == None:
            self.abort(404)

        if user_report.user_id != int(self.user_id):
            self.abort(403)

        address_from = self.request.get('address_from')
        address_from_coord = self.request.get('address_from_coord')
        catGroup = self.request.get('catGroup')
        subCat = self.request.get('subCat')
        description = self.request.get('description')
        when = self.request.get('when')
        
        try:
            user_report.user_id = int(self.user_id) if int(self.user_id) is not None else -1
            user_report.address_from_coord = ndb.GeoPt(address_from_coord)
            user_report.address_from = address_from
            user_report.when = date(int(when[:4]), int(when[5:7]), int(when[8:]))
            user_report.title = u'%s #%s' % (self.app.config.get('app_name'),subCat)
            user_report.description = description
            user_report.group_category = catGroup
            user_report.sub_category  = subCat
            user_report.contact_info = u'%s, %s, %s, %s, %s' % (user_info.name, user_info.last_name, user_info.address.address_from, user_info.phone, user_info.email)
            if user_info.credibility <= 0:
                user_report.status = 'spam'
            else:
                user_report.status = 'answered' if user_report.status in ('open', 'halted', 'forgot', 'solved', 'failed') else user_report.status
            
            user_report.put()
            

            if hasattr(self.request.POST['file'], 'filename'):
                #create attachment
                from google.appengine.api import urlfetch
                from poster.encode import multipart_encode, MultipartParam
                
                urlfetch.set_default_fetch_deadline(45)

                payload = {}
                upload_url = blobstore.create_upload_url('/report/image/upload/%s' %(user_report.key.id()))
                file_data = self.request.POST['file']
                payload['file'] = MultipartParam('file', filename=file_data.filename,
                                                         filetype=file_data.type,
                                                         fileobj=file_data.file)
                data,headers= multipart_encode(payload)
                t = urlfetch.fetch(url=upload_url, payload="".join(data), method=urlfetch.POST, headers=headers)
                
                logging.info('t.content: %s' % t.content)
                
                if t.content == 'success':
                    cartoUpdate(self, user_report.key.id(), False)
                    return self.redirect_to('materialize-reports')                    
                else:
                    message = _(messages.attach_error)
                    self.add_message(message, 'danger')            
                    return self.get(report_id=report_id)                    
            else:
                cartoUpdate(self, user_report.key.id(), False)
                message = _(messages.saving_success)
                self.add_message(message, 'success')
                return self.redirect_to('materialize-reports')


        except Exception as e:
            logging.info('error in post: %s' % e)
            message = _(messages.saving_error)
            self.add_message(message, 'danger')
            return self.get(report_id=report_id)         
        
class MaterializeReportCardlistHandler(BaseHandler):
    """
        Handler for materialized reports cardlists
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        if not self.has_reports:
            self.abort(403)

        params, user_info = disclaim(self)
        
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        
        return self.render_template('materialize/users/sections/reports_list.html', **params)
        
class MaterializeNewReportHandler(BaseHandler):
    """
    Handler for materialized home
    """  
    @user_required
    def get(self):
        """ Returns a simple HTML form for materialize home """
        if not self.has_reports:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####
        
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')

        return self.render_template('materialize/users/sections/report_new.html', **params)
        

    @user_required
    def post(self):
        """ Get fields from POST dict """
        
        if not self.has_reports:
            self.abort(403)

        address_from = self.request.get('address_from')
        address_from_coord = self.request.get('address_from_coord')
        catGroup = self.request.get('catGroup')
        subCat = self.request.get('subCat')
        description = self.request.get('description')
        when = self.request.get('when')
        
        try:
            user_info = self.user_model.get_by_id(long(self.user_id))   

            user_report = models.Report()
            user_report.user_id = int(self.user_id) if int(self.user_id) is not None else -1
            user_report.address_from_coord = ndb.GeoPt(address_from_coord)
            user_report.address_from = address_from
            user_report.when = date(int(when[:4]), int(when[5:7]), int(when[8:]))
            user_report.title = u'%s #%s' % (self.app.config.get('app_name'),subCat)
            user_report.description = description
            user_report.group_category = catGroup
            user_report.sub_category  = subCat
            user_report.contact_info = u'%s, %s, %s, %s, %s' % (user_info.name, user_info.last_name, user_info.address.address_from, user_info.phone, user_info.email)
            if user_info.credibility <= 0:
                user_report.status = 'spam'
            
            user_report.put()
            

            if hasattr(self.request.POST['file'], 'filename'):
                #create attachment
                from google.appengine.api import urlfetch
                from poster.encode import multipart_encode, MultipartParam
                
                urlfetch.set_default_fetch_deadline(45)

                payload = {}
                upload_url = blobstore.create_upload_url('/report/image/upload/%s' %(user_report.key.id()))
                file_data = self.request.POST['file']
                payload['file'] = MultipartParam('file', filename=file_data.filename,
                                                         filetype=file_data.type,
                                                         fileobj=file_data.file)
                data,headers= multipart_encode(payload)
                t = urlfetch.fetch(url=upload_url, payload="".join(data), method=urlfetch.POST, headers=headers)
                
                logging.info('t.content: %s' % t.content)
                
                if t.content == 'success':
                    message = _(messages.report_success)
                    self.add_message(message, 'success')
                    return self.redirect_to('materialize-report-success')
                else:
                    message = _(messages.attach_error)
                    self.add_message(message, 'danger')            
                    return self.get()                    
            else:
                message = _(messages.report_success)
                self.add_message(message, 'success')
                return self.redirect_to('materialize-report-success')

        except Exception as e:
            logging.info('error in post: %s' % e)
            message = _(messages.saving_error)
            self.add_message(message, 'danger')
            return self.get()

class MaterializeReportUploadImageHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self, report_id):
        try:
            logging.info(self.get_uploads()[0])
            logging.info('attaching file to report_id: %s' %report_id)
            upload = self.get_uploads()[0]
            report = models.Report.get_by_id(long(report_id))
            # report.attachment = upload.key()
            report.image_url = self.uri_for('blob-serve', photo_key = upload.key(), _full=True)
            report.put()
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('success')
        except Exception as e:
            logging.error('something went wrong: %s' % e)
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('error')

class MaterializeReportUploadAttachmentHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self, att_id):
        try:
            logging.info(self.get_uploads()[0])
            logging.info('attachment: %s' % att_id)
            upload = self.get_uploads()[0]
            att = models.Attachment.get_by_id(long(att_id))
            att.file_url = self.uri_for('blob-serve', photo_key = upload.key(), _full=True)
            att.put()
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('success')
        except Exception as e:
            logging.error('something went wrong: %s' % e)
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('error')

class MaterializeNewReportSuccessHandler(BaseHandler):
    """
    Handler for materialized home
    """  
    @user_required
    def get(self):
        """ Returns a simple HTML form for materialize home """
        if not self.has_reports:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####
        
        return self.render_template('materialize/users/sections/report_success.html', **params)

class MaterializeFollowRequestHandler(BaseHandler):
    @user_required
    def post(self):

        if not self.has_reports:
            self.abort(403)

        report_id = int(self.request.get('report_id'))
        user_id = int(self.request.get('user_id'))
        kind = self.request.get('kind')
        reportDict = {}

        try:
            report = models.Report.get_by_cdb(int(report_id))
            if report:
                if kind == 'follow' and report.user_id != int(user_id):
                    follower = models.Followers.query(ndb.AND(models.Followers.user_id == long(user_id),models.Followers.report_id == long(report_id)))
                    if follower.count() == 0 and report:
                        _u = models.User.get_by_id(long(user_id))
                        if _u:
                            follower = models.Followers()
                            follower.user_id = user_id
                            follower.report_id = report_id
                            follower.put()
                            report.follows += 1
                            report.put()
                            #UPDATE CARTO
                            from google.appengine.api import urlfetch
                            import urllib
                            api_key = self.app.config.get('cartodb_apikey')
                            cartodb_domain = self.app.config.get('cartodb_user')
                            cartodb_table = self.app.config.get('cartodb_reports_table')
                            unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET follows = %s WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, report.follows, report_id, api_key)).encode('utf8')
                            url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                            t = urlfetch.fetch(url)
                            reportDict['contents'] = 'follow request successful'
                    elif follower.count() == 1:
                        reportDict['contents'] = 'user already following'
                    reportDict['status'] = 'success'
                elif kind == 'unfollow' and report.user_id != int(user_id):
                    follower = models.Followers.query(ndb.AND(models.Followers.user_id == long(user_id),models.Followers.report_id == long(report_id)))
                    if follower.count > 0:
                        for _f in follower:
                            _f.key.delete()
                            report.follows -= 1
                            report.follows = 0 if report.follows < 0 else report.follows
                            report.put()
                            #UPDATE CARTO
                            from google.appengine.api import urlfetch
                            import urllib
                            api_key = self.app.config.get('cartodb_apikey')
                            cartodb_domain = self.app.config.get('cartodb_user')
                            cartodb_table = self.app.config.get('cartodb_reports_table')
                            unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET follows = %s WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, report.follows, report_id, api_key)).encode('utf8')
                            url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                            t = urlfetch.fetch(url)
                    reportDict['status'] = 'success'
                    reportDict['contents'] = 'unfollow request successful'
                elif report.user_id == int(user_id):
                    reportDict['status'] = 'success'
                    reportDict['contents'] = 'user is creator'
                    reportDict['report_id'] = report_id
                    reportDict['user_id'] = user_id
                    reportDict['kind'] = kind
            else:
                reportDict['status'] = 'success'
                reportDict['contents'] = 'nothing to do here'
                reportDict['report_id'] = report_id
                reportDict['user_id'] = user_id
                reportDict['kind'] = kind
        except Exception as e:
            reportDict['status'] = 'error'
            reportDict['contents'] = '%s' % e
            pass



        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeUrgentRequestHandler(BaseHandler):
    @user_required
    def post(self):

        if not self.has_reports:
            self.abort(403)

        report_id = int(self.request.get('report_id'))
        reportDict = {}
        reportDict['report_id'] = report_id
        reportDict['is_urgent'] = False
        try:
            report = models.Report.get_by_id(int(report_id))
            if report:
                report.urgent = not report.urgent
                report.put()
                reportDict['status'] = 'success'
                reportDict['contents'] = 'toggled urgency successfully'
                reportDict['is_urgent'] = report.urgent
            else:
                reportDict['status'] = 'success'
                reportDict['contents'] = 'nothing to do here'
        except Exception as e:
            reportDict['status'] = 'error'
            reportDict['contents'] = '%s' % e
            pass



        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeRateRequestHandler(BaseHandler):
    @user_required
    def post(self):

        if not self.has_reports:
            self.abort(403)

        report_id = int(self.request.get('report_id'))
        user_id = int(self.request.get('user_id'))
        rating = int(self.request.get('rating'))
        reportDict = {}
        try:
            report = models.Report.get_by_id(long(report_id))
            if report and (report.user_id == user_id or self.user_is_callcenter or self.user_is_secretary or self.user_is_agent or self.user_is_operator):
                report.rating = int(rating)
                if report.rating > 5:
                    report.rating = 5
                if report.rating < 1:
                    report.rating = 1
                report.put()
                #UPDATE CARTO
                from google.appengine.api import urlfetch
                import urllib
                api_key = self.app.config.get('cartodb_apikey')
                cartodb_domain = self.app.config.get('cartodb_user')
                cartodb_table = self.app.config.get('cartodb_reports_table')
                unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET rating = %s WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, report.rating, report.cdb_id, api_key)).encode('utf8')
                url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                t = urlfetch.fetch(url)
                reportDict['status'] = 'success'
                reportDict['contents'] = 'rating request successful'
                reportDict['report_id'] = report_id
                reportDict['user_id'] = user_id
                reportDict['rating'] = rating
            else:
                reportDict['status'] = 'success'
                if report:
                    reportDict['contents'] = 'nothing to do here'
                else:
                    reportDict['contents'] = 'user does not belong'
                reportDict['report_id'] = report_id
                reportDict['user_id'] = user_id
                reportDict['rating'] = rating
        except Exception as e:
            reportDict['status'] = 'error'
            reportDict['contents'] = '%s' % e
            pass



        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))


# ------------------------------------------------------------------------------------------- #
"""                                  CORE PETITION HANDLERS                                 """
# ------------------------------------------------------------------------------------------- #

class MaterializePetitionsRequestHandler(BaseHandler):
    """
        Handler for materialized petitions
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        if not self.has_petitions:
            self.abort(403)

        params, user_info = disclaim(self)

        user_reports = models.Report.query(models.Report.user_id == int(user_info.key.id()))
        user_reports = user_reports.order(-models.Report.created)
        user_reports = user_reports.fetch(50)
        if user_reports is not None:
            try:
                params['reports'] = []
                for report in user_reports:
                    if report.status != 'archived' and report.status != 'spam':
                        params['reports'].append((report.key.id(), report.title, report.when, report.address_from_coord, report.address_from, report.description, report.get_status(), report.image_url, report.group_category, report.sub_category, report.cdb_id, report.req_deletion, report.get_group_color(), report.rating, report.follows, report.get_log_count(), 'own'))
                try:
                    follows = models.Followers.query(models.Followers.user_id == int(user_info.key.id()))
                    for follow in follows:
                        report = models.Report.get_by_cdb(int(follow.report_id))
                        if report:
                            params['reports'].append((report.key.id(), report.title, report.when, report.address_from_coord, report.address_from, report.description, report.get_status(), report.image_url, report.group_category, report.sub_category, report.cdb_id, report.req_deletion, report.get_group_color(), report.rating, report.follows, report.get_log_count(), 'follow'))
                except:
                    pass
            except (AttributeError, TypeError), e:
                login_error_message = _(messages.expired_session)
                logging.error('Error updating profile: %s' % e)
                self.add_message(login_error_message, 'danger')
                self.redirect_to('login')

        return self.render_template('materialize/users/sections/petitions_user.html', **params)

    @user_required
    def post(self):
        delete = self.request.get('delete')
        report_id = self.request.get('report_id')
        
        try:
            report_info = models.Report.get_by_id(long(report_id))
            if delete == 'confirmed_deletion':
                if report_info:
                    report_info.req_deletion = True
            if delete == 'confirmed_cancelation':
                if report_info:
                    report_info.req_deletion = False
            if delete == 'confirmed_comment':
                user_info = self.user_model.get_by_id(long(self.user_id))
                if report_info:
                    report_info.status = 'answered'
                    log_info = models.LogChange()
                    log_info.user_email = user_info.email.lower()
                    log_info.report_id = int(report_id)
                    log_info.kind =  'comment'
                    log_info.title = "Ha hecho un comentario en su reporte."
                    log_info.contents = self.request.get('comment')
                    log_info.put()
                    private = models.SubCategory.query(models.SubCategory.name == report_info.sub_category).get()
                    if private is not None:
                        private = private.private
                    else:
                        private = False
                    
                    #PUSH TO CARTODB
                    from google.appengine.api import urlfetch
                    import urllib
                    api_key = self.app.config.get('cartodb_apikey')
                    cartodb_domain = self.app.config.get('cartodb_user')
                    cartodb_table = self.app.config.get('cartodb_reports_table')
                    if report_info.cdb_id != -1:
                        #UPDATE                        
                        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET pvt = %s ,the_geom = ST_GeomFromText('POINT(%s %s)', 4326), _when = '%s', title = '%s', description = '%s', status = '%s', address_from = '%s', folio = '%s', image_url = '%s', group_category = '%s', sub_category = '%s', follows = %s, rating = %s, via = '%s' WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, private, report_info.address_from_coord.lon, report_info.address_from_coord.lat, report_info.when.strftime("%Y-%m-%d"),report_info.title,report_info.description,report_info.status,report_info.address_from,report_info.folio,report_info.image_url,report_info.group_category,report_info.sub_category,report_info.follows,report_info.rating,report_info.via,report_info.cdb_id,api_key)).encode('utf8')
                        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                        try:
                            t = urlfetch.fetch(url)
                            logging.info("t: %s" % t.content)
                        except Exception as e:
                            logging.info('error in cartodb UPDATE request: %s' % e)
                            pass
                        
            report_info.put()
            self.add_message(messages.inquiry_success, 'success')
            return self.get()

        except (AttributeError, KeyError, ValueError), e:
            logging.error('Error updating report: %s ' % e)
            self.add_message(messages.saving_error, 'danger')
            return self.get()

class MaterializePetitionCardlistHandler(BaseHandler):
    """
        Handler for materialized reports cardlists
    """
    @user_required
    def get(self):
        """ returns simple html for a get request """
        if not self.has_petitions:
            self.abort(403)

        params, user_info = disclaim(self)

        return self.render_template('materialize/users/sections/petitions_list.html', **params)

class MaterializeNewPetitionHandler(BaseHandler):
    """
    Handler for materialized home
    """  
    @user_required
    def get(self):
        """ Returns a simple HTML form for materialize home """
        if not self.has_petitions:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####
        
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')

        return self.render_template('materialize/users/sections/petition_new.html', **params)

    @user_required
    def post(self):
        """ Get fields from POST dict """
        if not self.has_petitions:
            self.abort(403)

        address_from = self.request.get('address_from')
        address_from_coord = self.request.get('address_from_coord')
        catGroup = self.request.get('catGroup')
        subCat = self.request.get('subCat')
        description = self.request.get('description')
        when = self.request.get('when')
        
        try:
            user_info = self.user_model.get_by_id(long(self.user_id))   

            user_report = models.Report()
            user_report.user_id = int(self.user_id) if int(self.user_id) is not None else -1
            user_report.address_from_coord = ndb.GeoPt(address_from_coord)
            user_report.address_from = address_from
            user_report.when = date(int(when[:4]), int(when[5:7]), int(when[8:]))
            user_report.title = u'%s #%s' % (self.app.config.get('app_name'),subCat)
            user_report.description = description
            user_report.group_category = catGroup
            user_report.sub_category  = subCat
            user_report.contact_info = u'%s, %s, %s, %s, %s' % (user_info.name, user_info.last_name, user_info.address.address_from, user_info.phone, user_info.email)
            if user_info.credibility <= 0:
                user_report.status = 'spam'
            
            user_report.put()
            

            if hasattr(self.request.POST['file'], 'filename'):
                #create attachment
                from google.appengine.api import urlfetch
                from poster.encode import multipart_encode, MultipartParam
                
                urlfetch.set_default_fetch_deadline(45)

                payload = {}
                upload_url = blobstore.create_upload_url('/petition/image/upload/%s' %(user_report.key.id()))
                file_data = self.request.POST['file']
                payload['file'] = MultipartParam('file', filename=file_data.filename,
                                                         filetype=file_data.type,
                                                         fileobj=file_data.file)
                data,headers= multipart_encode(payload)
                t = urlfetch.fetch(url=upload_url, payload="".join(data), method=urlfetch.POST, headers=headers)
                
                logging.info('t.content: %s' % t.content)
                
                if t.content == 'success':
                    message = _(messages.report_success)
                    self.add_message(message, 'success')
                    return self.redirect_to('materialize-petition-success')
                else:
                    message = _(messages.attach_error)
                    self.add_message(message, 'danger')            
                    return self.get()                    
            else:
                message = _(messages.report_success)
                self.add_message(message, 'success')
                return self.redirect_to('materialize-petition-success')

        except Exception as e:
            logging.info('error in post: %s' % e)
            message = _(messages.saving_error)
            self.add_message(message, 'danger')
            return self.get()

class MaterializePetitionUploadImageHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self, petition_id):
        try:
            logging.info(self.get_uploads()[0])
            logging.info('attaching file to petition_id: %s' %petition_id)
            upload = self.get_uploads()[0]
            petition = models.Petition.get_by_id(long(petition_id))
            petition.image_url = self.uri_for('blob-serve', photo_key = upload.key(), _full=True)
            petition.put()
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('success')
        except Exception as e:
            logging.error('something went wrong: %s' % e)
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('error')

class MaterializeNewPetitionSuccessHandler(BaseHandler):
    """
    Handler for materialized petition success
    """  
    @user_required
    def get(self):
        """ Returns a simple HTML form for materialize petition success """
        if not self.has_petitions:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####
        
        return self.render_template('materialize/users/sections/petition_success.html', **params)


# ------------------------------------------------------------------------------------------- #
"""                              CORE TRANSPARENCY HANDLERS                                 """
# ------------------------------------------------------------------------------------------- #

class MaterializeTransparencyCityHandler(BaseHandler):
    """
    Handler for materialized petition success
    """  
    @user_required
    def get(self):
        """ Returns a simple HTML for materialize transparency city"""
        if not self.has_transparency:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####

        
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')  
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_pois_table'] = self.app.config.get('cartodb_pois_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['has_cic'] = self.app.config.get('has_cic')
        params['cartodb_cic_user'] = self.app.config.get('cartodb_cic_user')
        params['cartodb_cic_reports_table'] = self.app.config.get('cartodb_cic_reports_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        params['cartodb_polygon_full_name'] = self.app.config.get('cartodb_polygon_full_name')
        params['cartodb_polygon_cve_ent'] = self.app.config.get('cartodb_polygon_cve_ent')
        params['cartodb_markers_url'] = self.uri_for("landing", _full=True)+"default/materialize/images/markers/"
        
        return self.render_template('materialize/users/sections/transparency_city.html', **params)

class MaterializeTransparencyInitiativesHandler(BaseHandler):
    """
    Handler for materialized petition success
    """  
    @user_required
    def get(self):
        """ Returns a simple HTML for materialize transparency initiatives """
        if not self.has_transparency:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####

        params['areas'] = models.Area.query()
        params['count'] = models.Area.query().count()
        params['first_area'] = models.Area.query().get()

        
        return self.render_template('materialize/users/sections/transparency_inits.html', **params)

class MaterializeTransparencyInitiativeHandler(BaseHandler):
    @user_required
    def edit(self, initiative_id):
        if not self.has_transparency:
            self.abort(403)


        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####

        try:
            initiative = models.Initiative.get_by_id(long(initiative_id))
            if initiative:
                params['initiative'] = initiative
                return self.render_template('materialize/users/sections/transparency_initiative.html', **params)
            else:
                self.abort(404)
        except ValueError:
            self.abort(404)


        
#unused
class MaterializeTransparencyBudgetHandler(BaseHandler):
    """
    Handler for materialized petition success
    """  
    @user_required
    def get(self):
        """ Returns a simple HTML for materialize transparency budget"""
        if not self.has_transparency:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####
        
        return self.render_template('materialize/users/sections/transparency_budget.html', **params)

#unused
class MaterializeTransparencyBudgetNewHandler(BaseHandler):
    """
    Handler for materialized petition success
    """  
    @user_required
    def get(self):
        """ Returns a simple HTML for materialize transparency budget new proposal"""
        if not self.has_transparency:
            self.abort(403)

        ####-------------------- P R E P A R A T I O N S --------------------####
        if self.user:
            params, user_info = disclaim(self)
        else:
            params = {}
        ####------------------------------------------------------------------####
        
        return self.render_template('materialize/users/sections/transparency_budget_new.html', **params)


# ------------------------------------------------------------------------------------------- #
"""                                JSON/API HELPER HANDLERS                                 """
# ------------------------------------------------------------------------------------------- #

class MaterializeCategoriesHandler(BaseHandler):
    def get(self):
        if not self.has_reports:
            self.abort(403)
        reportDict = {}
        q = self.request.get('q') if self.request.get('q') else False
        o = self.request.get('o') if self.request.get('o') else False
        logging.info(q)
        logging.info(o)
        
        if q=='count':
            if o == 'agency':
                agencies = models.Agency.query()
                for agency in agencies:
                    groupcat = models.GroupCategory.get_by_id(agency.group_category_id)
                    reports = models.Report.query(models.Report.group_category == groupcat.name)
                    for report in reports:
                        reportDict[agency.name] = reportDict.get(agency.name, {})
                        reportDict[agency.name][groupcat.name] = reportDict[agency.name].get(groupcat.name,{})
                        reportDict[agency.name][groupcat.name][report.sub_category] = reportDict[agency.name][groupcat.name].get(report.sub_category,0)+1
            
            else:
                reports = models.Report.query()
                if o == 'groups':
                    for report in reports:
                        reportDict[report.group_category] = reportDict.get(report.group_category,0)+1
                elif o == 'categories':
                    for report in reports:
                        reportDict[report.sub_category] = reportDict.get(report.sub_category,0)+1
                elif o == 'status':
                    for report in reports:
                        reportDict[report.status] = reportDict.get(report.status,0)+1
                elif o == 'cartostatus':
                    reports = reports.filter(models.Report.cdb_id != -1)
                    for report in reports:
                        reportDict[report.status] = reportDict.get(report.status,0)+1
                elif o == 'cartoticket':
                    reports = reports.filter(models.Report.cdb_id != -1)
                    for report in reports:
                        reportDict[report.cdb_id] = reportDict.get(report.cdb_id,0)+1
                elif o == 'via':
                    for report in reports:
                        reportDict[report.via] = reportDict.get(report.via,0)+1
                else:    
                    for report in reports:
                        reportDict[report.group_category] = reportDict.get(report.group_category, {})
                        reportDict[report.group_category][report.sub_category] = reportDict[report.group_category].get(report.sub_category,0)+1
        
        #Return cdb id (ticket) and corresponding report status
        elif q=='cartoIdStatus':
            reports = models.Report.query(models.Report.cdb_id != -1)
            for report in reports:
                if o == 'reportid':
                    reportDict[report.key.id()] = reportDict.get(report.key.id(),{'status':report.status,'cdb_id':report.cdb_id})
                else:
                    reportDict[report.cdb_id] = reportDict.get(report.cdb_id,report.status)

        #Return category groups and parent agency
        elif q=='agencies':
            groups = models.GroupCategory.query()
            agen_raw = []
            for group in groups:
                agencies = models.Agency.query(models.Agency.group_category_id == group.key.id())
                agenArr = []
                for agency in agencies:
                    agenArr.append(agency.name)    
                    agen_raw.append(agency.name)    
                if o=='orphan':
                    if len(agenArr)==0:
                        reportDict[group.name] = {}
                else:
                    reportDict[group.name] = {'agencies': agenArr}
            if o=='raw':
                self.response.headers.add_header("Access-Control-Allow-Origin", "*")
                self.response.headers['Content-Type'] = 'text/html'
                return self.response.write(json.dumps(agen_raw))

        #Return category groups and parent secretary
        elif q=='secretaries':
            groups = models.GroupCategory.query()
            for group in groups:
                agencies = models.Agency.query(models.Agency.group_category_id == group.key.id())
                secArr = []
                for agency in agencies:
                    secretary = models.Secretary.get_by_id(long(agency.secretary_id))
                    secArr.append(secretary.name)    
                if o=='orphan':
                    if len(secArr)==0:
                        reportDict[group.name] = {}
                else:
                    reportDict[group.name] = {'secretaries': secArr}

        #Return subcategories
        elif q=='subcategories':
            subcats = models.SubCategory.query()
            for cat in subcats:
                reportDict[cat.name] = {
                    'icon_url': cat.icon_url,
                    'requires_image': cat.requires_image,
                    'benchmark': cat.benchmark
                }
        
        #Return organization
        elif q=='org':
            secretaries = models.Secretary.query()
            for secretary in secretaries:
                agencies = secretary.get_agencies()
                agArr = []
                for agency in agencies:
                    if agency.group_category_id is not None:
                        group_cat = models.GroupCategory.get_by_id(long(agency.group_category_id))
                        subcats = [ subs.name for subs in models.SubCategory.query(models.SubCategory.group_category_id == long(group_cat.key.id())) ]
                        operators = agency.get_operators()
                        agArr.append({
                            'name': agency.name,
                            'description': agency.description,
                            'admin_image':  self.user_model.get_by_email(agency.admin_email).get_image_url() if self.user_model.get_by_email(agency.admin_email) else '',
                            'admin_name': agency.admin_name,
                            'admin_email': agency.admin_email,
                            'group_cat': {
                                'name': group_cat.name,
                                'subcats': subcats
                            },
                            'operators' : {operator.name : [self.user_model.get_by_email(operator.email).get_image_url() if self.user_model.get_by_email(operator.email) else '', operator.email] for operator in operators}
                        })
                reportDict[secretary.name] = {
                        'name': secretary.name,
                        'description': secretary.description,
                        'phone': secretary.phone,
                        'address': secretary.address,
                        'admin_name': secretary.admin_name,
                        'admin_email': secretary.admin_email,
                        'admin_image':  self.user_model.get_by_email(secretary.admin_email).get_image_url() if self.user_model.get_by_email(secretary.admin_email) else '',
                        'agency': agArr
                }
                    
        #Return category groups attributes including subcategories
        else:
            groups = models.GroupCategory.query()
            for cat in groups:
                agencies = models.Agency.query(models.Agency.group_category_id == cat.key.id())
                agenArr = []
                secArr = []
                description = ''
                for agency in agencies:
                    agenArr.append(agency.name)    
                    secretary = models.Secretary.get_by_id(long(agency.secretary_id))
                    secArr.append(secretary.name)
                    if secretary.phone != '' or secretary.address != '':
                        description = u'Este grupo de categorías pertenece a %s a cargo de %s, en la %s a cargo de %s. <br><br> Contacto: <br> %s %s' % (secretary.name, secretary.admin_name, agency.name, agency.admin_name, secretary.phone, secretary.address)
                    else:
                        description = u'Este grupo de categorías pertenece a %s a cargo de %s, en la %s a cargo de %s.' % (secretary.name, secretary.admin_name, agency.name, agency.admin_name)
                subcatArr = []
                subcatDescArr = {}
                privateArr = []
                cdbArr = []
                icons = {}
                subcats = models.SubCategory.query(models.SubCategory.group_category_id == cat.key.id())
                for subcat in subcats:
                    subcatArr.append(subcat.name)
                    subcatDescArr[subcat.name]= subcat.description
                    icons[subcat.name]= subcat.icon_url
                    privateArr.append(1 if subcat.private else 0)
                    cdbArr.append(subcat.cdb_id)
                reportDict[cat.name] = {
                    'color': cat.color,
                    'icon': cat.icon_url,
                    'categories': subcatArr,
                    'categories_desc': subcatDescArr,
                    'icon_url': icons,
                    'secretaries': secArr,
                    'agencies': agenArr,
                    'description': description,
                    'pf': privateArr,
                    'scdbs': cdbArr,
                    'gcdb': cat.cdb_id
                }
        
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))
        
class MaterializeReportCommentsHandler(BaseHandler):
    def get(self,report_id):
        if not self.has_reports:
            self.abort(403)

        reportDict = {}
        logs = models.LogChange.query(models.LogChange.report_id == int(report_id))
        logs = logs.order(-models.LogChange.created)
        
        html = '<ul class="collection" style="overflow:scroll;">'
        for log in logs:
            if log.kind != 'note':
                user = log.get_user()            
                if user:
                    image = user.get_image_url()
                    initial_letter = user.name[1]
                    name = user.name
                else:
                    image = -1
                    initial_letter = log.user_email[1]
                    name = ''
                html+= '<li class="collection-item avatar" style="text-align: right; height: auto; display:inline-block; width: 100%; ">'
                if image != -1:
                    html+= '<img src="%s" alt="" class="circle" style="width: 60px;height: 60px;">' % image
                else:
                    html+= '<i class="mdi-action-face-unlock circle brand-color-text white" style="height: 60px;width: 60px;font-size: 40px;padding-top: 8px;"></i>'
                html+= '<span class="title right"><span class="orange-text">%s</span>: %s</span><br><p class="right brand-color-text" style="font-family: roboto-light;"><span class="light-blue-text">%s</span><br>%s</p>' % (name, log.title, log.get_formatted_date(), log.contents)
                html+= '</li>'
        html += '</ul>'
        reportDict['logs'] = {
            'html': html
        }
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeReportCommentsByTicketHandler(BaseHandler):
    def get(self,ticket):
        if not self.has_reports:
            self.abort(403)

        reportDict = {}
        reportDict['logs'] = {
            'html': 'error in ticket number request'
        }
        if ticket:
            try:
                report = models.Report.get_by_cdb(int(ticket))
                if report:
                    report_id = report.key.id()
                    logs = models.LogChange.query(models.LogChange.report_id == int(report_id))
                    logs = logs.order(-models.LogChange.created)
                    
                    html = '<ul class="collection" style="overflow:scroll;">'
                    for log in logs:
                        if log.kind != 'note':
                            user = log.get_user()            
                            if user:
                                image = user.get_image_url()
                                initial_letter = user.name[1]
                                name = user.name
                            else:
                                image = -1
                                initial_letter = log.user_email[1]
                                name = ''
                            html+= '<li class="collection-item avatar" style="text-align: right; height: auto; display:inline-block; width: 100%; ">'
                            if image != -1:
                                html+= '<img src="%s" alt="" class="circle" style="width: 60px;height: 60px;">' % image
                            else:
                                html+= '<i class="mdi-action-face-unlock circle brand-color-text white" style="height: 60px;width: 60px;font-size: 40px;padding-top: 8px;"></i>'
                            html+= '<span class="title right"><span class="orange-text">%s</span>: %s</span><br><p class="right brand-color-text" style="font-family: roboto-light;"><span class="light-blue-text">%s</span><br>%s</p>' % (name, log.title, log.get_formatted_date(), log.contents)
                            html+= '</li>'
                    html += '</ul>'
                    reportDict['logs'] = {
                        'html': html
                    }
            except Exception as e:
                logging.info("error loading comments from ticket -%s-: %s" % (ticket,e))                
                pass

        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeReportCommentsAddHandler(BaseHandler):
    @user_required
    def get(self):
        if not self.has_reports:
            self.abort(403)

        reportDict = {}
        report = models.Report.get_by_cdb(int(self.request.get('ticket')))
        if report:
            report_id = report.key.id()
            comments = self.request.get('comment')

            try:
                user_info = self.user_model.get_by_id(long(self.user_id))
                report_info = models.Report.get_by_id(long(report_id))
                if report_info:
                    log_info = models.LogChange()
                    log_info.user_email = user_info.email.lower()
                    log_info.report_id = int(report_id)
                    log_info.contents = comments
                    log_info.kind = 'comment'
                    log_info.title = "Ha hecho un comentario."
                    log_info.put()                

                reportDict['status'] = 'success'

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating report: %s ' % e)
                reportDict['status'] = 'error: %s' % e
                pass

        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeReportAuthorRequestHandler(BaseHandler):
    def get(self,uuid):
        if not self.has_reports:
            self.abort(403)

        reportDict = {}
        reportDict['response'] = {
            'status': 'error',
            'content': 'error in uuid number request'
        }

        if uuid:
            try:
                report = models.Report.get_by_id(long(uuid))
                if report:
                    if report.user_id == -1:
                        reportDict['response']['user_url'] = '#'
                        reportDict['response']['name'] = report.contact_name
                        reportDict['response']['lastname'] = report.contact_lastname
                        reportDict['response']['content'] = 'manually created report, collected contact info'
                    else:
                        reportDict['response']['user_url'] = report.user_id
                        reportDict['response']['name'] = report.get_user_name()
                        reportDict['response']['lastname'] = report.get_user_lastname()
                        reportDict['response']['content'] = 'user created report, collected user data'
                    reportDict['response']['status'] = 'success'

            except Exception as e:
                logging.info("error loading author from uuid -%s-: %s" % (uuid,e))                
                pass

        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeLogChangeDeleteHandler(BaseHandler):
    def get_log_or_404(self, log_id):
        if log_id:
            try:
                log = models.LogChange.get_by_id(long(log_id))
                if log:
                    return log
            except ValueError:
                pass
        self.abort(404)

    def edit(self, log_id):
        if not self.has_reports:
            self.abort(403)
        reportDict = {}
        log = self.get_log_or_404(log_id)
        if self.request.POST:
            try:
                log.key.delete()
                reportDict['status'] = "deleted successfully"

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error deleting logchange -%s-: %s ' % (log_id,e))
                reportDict['status'] = "something went wrong"
        else:
            reportDict['status'] = "log not found"

        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeAttachmentDeleteHandler(BaseHandler):
    def get_att_or_404(self, att_id):
        if att_id:
            try:
                att = models.Attachment.get_by_id(long(att_id))
                if att:
                    return att
            except ValueError:
                pass
        self.abort(404)

    def edit(self, att_id):
        if not self.has_reports:
            self.abort(403)
        reportDict = {}
        att = self.get_att_or_404(att_id)
        if self.request.POST:
            try:
                att.key.delete()
                reportDict['status'] = "deleted successfully"

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error deleting attachment -%s-: %s ' % (att_id,e))
                reportDict['status'] = "something went wrong"
        else:
            reportDict['status'] = "att not found"

        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeTopicsHandler(BaseHandler):
    def get(self):
        if not self.has_petitions:
            self.abort(403)

        reportDict = {}
        q = self.request.get('q') if self.request.get('q') else False
        o = self.request.get('o') if self.request.get('o') else False
        logging.info(q)
        logging.info(o)

        topics = models.Topic.query()
        for topic in topics:
            reportDict[topic.name] = {
                    'name': topic.name,
                    'color': topic.color,
                    'icon_url': topic.icon_url,
                    'requires_image': topic.requires_image,
                    'benchmark': topic.benchmark,
                    'trigger': topic.trigger,
                }
        
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeAreasHandler(BaseHandler):
    def get(self):
        if not self.has_transparency:
            self.abort(403)

        reportDict = {}
        q = self.request.get('q') if self.request.get('q') else False
        o = self.request.get('o') if self.request.get('o') else False
        area_id = self.request.get('area_id') if self.request.get('area_id') else False
        init_id = self.request.get('init_id') if self.request.get('init_id') else False
        logging.info(q)
        logging.info(o)

        if area_id:
            reportDict['initiatives'] = {
                'html': 'error in area id number request'
            }
            html = ''
            empty = True
            initiatives = models.Initiative.query(models.Initiative.area_id == int(area_id))
            for initiative in initiatives:
                empty = False
                html += '<div class="card col s12 m3 hoverable" onclick="loadDetail(%s)"><div class="initiative card-content center" style="padding:8px;"><p class="initiative image left" style="background-color: %s%s;  -webkit-mask: url(%s) no-repeat 50%s 50%s ;"></p><span class="center" style="text-transform: uppercase;color:%s%s;">%s</span><div class="col s12" style="margin-bottom:18px; border-radius:2px; margin-top:25px;">' % (initiative.get_id(), "#", initiative.color, initiative.icon_url, "%", "%", "#", initiative.color, initiative.name)
                
                if initiative.status == 'completed':
                    html += '<a class="btn-floating btn-move-up waves-effect waves-light green right tooltipped" data-position="top" data-delay="50" data-tooltip="Cumplido" style="top: 25px;left: 10px;"><i class="mdi-action-verified-user"></i></a>'
                
                html += '<div class="col s10 offset-s1 valign-wrapper center grey-text" style="height:100px; margin-bottom:20px;border: 8px solid %s%s; border-radius: 4px;"><span class="col s12 center flow-text">%s</span></div><p class="col s12 center" style="color:%s%s;">%s</p></div></div><div class="card-action"></div></div>' % ("#",initiative.get_status_color(), initiative.value, "#", initiative.get_status_color(), initiative.get_status())

            if empty:
                html += '<div class="card col m2 hoverable"><div class="initiative card-content center" style="padding:8px;"><p class="initiative image left" style="background-color: %s9b9b9b;  -webkit-mask: url(http://one-smart-city-demo.appspot.com/default/materialize/images/google_icons/zoom-out.svg) no-repeat 50%s 50%s ;"></p><span class="center" style="text-transform: uppercase;color:%s9b9b9b;">No hay compromisos</span></div><div class="card-action"></div></div>' % ("#", "%" , "%", "#")
            
            reportDict['initiatives']['html'] = html
        
        elif init_id:
            reportDict['initiatives'] = {
                'initiative': 'error in init id number request'
            }
            html = ''
            initiative = models.Initiative.get_by_id(int(init_id))
            if initiative:
                reportDict['initiatives']['initiative'] = {
                    'name' : initiative.name,
                    'color' : initiative.color,
                    'icon_url' : initiative.icon_url,
                    'image_url' : initiative.image_url,
                    'value' : initiative.value,
                    'lead' : initiative.lead,
                    'description' : initiative.description,
                    'relevance' : initiative.relevance,
                    'status' : initiative.get_status(),
                    'status_color' : initiative.get_status_color(),
                    'area' : initiative.get_area_name()
                }

        else:
            area = models.Area.query()
            for area in area:
                reportDict[area.name] = {
                        'name': area.name,
                        'color': area.color,
                        'icon_url': area.icon_url
                    }
        
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))

class MaterializeUserBudgetHandler(BaseHandler):
    def get(self):
        if not self.has_transparency:
            self.abort(403)
        reportDict = {
            "name": "US_Budget",
            "children": [       
                {
                    "name": "DEF",
                    "label": "Infraestructura",
                    "size": 20,
                    "color": "#cc3333"
                },{
                    "name": "SCI",
                    "label": "Ciencia e investigación",
                    "size": 4.5,
                    "color": "#ea4c88"
                },
                {
                    "name": "EDU",
                    "label": "Educación",
                    "size": 3.5,
                    "color": "#663399"
                },
                {
                    "name": "ENE",
                    "label": "Energía renovable",
                    "size": 1.5,
                    "color": "#0066cc"
                },
                {
                    "name": "TRA",
                    "label": "Transporte",
                    "size": 2.5,
                    "color": "#669900"
                },
                {
                    "name": "CRD",
                    "label": "Desarrollo social",
                    "size": 1.5,
                    "color": "#ffcc33"
                },
                {
                    "name": "AGR",
                    "label": "Reforestación",
                    "size": 1.5,
                    "color": "#ff9900"
                },
                {
                    "name": "OTH",
                    "label": "Otros",
                    "size": 8,
                    "color": "#996633"
                },
                {
                    "name": "HEL",
                    "label": "Servicios de salud",
                    "size": 22,
                    "color": "#663300"
                },
                {
                    "name": "INC",
                    "label": "Empleo",
                    "size": 15,
                    "color": "#353535"
                },
                {
                    "name": "SOC",
                    "label": "Seguridad social",
                    "size": 20,
                    "color": "#999999"
                }
            ]
        }
        
        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))
 

# ------------------------------------------------------------------------------------------- #
"""                                     REST API HANDLERS                                   """
# ------------------------------------------------------------------------------------------- #

class APIDocHandler(BaseHandler):
    @user_required
    def get(self):
        """ Returns a simple HTML form for materialize home """
        ####-------------------- R E D I R E C T I O N S --------------------####
        if not self.user:
            return self.redirect_to('login')
        ####------------------------------------------------------------------####

        ####-------------------- P R E P A R A T I O N S --------------------####
        params, user_info = disclaim(self)
        ####------------------------------------------------------------------####
        return self.render_template('materialize/api/doc.html',**params)

class APIIncomingHandler(BaseHandler):
    """
    Core Handler for incoming interactions
    """

    def post(self):
        KEY = "mwkMqTWFnK0LzJHyfkeBGoS2hr2KG7WhHqSGX0SbDJ4"
        SECRET = "152731fe2b14da111a72127d642e73c779e530b3"
        
        api_key = ""
        api_secret = ""
        args = self.request.arguments()
        for arg in args:
            logging.info("argument: %s" % arg)
            for key,value in json.loads(arg).iteritems():
                if key == "api_key":
                    api_key = value
                if key == "api_secret":
                    api_secret = value
                if key == "method":
                    if value == "101":
                        logging.info("parsing method 101")
                    elif value == "201":
                        logging.info("parsing method 201")

                        

        if api_key == KEY and api_secret == SECRET:
            logging.info("Attempt to receive incoming message with key: %s." % api_key)

            # DO SOMETHING WITH RECEIVED PAYLOAD

        else:
            logging.info("Attempt to receive incoming message without appropriate key: %s." % api_key)
            self.abort(403)

class APIOutgoingHandler(BaseHandler):
    """
    Core Handler for outgoing interactions with simpplo
    """

    def post(self):
        from google.appengine.api import urlfetch
        
        KEY = "mwkMqTWFnK0LzJHyfkeBGoS2hr2KG7WhHqSGX0SbDJ4"
        _URL = ""


        api_key = ""
        api_secret = ""
        args = self.request.arguments()
        for arg in args:
            logging.info("argument: %s" % arg)
            for key,value in json.loads(arg).iteritems():
                if key == "api_key":
                    api_key = value
                if key == "api_secret":
                    api_secret = value
                if key == "method":
                    if value == "101":
                        logging.info("parsing method 101")
                    elif value == "201":
                        logging.info("parsing method 201")
                        

        if api_key == KEY:
            logging.info("Attempt to send outgoing message with appropriate key: %s." % api_key)
            
            # DO SOMETHING WITH RECEIVED PAYLOAD
            #urlfetch.fetch(_URL, payload='', method='POST') 

        else:
            logging.info("Attempt to send outgoing message without appropriate key: %s." % api_key)
            self.abort(403)
       
class APITestingHandler(BaseHandler):
    """
    Core Handler for testing interactions with simpplo
    """

    def get(self):
        from google.appengine.api import urlfetch
        import urllib

        try:
            _url = self.uri_for('mbapi-out', _full=True)
            urlfetch.fetch(_url, payload='{"api_key": "mwkMqTWFnK0LzJHyfkeBGoS2hr2KG7WhHqSGX0SbDJ4","channel": "CHANNELHERE","container": "CONTENTSHERE"}', method="POST")
        except:
            pass
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('Tests went good... =)')

class MBoiUsersHandler(BaseHandler):
    def get(self):
        reportDict = {}
        try:
            users = self.user_model.query()
            reportDict['status'] = 'success'
            reportDict['users'] = users.count()
            reportDict['exception'] = ''
            
        except Exception as e:
            reportDict['status'] = 'error'
            reportDict['users'] = 0
            reportDict['exception'] = '%s' % e

        self.response.headers.add_header("Access-Control-Allow-Origin", "*")
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(reportDict))


# ------------------------------------------------------------------------------------------- #
"""                                     MEDIA HANDLERS                                      """
# ------------------------------------------------------------------------------------------- #

#SMALL MEDIA
class MediaDownloadHandler(BaseHandler):
    """
    Handler for Serve Vendor's Logo
    """
    def get(self, kind, media_id):
        """ Handles download"""

        params = {}

        if kind == 'profile':
            user_info = self.user_model.get_by_id(long(media_id))        
            if user_info != None:
                if user_info.picture != None:
                    self.response.headers['Content-Type'] = 'image/png'
                    self.response.out.write(user_info.picture)


        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('No image')

#LARGE MEDIA
class BlobFormHandler(BaseHandler, blobstore_handlers.BlobstoreUploadHandler):
    """
        To better handle text inputs included in same file form, please refer to bp_admin/blog.py
    """
    @user_required
    def get(self):
        upload_url = blobstore.create_upload_url('/blobstore/upload/')
        self.response.out.write('<html><body>')
        self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
        self.response.out.write('''<h2>Sube tu archivo y luego copia la liga directo de tu navegador</h2><br> <input type="file" name="file" style="padding: 20px;"><br> <input type="submit"
            name="submit" value="Subir archivo" style="background-color: #FFFFFF;font-family: roboto-light;padding: 20px;margin: 10px;"> <input type="hidden" name="_csrf_token" value="%s"> </form></body></html>''' % self.session.get('_csrf_token'))

class BlobUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        try:
            upload = self.get_uploads()[0]
            user_photo = models.Media(blob_key=upload.key())
            user_photo.put()
            self.redirect('/blobstore/serve/%s' % upload.key())
        except:
            self.error(404)

class BlobDownloadHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, photo_key):
        if not blobstore.get(photo_key):
            self.error(404)
        else:
            self.send_blob(photo_key)


# ------------------------------------------------------------------------------------------- #
"""                                CRONJOB + TASKQUEUE HANDLERS                             """
# ------------------------------------------------------------------------------------------- #

class Auto72CronjobHandler(BaseHandler):
    def get(self):
        _url = self.uri_for('taskqueue-auto72')
        taskqueue.add(url=_url, params={
        })
        
class Auto72Handler(BaseHandler):
    """
    Core Handler for sending users automatic 72-hours insurance message
    Use with TaskQueue
    """

    @taskqueue_method
    def post(self):
        # HERE WE MUST CREATE CODE FOR               
        # SENDING AUTOMATIC EMAIL IF REPORT STATUS IS OPEN, MORE THAN 3 DAYS HAVE PASSED AND REPORT EMAILED_72 IS FALSE. (template: auto_72.txt)
        # REPORT EMAILED_72 VARIABLE MUST BE SET TO TRUE
        return ''

class ForgotCronjobHandler(BaseHandler):
    def get(self):
        _url = self.uri_for('taskqueue-forgot')
        taskqueue.add(url=_url, params={
        })
        
class ForgotHandler(BaseHandler):
    """
    Core Handler for sending users automatic forgot insurance message
    Use with TaskQueue
    """

    @taskqueue_method
    def post(self):
        # HERE WE MUST CREATE CODE FOR:
        # If report is HALTED for more than 30 days a cronjob will set: status -> FORGOT               
        # AUTOMATIC EMAIL IF REPORT STATUS IS AUTOMATICALLY CHANGED TO FORGOT. (template: change_notification.txt)
        return ''


# ------------------------------------------------------------------------------------------- #
"""                                     WEB STATIC HANDLERS                                 """
# ------------------------------------------------------------------------------------------- #
class RobotsHandler(BaseHandler):
    def get(self):
        params = {
            'scheme': self.request.scheme,
            'host': self.request.host,
        }
        self.response.headers['Content-Type'] = 'text/plain'

        def set_variables(text, key):
            return text.replace("{{ %s }}" % key, params[key])

        self.response.write(reduce(set_variables, params, open("bp_content/themes/%s/templates/seo/robots.txt" % self.get_theme).read()))

class HumansHandler(BaseHandler):
    def get(self):
        params = {
            'scheme': self.request.scheme,
            'host': self.request.host,
        }
        self.response.headers['Content-Type'] = 'text/plain'

        def set_variables(text, key):
            return text.replace("{{ %s }}" % key, params[key])

        self.response.write(reduce(set_variables, params, open("bp_content/themes/%s/templates/seo/humans.txt" % self.get_theme).read()))

class SitemapHandler(BaseHandler):
    def get(self):
        params = {
            'scheme': self.request.scheme,
            'host': self.request.host,
        }
        self.response.headers['Content-Type'] = 'application/xml'

        def set_variables(text, key):
            return text.replace("{{ %s }}" % key, params[key])

        self.response.write(reduce(set_variables, params, open("bp_content/themes/%s/templates/seo/sitemap.xml" % self.get_theme).read()))

class CrossDomainHandler(BaseHandler):
    def get(self):
        params = {
            'scheme': self.request.scheme,
            'host': self.request.host,
        }
        self.response.headers['Content-Type'] = 'application/xml'

        def set_variables(text, key):
            return text.replace("{{ %s }}" % key, params[key])

        self.response.write(reduce(set_variables, params, open("bp_content/themes/%s/templates/seo/crossdomain.xml" % self.get_theme).read()))
