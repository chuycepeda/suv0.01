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
from bp_includes.lib.cartodb import CartoDBAPIKey, CartoDBException
from google.appengine.api import urlfetch
import urllib
from bp_includes.lib.decorators import taskqueue_method



"""

    REPORTS HANDLERS

"""
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

class AdminInboxHandler(BaseHandler):
    def get(self):
        params={}
        names = []
        categories = models.GroupCategory.query()
        for category in categories:
            names.append(category.name)

        status = self.request.get('status') if (self.request.get('status') or self.request.get('status') != "") else False
        ticket = int(self.request.get('ticket')) if (self.request.get('ticket') or self.request.get('ticket') != "") else False
        folio = self.request.get('folio') if (self.request.get('folio') or self.request.get('folio') != "") else False
        groupCat = self.request.get('cat') if (self.request.get('cat') or self.request.get('cat') != "") else False
        
        logging.info(status)
        logging.info(ticket)
        logging.info(folio)
        logging.info(groupCat)
        
        p = self.request.get('p')
        q = self.request.get('q')
        c = self.request.get('c')
        forward = True if p not in ['prev'] else False
        cursor = Cursor(urlsafe=c)

        if q:
            reports = models.Report.query()            
            count = reports.count()
        else:
            if groupCat:
                reports = models.Report.query(models.Report.group_category == groupCat)
                params['ddfill'] = groupCat
            else:
                reports = models.Report.query()
                params['ddfill'] = 'TODOS'
            if status:
                reports = reports.filter(models.Report.status == status) if status != 'pending' else reports.filter(models.Report.status.IN(['assigned', 'halted', 'answered', 'working']))
                params['ddfillstat'] = get_status(status)
            else:
                params['ddfillstat'] = 'TODOS'
            if ticket:    
                reports = reports.filter(models.Report.cdb_id == ticket)
            if folio:     
                reports = reports.filter(models.Report.folio == folio)
            count = reports.count()
            PAGE_SIZE = 100
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
            return self.uri_for('admin-inbox', **params)



        self.view.pager_url = pager_url
        self.view.q = q

        params['statusval'] = get_status(status) if status else ""
        params['ticketval'] = ticket if ticket else ""
        params['folioval'] = folio if folio else ""
        params['catGroup'] = groupCat if groupCat else ""
        params['reports'] = reports
        params['count'] = count
        params['cats'] = sorted(names) if names else names
        params['inbox'] = 'admin-inbox'
        params['nickname'] = g_users.get_current_user().email().lower()

        return self.render_template('admin_inbox.html', **params)

class AdminMapHandler(BaseHandler):
    """
    Handler to show the map page
    """
    def get(self):
        """ Returns a simple HTML form for landing """
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')  
        params['right_sidenav_msg'] = self.app.config.get('right_sidenav_msg')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_has_cic'] = self.app.config.get('cartodb_has_cic')
        params['cartodb_cic_user'] = self.app.config.get('cartodb_cic_user')
        params['cartodb_cic_reports_table'] = self.app.config.get('cartodb_cic_reports_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        params['cartodb_markers_url'] = self.uri_for("landing", _full=True)+"default/materialize/images/markers/"
        return self.render_template('admin_map.html', **params)

class AdminManualHandler(BaseHandler):
    """
    Handler to show the manuals page
    """
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_manual.html', **params)

class AdminReportEditHandler(BaseHandler):
    def get_or_404(self, report_id):
        try:
            report = models.Report.get_by_id(long(report_id))
            if report:
                return report
        except ValueError:
            pass
        self.abort(404)

    def edit(self, report_id):
        if self.request.POST:
            report_info = self.get_or_404(report_id)
            delete = self.request.get('delete')
            try:
                if delete == 'confirmed_deletion':
                    
                    #ASSIGN AS IS
                    report_info.status = 'archived'
                    report_info.terminated = datetime.now()
                    #LOG CHANGES
                    log_info = models.LogChange()
                    log_info.user_email = g_users.get_current_user().email().lower()
                    log_info.report_id = int(report_id)
                    log_info.kind = 'status'
                    log_info.title = "Ha archivado este reporte."
                    log_info.contents = self.request.get('contents')
                    log_info.put()

                    #PUSH UPDATED STATUS TO CARTODB
                    from google.appengine.api import urlfetch
                    import urllib
                    api_key = self.app.config.get('cartodb_apikey')
                    cartodb_domain = self.app.config.get('cartodb_user')
                    cartodb_table = self.app.config.get('cartodb_reports_table')
                    if report_info.cdb_id != -1:
                        #UPDATE
                        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET status = '%s' WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, report_info.status, report_info.cdb_id, api_key)).encode('utf8')
                        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                        try:
                            t = urlfetch.fetch(url)
                            logging.info("t: %s" % t.content)
                        except Exception as e:
                            logging.info('error in cartodb request: %s' % e)
                            pass
                    report_info.put()

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-report-edit", report_id=report_id)

                elif delete == 'report_edition':

                    #UPDATED VALUES
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
                        return self.redirect_to("admin-report-edit", report_id=report_id)


                    #ASSIGN AS IS
                    status = status if status != 'undefined' else report_info.status

                    if report_info.address_from != address_from:
                        report_info.address_from = address_from
                        changes += "el domicilio, "
                    if report_info.address_from_coord != ndb.GeoPt(address_from_coord):
                        report_info.address_from_coord = ndb.GeoPt(address_from_coord)
                        changes += "el mapa, "
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
                    log_info.user_email = g_users.get_current_user().email().lower()
                    log_info.report_id = int(report_id)
                    log_info.kind = kind
                    if kind == 'status' and report_info.status == 'archived':
                        log_info.title = "Ha archivado este reporte."
                        log_info.contents = self.request.get('contents')
                    elif kind == 'status' and report_info.status == 'spam':
                        log_info.title = "Ha marcado como spam este reporte."
                        log_info.contents = self.request.get('contents')
                    elif kind == 'status' and report_info.status == 'solved':
                        log_info.title = "Ha marcado como resuelto este reporte."
                        log_info.contents = self.request.get('contents')
                    elif kind == 'status' and report_info.status == 'failed':
                        log_info.title = "Ha marcado como fallido este reporte."
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
                

                    #PUSH TO CARTODB
                    from google.appengine.api import urlfetch
                    import urllib
                    api_key = self.app.config.get('cartodb_apikey')
                    cartodb_domain = self.app.config.get('cartodb_user')
                    cartodb_table = self.app.config.get('cartodb_reports_table')
                    if report_info.cdb_id == -1:
                        #INSERT
                        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=INSERT INTO %s (created, pvt, the_geom, _when, title, description, status, address_from, folio, image_url, group_category, sub_category, follows, rating, via) VALUES ('%s', %s, ST_GeomFromText('POINT(%s %s)', 4326),'%s','%s','%s','%s','%s','%s','%s','%s','%s',%s,%s,'%s')&api_key=%s" % (cartodb_domain, cartodb_table, report_info.created.strftime("%Y-%m-%d %H:%M:%S"), private, report_info.address_from_coord.lon, report_info.address_from_coord.lat, report_info.when.strftime("%Y-%m-%d"),report_info.title,report_info.description,report_info.status,report_info.address_from,report_info.folio,report_info.image_url,report_info.group_category,report_info.sub_category,report_info.follows,report_info.rating,report_info.via,api_key)).encode('utf8')
                        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                        try:
                            t = urlfetch.fetch(url)
                            logging.info("t: %s" % t.content)
                            #SELECT CARTODB_ID & ASSIGN
                            cl = CartoDBAPIKey(api_key, cartodb_domain)
                            response = cl.sql('select cartodb_id from %s order by cartodb_id desc limit 1' % cartodb_table)
                            report_info.cdb_id = response['rows'][0]['cartodb_id']
                        except Exception as e:
                            logging.info('error in cartodb INSERT request: %s' % e)
                            pass
                    else:
                        #UPDATE
                        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET terminated = '%s', pvt = %s ,the_geom = ST_GeomFromText('POINT(%s %s)', 4326), _when = '%s', title = '%s', description = '%s', status = '%s', address_from = '%s', folio = '%s', image_url = '%s', group_category = '%s', sub_category = '%s', follows = %s, rating = %s, via = '%s' WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table,report_info.terminated.strftime("%Y-%m-%d %H:%M:%S"), private, report_info.address_from_coord.lon, report_info.address_from_coord.lat, report_info.when.strftime("%Y-%m-%d"),report_info.title,report_info.description,report_info.status,report_info.address_from,report_info.folio,report_info.image_url,report_info.group_category,report_info.sub_category,report_info.follows,report_info.rating,report_info.via,report_info.cdb_id,api_key)).encode('utf8')
                        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                        try:
                            t = urlfetch.fetch(url)
                            logging.info("t: %s" % t.content)
                        except Exception as e:
                            logging.info('error in cartodb UPDATE request: %s' % e)
                            pass
                    report_info.put()

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
                    if kind != 'note' and report_info.status != 'archived' and report_info.status != 'spam':
                        reason = ""
                        if kind == 'comment':
                            reason = unicode('Tu reporte fue recibido pero hacen falta algunas aclaraciones para poder seguir avanzando en su solución. Por favor visita Alcalde en Línea en la sección de Mis reportes y envíanos tus comentarios.','utf-8')
                        elif kind == 'status' and report_info.status == 'assigned':
                            if report_info.get_agency() != '':
                                _r = u'Tu reporte fue recibido y asignado a la %s, parte de la %s. Visita Alcalde en Línea para ver su estado actual, es posible que necesitemos información adicional.'
                                reason = _r % (report_info.get_agency(), report_info.get_secretary())
                            else:
                                reason = unicode('Tu reporte fue recibido y asignado. Visita Alcalde en Línea para ver su estado actual, es posible que necesitemos información adicional.', 'utf-8')
                        elif 'categoria' in changes:
                            if report_info.get_agency() != '':
                                _r = u'Tu reporte fue recibido y re-asignado a la %s, parte de la %s. Visita Alcalde en Línea para ver su estado actual, es posible que necesitemos información adicional.'
                                reason = _r % (report_info.get_agency(), report_info.get_secretary())
                            else:
                                reason = unicode('Tu reporte fue recibido y asignado. Visita Alcalde en Línea para ver su estado actual, es posible que necesitemos información adicional.', 'utf-8')
                        else:
                            reason = unicode('Tu reporte ha sido modificado en algunos campos y estamos avanzando en solucionarlo. Por favor visita Alcalde en Línea en la sección de Mis reportes y si tienes algún comentario por favor háznoslo saber.','utf-8')

                        template_val = {
                            "name": report_info.get_user_name(),
                            "_url": self.uri_for("materialize-reports", _full=True),
                            "cdb_id": report_info.cdb_id,
                            "reason": reason,
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
                    return self.redirect_to("admin-report-edit", report_id=report_id)
                
            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating report: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("admin-report-edit", report_id=report_id)
        else:
            report_info = self.get_or_404(report_id)

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
        params['nickname'] = g_users.get_current_user().email().lower()
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        return self.render_template('admin_report_edit.html', **params)

class AdminOrganizationViewHandler(BaseHandler):
    """
    Handler to show the organization visualization page
    """
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')        
        return self.render_template('admin_orgview.html', **params)

"""

    CALL CENTER HANDLERS

"""
class AdminCallCenterHandler(BaseHandler):
    def get(self):
        params = {}
        params['operators']  = models.CallCenterOperator.query()
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_callcenter.html', **params)

    def post(self):
        try:
            #SECRETARY ADD
            logging.info("adding a new callcenter operator")
            operator = models.CallCenterOperator()
            operator.email = self.request.get('adminemail') if self.request.get('adminemail') else ''
            operator.name = self.request.get('adminname') if self.request.get('adminname') else ''
            operator.put()

            #SEND EMAIL NOTIFICATION TO ADMIN_EMAIL
            template_val = {
                "_url": self.uri_for("landing", _full=True),
                "support_url": self.uri_for("contact", _full=True),
                "twitter_url": self.app.config.get('twitter_url'),
                "facebook_url": self.app.config.get('facebook_url'),
                "faq_url": self.uri_for("faq", _full=True)
            }
            body_path = "emails/special_access_invite.txt"
            body = self.jinja2.render_template(body_path, **template_val)

            email_url = self.uri_for('taskqueue-send-email')
            taskqueue.add(url=email_url, params={
                'to': str(operator.email),
                'subject': messages.special_access,
                'body': body,
            })

            self.add_message(messages.saving_success, 'success')
            return self.get()
        except Exception as e:
            logging.info("error in saving to datastore: %s" % e)
            self.add_message(messages.saving_error, 'danger')
            return self.get()

class AdminCallCenterOperatorHandler(BaseHandler):
    def get_or_404(self, operator_id):
        try:
            operator = models.CallCenterOperator.get_by_id(long(operator_id))
            if operator:
                return operator
        except ValueError:
            pass
        self.abort(404)

    def edit(self, operator_id):
        if self.request.POST:
            operator = self.get_or_404(operator_id)
            delete = self.request.get('delete')
            
            try:

                if delete == 'confirmed_deletion':
                    #DELETE REQUEST
                    operator_info = models.CallCenterOperator.get_by_id(long(operator_id))
                    operator_info.key.delete()
                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-callcenter")
                elif delete == 'operator_edition':
                    #OPERATOR EDITION
                    operator_info = models.CallCenterOperator.get_by_id(long(operator_id))
                    operator_info.name = self.request.get('opsadminname') if self.request.get('opsadminname') else ''
                    if operator_info.email != self.request.get('opsadminemail') and self.request.get('opsadminemail') != '':
                        operator_info.email = self.request.get('opsadminemail')
                        #SEND EMAIL NOTIFICATION TO ADMIN_EMAIL
                        template_val = {
                            "_url": self.uri_for("landing", _full=True),
                            "support_url": self.uri_for("contact", _full=True),
                            "twitter_url": self.app.config.get('twitter_url'),
                            "facebook_url": self.app.config.get('facebook_url'),
                            "faq_url": self.uri_for("faq", _full=True)
                        }
                        body_path = "emails/special_access_invite.txt"
                        body = self.jinja2.render_template(body_path, **template_val)

                        email_url = self.uri_for('taskqueue-send-email')
                        taskqueue.add(url=email_url, params={
                            'to': str(operator_info.email),
                            'subject': messages.special_access,
                            'body': body,
                        })
                    operator_info.put()

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-callcenter-edit", operator_id=operator_id)

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating operator: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("admin-callcenter-edit", operator_id=operator_id)
        else:
            operator = self.get_or_404(operator_id)

        params = {
            'operator': operator,
            '_user': models.User.get_by_email(operator.email)
        }
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_callcenter_operator.html', **params)

"""

    ORGANIZATION HANDLERS

"""
class AdminOrganizationHandler(BaseHandler):
    def get(self):
        params = {}
        params['secretaries']  = models.Secretary.query()
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_organization.html', **params)

    def post(self):
        try:
            #SECRETARY ADD
            logging.info("adding a new secretary")
            name = self.request.get('secname') if self.request.get('secname') else ''
            possible_repeat = models.Secretary.query(models.Secretary.name == name).get()
            if possible_repeat is not None:
                self.add_message(messages.nametaken, 'danger')
                logging.info(messages.nametaken)
            else:
                secretary = models.Secretary()
                secretary.name = name            
                secretary.description = self.request.get('description') if self.request.get('description') else ''
                secretary.admin_email = self.request.get('adminemail').lower() if self.request.get('adminemail') else ''
                secretary.admin_name = self.request.get('adminname') if self.request.get('adminname') else ''
                secretary.phone = self.request.get('phone') if self.request.get('phone') else ''
                secretary.address = self.request.get('address') if self.request.get('address') else ''
                secretary.put()

                #SEND EMAIL NOTIFICATION TO ADMIN_EMAIL
                template_val = {
                    "_url": self.uri_for("landing", _full=True),
                    "support_url": self.uri_for("contact", _full=True),
                    "twitter_url": self.app.config.get('twitter_url'),
                    "facebook_url": self.app.config.get('facebook_url'),
                    "faq_url": self.uri_for("faq", _full=True)
                }
                body_path = "emails/special_access_invite.txt"
                body = self.jinja2.render_template(body_path, **template_val)
    
                email_url = self.uri_for('taskqueue-send-email')
                taskqueue.add(url=email_url, params={
                    'to': str(secretary.admin_email),
                    'subject': messages.special_access,
                    'body': body,
                })
    
                self.add_message(messages.saving_success, 'success')
            return self.get()
        except Exception as e:
            logging.info("error in saving to datastore: %s" % e)
            self.add_message(messages.saving_error, 'danger')
            return self.get()

class AdminOrganizationSecretaryHandler(BaseHandler):
    def get_or_404(self, secretary_id):
        try:
            secretary = models.Secretary.get_by_id(long(secretary_id))
            if secretary:
                return secretary
        except ValueError:
            pass
        self.abort(404)

    def edit(self, secretary_id):
        if self.request.POST:
            secretary = self.get_or_404(secretary_id)
            delete = self.request.get('delete')
            
            try:
                if delete == 'confirmed_deletion':
                    secretary_info = models.Secretary.get_by_id(long(secretary_id))

                    #DELETE AGENCIES & OPERATORS ACCESS
                    agencies = secretary_info.get_agencies()
                    for agency in agencies:
                        operators = agency.get_operators()
                        for operator in operators:
                            operator.key.delete()
                        agency.key.delete()

                    #DELETE SECRETARY
                    secretary_info.key.delete()

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-organization")
                elif delete == 'secretary_edition':
                    #SECRETARY EDITION
                    secretary_info = models.Secretary.get_by_id(long(secretary_id))
                    name = self.request.get('secname') if self.request.get('secname') else ''
                    if secretary_info.name != name:
                        possible_repeat = models.Secretary.query(models.Secretary.name == name).get()
                        if possible_repeat is not None:
                            self.add_message(messages.nametaken, 'danger')
                            logging.info(messages.nametaken)
                            return self.redirect_to("admin-secretary-edit", secretary_id=secretary_id)                  
                    
                    secretary_info.name = name
                    secretary_info.description = self.request.get('description') if self.request.get('description') else ''
                    if secretary_info.admin_email != self.request.get('adminemail'):
                        secretary_info.admin_email = self.request.get('adminemail').lower() if self.request.get('adminemail') else ''
                        template_val = {
                            "_url": self.uri_for("landing", _full=True),
                            "support_url": self.uri_for("contact", _full=True),
                            "twitter_url": self.app.config.get('twitter_url'),
                            "facebook_url": self.app.config.get('facebook_url'),
                            "faq_url": self.uri_for("faq", _full=True)
                        }
                        body_path = "emails/special_access_invite.txt"
                        body = self.jinja2.render_template(body_path, **template_val)

                        email_url = self.uri_for('taskqueue-send-email')
                        taskqueue.add(url=email_url, params={
                            'to': str(secretary_info.admin_email),
                            'subject': messages.special_access,
                            'body': body,
                        })
                    secretary_info.admin_name = self.request.get('adminname') if self.request.get('adminname') else ''
                    secretary_info.phone = self.request.get('phone') if self.request.get('phone') else ''
                    secretary_info.address = self.request.get('address') if self.request.get('address') else ''
                    secretary_info.put()
                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-secretary-edit", secretary_id=secretary_id)
                else:
                    #AGENCY ADD                    
                    logging.info("adding a new agency")
                    name = self.request.get('agename') if self.request.get('agename') else ''
                    possible_repeat = models.Agency.query(models.Agency.name == name).get()
                    if possible_repeat is not None:
                        secretary = models.Secretary.get_by_id(long(possible_repeat.secretary_id)) 
                        self.add_message(messages.nametaken, 'danger')
                        message = ('<div>El nombre %s esta en uso por las siguientes secretarias:</div><div> - %s</div>' %(name, secretary.name))
                        self.add_message(message, 'danger')
                        logging.info(messages.nametaken)
                    else:
                        agency = models.Agency()
                        agency.secretary_id = int(secretary_id)
                        agency.name = name
                        agency.description = self.request.get('agedescription') if self.request.get('agedescription') else ''
                        agency.admin_email = self.request.get('ageadminemail').lower() if self.request.get('ageadminemail') else ''
                        agency.admin_name = self.request.get('ageadminname') if self.request.get('ageadminname') else ''
                        groups = models.GroupCategory.query(models.GroupCategory.name == self.request.get('agegroupcat'))
                        if groups:
                            for group in groups:
                                agency.group_category_id = int(group.key.id())
                                break
                        agency.put()
    
                        #SEND EMAIL NOTIFICATION TO ADMIN_EMAIL
                        template_val = {
                            "_url": self.uri_for("landing", _full=True),
                            "support_url": self.uri_for("contact", _full=True),
                            "twitter_url": self.app.config.get('twitter_url'),
                            "facebook_url": self.app.config.get('facebook_url'),
                            "faq_url": self.uri_for("faq", _full=True)
                        }
                        body_path = "emails/special_access_invite.txt"
                        body = self.jinja2.render_template(body_path, **template_val)
    
                        email_url = self.uri_for('taskqueue-send-email')
                        taskqueue.add(url=email_url, params={
                            'to': str(agency.admin_email),
                            'subject': messages.special_access,
                            'body': body,
                        })
    
                        self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-secretary-edit", secretary_id=secretary_id)

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating secretary: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("admin-secretary-edit", secretary_id=secretary_id)

        else:
            secretary = self.get_or_404(secretary_id)

        params = {
            'secretary': secretary,
            'agencies': models.Agency.query(models.Agency.secretary_id == secretary.get_id()),
            '_user': models.User.get_by_email(secretary.admin_email)
        }

        groups = models.GroupCategory.query()
        params['group_count'] = groups.count()

        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_secretary.html', **params)

class AdminOrganizationAgencyHandler(BaseHandler):
    def get_or_404(self, agency_id):
        try:
            agency = models.Agency.get_by_id(long(agency_id))
            if agency:
                return agency
        except ValueError:
            pass
        self.abort(404)

    def edit(self, agency_id):
        if self.request.POST:
            agency = self.get_or_404(agency_id)
            delete = self.request.get('delete')
            
            try:

                if delete == 'confirmed_deletion':
                    agency_info = models.Agency.get_by_id(long(agency_id))
                    
                    #DELETE OPERATORS ACCESS
                    operators = agency_info.get_operators()
                    for operator in operators:
                        operator.key.delete()

                    #DELETE AGENCY
                    agency_info.key.delete()

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-secretary-edit", secretary_id=agency_info.secretary_id)
                elif delete == 'agency_edition':
                    #AGENCY EDITION
                    agency_info = models.Agency.get_by_id(long(agency_id))
                    name = self.request.get('agename') if self.request.get('agename') else ''
                    if agency_info.name != name:
                        possible_repeat = models.Agency.query(models.Agency.name == name).get()
                        if possible_repeat is not None:
                            secretary = models.Secretary.get_by_id(long(possible_repeat.secretary_id)) 
                            self.add_message(messages.nametaken, 'danger')
                            message = ('<div>El nombre %s esta en uso por las siguientes secretarias:</div><div> - %s</div>' %(name, secretary.name))
                            self.add_message(message, 'danger')
                            logging.info(messages.nametaken)
                            return self.redirect_to("admin-agency-edit", agency_id=agency_id)
                    agency_info.name = name
                    agency_info.description = self.request.get('agedescription') if self.request.get('agedescription') else ''
                    agency_info.admin_name = self.request.get('ageadminname') if self.request.get('ageadminname') else ''
                    groups = models.GroupCategory.query(models.GroupCategory.name == self.request.get('agegroupcat'))
                    if groups:
                        for group in groups:
                            agency.group_category_id = int(group.key.id())
                            break
                    if agency_info.admin_email != self.request.get('ageadminemail'):
                        agency_info.admin_email = self.request.get('ageadminemail').lower() if self.request.get('ageadminemail') else ''
                        template_val = {
                            "_url": self.uri_for("landing", _full=True),
                            "support_url": self.uri_for("contact", _full=True),
                            "twitter_url": self.app.config.get('twitter_url'),
                            "facebook_url": self.app.config.get('facebook_url'),
                            "faq_url": self.uri_for("faq", _full=True)
                        }
                        body_path = "emails/special_access_invite.txt"
                        body = self.jinja2.render_template(body_path, **template_val)

                        email_url = self.uri_for('taskqueue-send-email')
                        taskqueue.add(url=email_url, params={
                            'to': str(agency_info.admin_email),
                            'subject': messages.special_access,
                            'body': body,
                        })


                    agency_info.put()
                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-agency-edit", agency_id=agency_id)
                else:
                    #OPERATOR ADD
                    logging.info("adding a new operator")
                    operator = models.Operator()
                    operator.agency_id = int(agency_id)
                    operator.email = self.request.get('opsadminemail').lower() if self.request.get('opsadminemail') else ''
                    operator.name = self.request.get('opsadminname') if self.request.get('opsadminname') else ''
                    operator.put()

                    #SEND EMAIL NOTIFICATION TO ADMIN_EMAIL
                    template_val = {
                        "_url": self.uri_for("landing", _full=True),
                        "support_url": self.uri_for("contact", _full=True),
                        "twitter_url": self.app.config.get('twitter_url'),
                        "facebook_url": self.app.config.get('facebook_url'),
                        "faq_url": self.uri_for("faq", _full=True)
                    }
                    body_path = "emails/special_access_invite.txt"
                    body = self.jinja2.render_template(body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url=email_url, params={
                        'to': str(operator.email),
                        'subject': messages.special_access,
                        'body': body,
                    })

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-agency-edit", agency_id=agency_id)

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating agency: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("admin-agency-edit", agency_id=agency_id)
        else:
            agency = self.get_or_404(agency_id)

        params = {
            'agency': agency,
            'operators': models.Operator.query(models.Operator.agency_id == agency.get_id()),
            '_user': models.User.get_by_email(agency.admin_email)
        }

        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_agency.html', **params)

class AdminOrganizationOperatorHandler(BaseHandler):
    def get_or_404(self, operator_id):
        try:
            operator = models.Operator.get_by_id(long(operator_id))
            if operator:
                return operator
        except ValueError:
            pass
        self.abort(404)

    def edit(self, operator_id):
        if self.request.POST:
            operator = self.get_or_404(operator_id)
            delete = self.request.get('delete')
            
            try:

                if delete == 'confirmed_deletion':
                    #DELETE REQUEST
                    operator_info = models.Operator.get_by_id(long(operator_id))
                    operator_info.key.delete()
                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-agency-edit", agency_id=operator_info.agency_id)
                elif delete == 'operator_edition':
                    #OPERATOR EDITION
                    operator_info = models.Operator.get_by_id(long(operator_id))
                    operator_info.name = self.request.get('opsadminname') if self.request.get('opsadminname') else ''
                    if operator_info.email != self.request.get('opsadminemail'):
                        operator_info.email = self.request.get('opsadminemail').lower() if self.request.get('opsadminemail') else ''
                        #SEND EMAIL NOTIFICATION TO ADMIN_EMAIL
                        template_val = {
                            "_url": self.uri_for("landing", _full=True),
                            "support_url": self.uri_for("contact", _full=True),
                            "twitter_url": self.app.config.get('twitter_url'),
                            "facebook_url": self.app.config.get('facebook_url'),
                            "faq_url": self.uri_for("faq", _full=True)
                        }
                        body_path = "emails/special_access_invite.txt"
                        body = self.jinja2.render_template(body_path, **template_val)

                        email_url = self.uri_for('taskqueue-send-email')
                        taskqueue.add(url=email_url, params={
                            'to': str(operator_info.email),
                            'subject': messages.special_access,
                            'body': body,
                        })
                    operator_info.put()

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-operator-edit", operator_id=operator_id)

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating operator: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("admin-operator-edit", operator_id=operator_id)
        else:
            operator = self.get_or_404(operator_id)

        params = {
            'operator': operator,
            '_user': models.User.get_by_email(operator.email)
        }
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_operator.html', **params)

"""

    CATEGORIES HANDLERS

"""
class AdminCategoriesHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['groups'] = models.GroupCategory.query()
        return self.render_template('admin_categories.html', **params)
    
    def post(self):
        name = self.request.get('name').strip()
        color = self.request.get('color').upper()[1:]
        groupCat = models.GroupCategory.query(models.GroupCategory.name == name).get()
        if groupCat is not None:
            agencies = groupCat.get_agencies()
            agenciesArr = [agency.name for agency in agencies]
            self.add_message(messages.nametaken, 'danger')
            message = ('<div>El nombre %s esta en uso por las siguientes dependencias:</div><div> - %s</div>' %(name,', '.join(agenciesArr)))
            self.add_message(message, 'danger')
            logging.info(messages.nametaken)
        else:
            groupCat = models.GroupCategory()
            groupCat.name = name
            groupCat.color = color
            groupCat.icon_url = "http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld= |%s" %(color)
        
            #PUSH TO CARTODB
            from google.appengine.api import urlfetch
            import urllib
            api_key = self.app.config.get('cartodb_apikey')
            cartodb_domain = self.app.config.get('cartodb_user')
            cartodb_table = self.app.config.get('cartodb_category_dict_table')
            
            #INSERT IN CARTODB DICT TABLE
            unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=INSERT INTO %s (description, name) VALUES ('%s','%s')&api_key=%s" % (cartodb_domain, cartodb_table, 'group_category', name, api_key)).encode('utf8')
            url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
            try:
                t = urlfetch.fetch(url)
                logging.info("t: %s" % t.content)
                #SELECT CARTODB_ID & ASSIGN
                cl = CartoDBAPIKey(api_key, cartodb_domain)
                response = cl.sql('SELECT cartodb_id FROM %s ORDER BY cartodb_id DESC LIMIT 1' % cartodb_table)
                groupCat.cdb_id = response['rows'][0]['cartodb_id']
            except Exception as e:
                logging.info('error in cartodb request: %s' % e)
                pass
            groupCat.put()
        
        return self.get()  

class AdminSubcategoriesHandler(BaseHandler):
    def get_or_404(self, group_id):
        try:
            group = models.GroupCategory.get_by_id(long(group_id))
            if group:
                return group
        except ValueError:
            pass
        self.abort(404)

    def edit(self, group_id):
        if self.request.POST:
            group = self.get_or_404(group_id)
            delete = self.request.get('delete')
            
            try:

                if delete == 'confirmed_deletion':
                    group_info = models.GroupCategory.get_by_id(long(group_id))
                    
                    #SHALL WE DELETE ALL REPORTS WITH CATEGORY ?

                    #DELETE SUBCATEGORIES
                    subcategories = group_info.get_subcategories()
                    for subcategory in subcategories:
                        subcategory.key.delete()

                    #DELETE GROUP CATEGORY
                    group_info.key.delete()

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-categories")
                elif delete == 'category_edition':
                    #GROUP EDITION
                    name = self.request.get('name').strip()
                    color = self.request.get('color').upper()[1:]

                    groupCat = models.GroupCategory.get_by_id(long(group_id))
                    if groupCat.name != name:
                        possible_repeat = models.GroupCategory.query(models.GroupCategory.name == name).get()
                        if possible_repeat is not None:
                            agencies = groupCat.get_agencies()
                            agenciesArr = [agency.name for agency in agencies]
                            self.add_message(messages.nametaken, 'danger')
                            message = ('<div>El nombre %s esta en uso por las siguientes dependencias:</div><div> - %s</div>' %(name,', '.join(agenciesArr)))
                            self.add_message(message, 'danger')
                            logging.info(messages.nametaken)
                            return self.redirect_to("admin-category-edit", group_id=group_id)                  
                    
                    groupCat.name = name
                    groupCat.color = color
                    groupCat.icon_url = "http://chart.apis.google.com/chart?chst=d_map_pin_letter&chld= |%s" %(color)


                    #PUSH TO CARTODB
                    from google.appengine.api import urlfetch
                    import urllib
                    api_key = self.app.config.get('cartodb_apikey')
                    cartodb_domain = self.app.config.get('cartodb_user')
                    cartodb_table = self.app.config.get('cartodb_category_dict_table')
                    if groupCat.cdb_id == -1:
                        #INSERT IN CARTODB DICT TABLE
                        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=INSERT INTO %s (description, name) VALUES ('%s','%s')&api_key=%s" % (cartodb_domain, cartodb_table, 'group_category', name, api_key)).encode('utf8')
                        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                        try:
                            t = urlfetch.fetch(url)
                            logging.info("t: %s" % t.content)
                            #SELECT CARTODB_ID & ASSIGN
                            cl = CartoDBAPIKey(api_key, cartodb_domain)
                            response = cl.sql('SELECT cartodb_id FROM %s ORDER BY cartodb_id DESC LIMIT 1' % cartodb_table)
                            groupCat.cdb_id = response['rows'][0]['cartodb_id']
                        except Exception as e:
                            logging.info('error in cartodb request: %s' % e)
                            pass
                    else:
                        #UPDATE
                        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET name = '%s' WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, name,groupCat.cdb_id,api_key)).encode('utf8')
                        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                        t = urlfetch.fetch(url)
                        logging.info("t: %s" % t.content)
                    logging.info(unquoted_url)
                    groupCat.put()

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-category-edit", group_id=group_id)
                else:
                    #SUBCATEGORY ADD
                    logging.info("adding a new subcategory")
                    group_info = models.GroupCategory.get_by_id(long(group_id))
                    name = self.request.get('subname').strip()
                    icon = self.request.get('subicon')
                    color = group_info.color
                    image_req = True if self.request.get('subimagereq') else False
                    private = True if self.request.get('subprivate') else False
                    benchmark = int(self.request.get('subbenchmark'))
                    subcategory = models.SubCategory.query(models.SubCategory.name == name).get()
                    if subcategory is not None:
                        group = models.GroupCategory.get_by_id(long(subcategory.group_category_id))
                        self.add_message(messages.nametaken, 'danger')
                        message = ('<div>El nombre %s esta en uso por el grupo:</div><div> - %s</div>' %(name, group.name))
                        self.add_message(message, 'danger')
                        logging.info(messages.nametaken)
                    else:
                        subcategory = models.SubCategory()
                        subcategory.name = name
                        subcategory.icon = icon
                        subcategory.icon_url = icon
                        # subcategory.icon_url = "http://chart.apis.google.com/chart?chst=d_map_pin_icon&chld=%s|%s" % (icon,color)
                        subcategory.requires_image = image_req
                        subcategory.benchmark = benchmark
                        subcategory.private = private
                        subcategory.group_category_id = int(group_id)
                        
                        #PUSH TO CARTODB
                        from google.appengine.api import urlfetch
                        import urllib
                        api_key = self.app.config.get('cartodb_apikey')
                        cartodb_domain = self.app.config.get('cartodb_user')
                        cartodb_table = self.app.config.get('cartodb_category_dict_table')
                        
                        #INSERT IN CARTODB DICT TABLE
                        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=INSERT INTO %s (description, name) VALUES ('%s','%s')&api_key=%s" % (cartodb_domain, cartodb_table, 'sub_category', name, api_key)).encode('utf8')
                        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                        try:
                            t = urlfetch.fetch(url)
                            logging.info("t: %s" % t.content)
                            #SELECT CARTODB_ID & ASSIGN
                            cl = CartoDBAPIKey(api_key, cartodb_domain)
                            response = cl.sql('SELECT cartodb_id FROM %s ORDER BY cartodb_id DESC LIMIT 1' % cartodb_table)
                            subcategory.cdb_id = response['rows'][0]['cartodb_id']
                        except Exception as e:
                            logging.info('error in cartodb request: %s' % e)
                            pass
                        subcategory.put()
                        self.add_message(messages.saving_success, 'success')
                    
                    return self.redirect_to("admin-category-edit", group_id=group_id)

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating category: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("admin-category-edit", group_id=group_id)
        else:
            group = self.get_or_404(group_id)

        params = {
            'group': group,
            'subcategories': group.get_subcategories()
        }

        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_subcategories.html', **params)

class AdminSubcategoriesEditHandler(BaseHandler):
    def get_or_404(self, category_id):
        try:
            category = models.SubCategory.get_by_id(long(category_id))
            if category:
                return category
        except ValueError:
            pass
        self.abort(404)

    def edit(self, category_id):
        if self.request.POST:
            group = self.get_or_404(category_id)
            delete = self.request.get('delete')
            
            try:
                if delete == 'confirmed_deletion':
                    cat_info = models.SubCategory.get_by_id(long(category_id))
                    cat_info.key.delete()

                    #SHALL WE DELETE ALL REPORTS WITH SUBCATEGORY ?

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-category-edit", group_id=cat_info.group_category_id)
                else:
                    #SUBCATEGORY UPDATE
                    subcategory = models.SubCategory.get_by_id(long(category_id))
                    group_info = models.GroupCategory.get_by_id(long(subcategory.group_category_id))
                    name = self.request.get('subname').strip()
                    icon = self.request.get('subicon')
                    image_req = True if self.request.get('subimagereq') else False
                    private = True if self.request.get('subprivate') else False
                    benchmark = int(self.request.get('subbenchmark'))

                    if subcategory.name != name:
                        possible_repeat = models.SubCategory.query(models.SubCategory.name == name).get()
                        if possible_repeat is not None:
                            group = models.GroupCategory.get_by_id(long(possible_repeat.group_category_id))
                            self.add_message(messages.nametaken, 'danger')
                            message = ('<div>El nombre %s esta en uso por el grupo:</div><div> - %s</div>' %(name, group.name))
                            self.add_message(message, 'danger')
                            logging.info(messages.nametaken)
                            return self.redirect_to("admin-subcategory-edit", category_id=category_id)
                    
                    prevPrivate = subcategory.private
                    prevName = subcategory.name
                    subcategory.name = name
                    subcategory.icon = icon
                    subcategory.icon_url = icon
                    # subcategory.icon_url = "http://chart.apis.google.com/chart?chst=d_map_pin_icon&chld=%s|%s" % (icon,group_info.color)
                    subcategory.requires_image = image_req
                    subcategory.benchmark = benchmark
                    subcategory.private = private
                    
                    #PUSH TO CARTODB
                    from google.appengine.api import urlfetch
                    import urllib
                    api_key = self.app.config.get('cartodb_apikey')
                    cartodb_domain = self.app.config.get('cartodb_user')
                    cartodb_table = self.app.config.get('cartodb_category_dict_table')
                    if subcategory.cdb_id == -1:
                        #INSERT IN CARTODB DICT TABLE
                        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=INSERT INTO %s (description, name) VALUES ('%s','%s')&api_key=%s" % (cartodb_domain, cartodb_table, 'sub_category', name, api_key)).encode('utf8')
                        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                        try:
                            t = urlfetch.fetch(url)
                            logging.info("t: %s" % t.content)
                            #SELECT CARTODB_ID & ASSIGN
                            cl = CartoDBAPIKey(api_key, cartodb_domain)
                            response = cl.sql('SELECT cartodb_id FROM %s ORDER BY cartodb_id DESC LIMIT 1' % cartodb_table)
                            subcategory.cdb_id = response['rows'][0]['cartodb_id']
                        except Exception as e:
                            logging.info('error in cartodb request: %s' % e)
                            pass
                    else:
                        #UPDATE
                        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET name = '%s' WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, name,subcategory.cdb_id,api_key)).encode('utf8')
                        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                        t = urlfetch.fetch(url)
                        logging.info("t: %s" % t.content)
                                            
                    #UPDATE CARTODB REPORTS ACCORDING TO PRIVATE VALUE
                    logging.info(prevPrivate)
                    logging.info(private)
                    logging.info(prevName)
                    logging.info(name)
                    
                    if prevPrivate != private:
                        cartodb_table = self.app.config.get('cartodb_reports_table')
                        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET pvt = %s WHERE sub_category = '%s' &api_key=%s" % (cartodb_domain, cartodb_table, private, prevName.strip(), api_key)).encode('utf8')
                        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                        try:
                            t = urlfetch.fetch(url)
                            logging.info("t: %s" % t.content)
                        except Exception as e:
                            logging.info('error in cartodb private subcategory UPDATE request: %s' % e)
                            pass
                    logging.info(unquoted_url)
                    subcategory.put()
                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-category-edit", group_id=subcategory.group_category_id)

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating category: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("admin-category-edit", category_id=category_id)
        else:
            category = self.get_or_404(category_id)

        group = models.GroupCategory.get_by_id(long(category.group_category_id))
        params = {
            'category': category,
            'group_color': '#' + group.color if group else '000000'
        }
        params['group_color'] = params['group_color'] if params['group_color'] != '#FFFFFF' else '#000000'
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_subcategory.html', **params)

class AdminBulkCategoriesHandler(BaseHandler):
    def get(self):
        
        peopleDict = {
            'FRANCISCO CIENFUEGOS MARTÍNEZ': 'ALCALDE',
            'JORGE STAHL ESCAMILLA': 'SECRETARIO DE ADMINISTRACIÓN',
            'THANIA BERENICE SAUCEDO ELIZONDO': 'DIRECTORA GENERAL DEL INSTITUTO MUNICIPAL DE LA JUVENTUD',
            'NATALIA MERCADO RODRÍGUEZ': 'DIRECTORA GENERAL  DE GOBIERNO DIGITAL Y TECNOLOGÍA',
            'ALBERTO BARRERA CANTÚ': 'SECRETARIO DE CONTROL Y  SUSTENTABILIDAD URBANA',
            'MARIA DE JESÚS AGUIRRE MALDONADO': 'CONSEJERA MUNICIPAL',
            'OLIVERIO TIJERINA SEPÚLVEDA': 'SECRETARIO DE SERVICIOS PÚBLICOS',
            'ADRIÁN FERNÁNDEZ GARZA': 'JEFE DE LA OFICINA EJECUTIVA DE LA PRESIDENCIA MUNICIPAL',
            'JOSÉ SALVADOR TREVIÑO FLORES': 'CONTRALOR',
            'JUAN FRANCISCO LIVAS CANTÚ': 'SECRETARIO DE DESARROLLO ECONÓMICO',
            'ALEJANDRA LARA MAIZ': 'DIRECTORA GENERAL DEL SISTEMA DIF',
            'CLARITZA ESTEFANÍA DUARTE LUGO': 'DIRECTORA GENERAL DEL INSTITUTO DE LA MUJER',
            'RICARDO GARZA VILLARREAL': 'SECRETARÍA DE FINANZAS Y TESORERÍA MUNICIPAL',
            'FELIPE DE JESÚS GALLO GUTIÉRREZ': 'SECRETARIO DE SEGURIDAD PÚBLICA Y TRÁNSITO',
            'ARTURO ALEJANDRO CANTÚ GONZÁLEZ': 'DIRECTOR GENERAL DE RELACIONES PÚBLICAS',
            'EPIGMENIO GARZA VILLARREAL': 'SECRETARIO DEL AYUNTAMIENTO',
            'LORENA DE LA GARZA VENECIA': 'DIRECTORA GENERAL DE COMUNICACIÓN SOCIAL',
            'MÓNICA AGREDANO RAMÍREZ': 'CONSEJERA DE MEDIOS DE COMUNICACIÓN',
            'JUAN RAMÓN PALACIOS CHAPA': 'SECRETARIO DE DESARROLLO SOCIAL',
            'HÉCTOR MORALES RIVERA': 'SECRETARIO DE OBRAS PÚBLICAS',
            'GERARDO SAÚL PALACIOS PÁMANES': 'SECRETARIO DE PREVENCIÓN SOCIAL'
        }

        try:                 
#             import csv, json
#             from google.appengine.api import urlfetch
#             urlfetch.set_default_fetch_deadline(45)
#             url = self.app.config.get('reports_export_url')
#             result = urlfetch.fetch(url)
#             if result.status_code == 200:
#                 data = json.loads(result.content)                
#                 writer = csv.writer(self.response.out)
#                 writer.writerow(["rating", "via", "sub_category", "contact_info", "urgent", "req_deletion", "address_lon", "terminated", "folio", "user_id", "title", "cdb_id", "group_category", "when", "address_lat", "status", "updated", "address_from", "description", "created", "follows", "emailed_72", "image_url"])
#                 for item in data['items']:
#                     writer.writerow([ item['rating'], item['via'], item['sub_category'].encode('utf8'), item['contact_info'].encode('utf8'), item['urgent'], item['req_deletion'], item['address_lon'], item['terminated'], item['folio'], item['user_id'], item['title'].encode('utf8'), item['cdb_id'], item['group_category'].encode('utf8'), item['when'], item['address_lat'], item['status'], item['updated'], item['address_from'].encode('utf8'), item['description'].encode('utf8'), item['created'], item['follows'], item['emailed_72'], str(item['image_url'])  ])
#                         
#             self.response.headers['Content-Type'] = 'application/csv'
#             self.response.headers['Content-Disposition'] = 'attachment; filename=export.csv'
#             writer = csv.writer(self.response.out)
            
            ''' 
            import csv, json
            from google.appengine.api import urlfetch
            urlfetch.set_default_fetch_deadline(45)
            url = self.app.config.get('users_export_url')
            result = urlfetch.fetch(url)
            if result.status_code == 200:
                data = json.loads(result.content)                
                writer = csv.writer(self.response.out)
                writer.writerow(["name", "credibility", "created_at", "address", "phone", "last_login", "birth", "gender", "image_url", "identifier", "email"])
                for item in data['items']:
                    logging.info(item)
                    writer.writerow([ item['name'].encode('utf8'), item['credibility'], item['created_at'], item['address'].replace(',',' ').encode('utf8'), item['phone'], item['last_login'], item['birth'], item['gender'], item['image_url'], item['identifier'], item['email'] ])
                        
            self.response.headers['Content-Type'] = 'application/csv'
            self.response.headers['Content-Disposition'] = 'attachment; filename=export.csv'
            writer = csv.writer(self.response.out)            
            '''
            '''
            reports = models.Report.query(models.Report.status == 'solved')
            ids = [5833671273611264, 5874719752454144, 6012377212387328, 6089252966236160, 6356598976937984, 6396621227032576, 6466823809662976, 6631555267035136]
            reportList = []
            for id in ids:
                reportList.append(ndb.Key(models.Report, id))
            reports = ndb.get_multi(reportList)
            url = self.uri_for('admin-bulk')
            from google.appengine.api import urlfetch
            import urllib
            api_key = self.app.config.get('cartodb_apikey')
            cartodb_domain = self.app.config.get('cartodb_user')
            cartodb_table = self.app.config.get('cartodb_reports_table')
            for report in reports:
                taskqueue.add(url=url, target = 'devdb', params={
                    'terminated': report.terminated.strftime("%Y-%m-%d %H:%M:%S"),
                    'cdb_id': report.cdb_id,
                })
                unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET terminated = '%s' WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, report.terminated, report.cdb_id, api_key)).encode('utf8')
                url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
                try:
                    t = urlfetch.fetch(url)
                    logging.info("t: %s" % t.content)
                except Exception as e:
                    logging.info('error in cartodb UPDATE request: %s' % e)
                    pass            
    
            reports = models.Report.query()     
            mod_reports=[]
            for report_info in reports:
                if report_info.status == 'solved':
                    logs = models.LogChange.query(models.LogChange.report_id == report_info.key.id())
                    for log in logs:
                        if log.title == 'Ha marcado este reporte como resuelto.':
                            report_info.terminated = log.created
                            mod_reports.append(report_info)
                elif report_info.status == 'failed': 
                    logs = models.LogChange.query(models.LogChange.report_id == report_info.key.id())
                    for log in logs:
                        if log.title == 'Ha marcado este reporte como fallo.':
                            report_info.terminated = log.created
                            mod_reports.append(report_info)
                elif report_info.status == 'archived':
                    logs = models.LogChange.query(models.LogChange.report_id == report_info.key.id())
                    for log in logs:
                        if log.title == "Ha archivado este reporte.":
                            report_info.terminated = log.created
                            mod_reports.append(report_info)
                        
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Done with bulk operation')
            '''

        except Exception as e:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.write('Bulk error: %s' %e)
    '''
    @taskqueue_method
    def post(self):
        from google.appengine.api import urlfetch
        import urllib
        cdb_id = self.request.get("cdb_id")
        terminated = self.request.get("terminated")        
        api_key = self.app.config.get('cartodb_apikey')
        cartodb_domain = self.app.config.get('cartodb_user')
        cartodb_table = self.app.config.get('cartodb_reports_table')
        unquoted_url = ("https://%s.cartodb.com/api/v2/sql?q=UPDATE %s SET terminated = '%s' WHERE cartodb_id = %s &api_key=%s" % (cartodb_domain, cartodb_table, terminated, cdb_id, api_key)).encode('utf8')
        url = urllib.quote(unquoted_url, safe='~@$&()*!+=:;,.?/\'')
        try:
            t = urlfetch.fetch(url)
            logging.info("t: %s" % t.content)
        except Exception as e:
            logging.info('error in cartodb UPDATE request: %s' % e)
            pass
    '''