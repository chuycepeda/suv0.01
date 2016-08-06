# -*- coding: utf-8 -*-
import webapp2, json
from webapp2_extras.i18n import gettext as _
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb, blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import ndb
from google.appengine.api import taskqueue
from google.appengine.api import users as g_users #https://cloud.google.com/appengine/docs/python/refdocs/modules/google/appengine/api/users#get_current_user
from google.appengine.api import urlfetch
import urllib
import logging
from collections import OrderedDict, Counter
from wtforms import fields  
from datetime import datetime, date, time, timedelta
from bp_includes import forms, models, handlers, messages
from bp_includes.lib.cartodb import CartoDBAPIKey, CartoDBException
from bp_includes.lib.decorators import taskqueue_method
from bp_includes.lib.basehandler import BaseHandler


class AdminBrandHandler(BaseHandler):
    """
    Handler to show the map page
    """
    def get(self):
        """ Returns a simple HTML form for branding setup """
        params = {}

        brand = models.Brand.query().get()

        if brand is not None:
            params['app_name'] = self.app.config.get('app_name') if brand.app_name == '' else brand.app_name 
            params['city_name'] = self.app.config.get('city_name') if brand.city_name == '' else brand.city_name 
            params['city_slogan'] = self.app.config.get('city_slogan') if brand.city_slogan == '' else brand.city_slogan 
            params['city_splash'] = self.app.config.get('city_splash') if brand.city_splash == '' else brand.city_splash 
            params['city_splash_light'] = self.app.config.get('city_splash_light') if brand.city_splash_light == '' else brand.city_splash_light
            params['city_splash_secondary'] = self.app.config.get('city_splash_secondary') if brand.city_splash_secondary == '' else brand.city_splash_secondary 
            params['city_splash_secondary_light'] = self.app.config.get('city_splash_secondary_light') if brand.city_splash_secondary_light == '' else brand.city_splash_secondary_light 
            params['brand_logo'] = self.app.config.get('brand_logo') if brand.brand_logo == '' else brand.brand_logo 
            params['brand_favicon'] = self.app.config.get('brand_favicon') if brand.brand_favicon == '' else brand.brand_favicon 
            params['brand_color'] = self.app.config.get('brand_color') if brand.brand_color == '' else brand.brand_color 
            params['brand_secondary_color'] = self.app.config.get('brand_secondary_color') if brand.brand_secondary_color == '' else brand.brand_secondary_color 
            params['brand_tertiary_color'] = self.app.config.get('brand_tertiary_color') if brand.brand_tertiary_color == '' else brand.brand_tertiary_color 

        else:
            params['app_name'] = self.app.config.get('app_name')
            params['city_name'] = self.app.config.get('city_name')
            params['city_slogan'] = self.app.config.get('city_slogan')
            params['city_splash'] = self.app.config.get('city_splash')
            params['city_splash_light'] = self.app.config.get('city_splash_light')
            params['city_splash_secondary'] = self.app.config.get('city_splash_secondary')
            params['city_splash_secondary_light'] = self.app.config.get('city_splash_secondary_light')
            params['brand_logo'] = self.app.config.get('brand_logo')
            params['brand_favicon'] = self.app.config.get('brand_favicon')
            params['brand_color'] = self.app.config.get('brand_color')
            params['brand_secondary_color'] = self.app.config.get('brand_secondary_color')
            params['brand_tertiary_color'] = self.app.config.get('brand_tertiary_color')

        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('admin_brand.html', **params)


    def post(self):
        """ Saves a simple HTML form for branding setup """
        try:
            brand = models.Brand.query().get()
            if brand is None:
                brand = models.Brand()

            source = self.request.get('source')
            brand.app_name = self.request.get('app_name') if self.request.get('app_name') != '' else self.app.config.get('app_name')
            brand.city_name = self.request.get('city_name') if self.request.get('city_name') != '' else self.app.config.get('city_name')
            brand.city_slogan = self.request.get('city_slogan') if self.request.get('city_slogan') != '' else self.app.config.get('city_slogan')
            brand.city_splash = self.request.get('city_splash') if self.request.get('city_splash') != '' else self.app.config.get('city_splash')
            brand.city_splash_light = self.request.get('city_splash_light') if self.request.get('city_splash_light') != '' else self.app.config.get('city_splash_light')
            brand.city_splash_secondary = self.request.get('city_splash_secondary') if self.request.get('city_splash_secondary') != '' else self.app.config.get('city_splash_secondary')
            brand.city_splash_secondary_light = self.request.get('city_splash_secondary_light') if self.request.get('city_splash_secondary_light') != '' else self.app.config.get('city_splash_secondary_light')
            brand.brand_logo = self.request.get('brand_logo') if self.request.get('brand_logo') != '' else self.app.config.get('brand_logo')
            brand.brand_favicon = self.request.get('brand_favicon') if self.request.get('brand_favicon') != '' else self.app.config.get('brand_favicon')
            brand.brand_color = self.request.get('brand_color') if self.request.get('brand_color') != '' else self.app.config.get('brand_color')
            brand.brand_secondary_color = self.request.get('brand_secondary_color') if self.request.get('brand_secondary_color') != '' else self.app.config.get('brand_secondary_color')
            brand.brand_tertiary_color = self.request.get('brand_tertiary_color') if self.request.get('brand_tertiary_color') != '' else self.app.config.get('brand_tertiary_color')
            brand.put()
            if source == 'AJAX':
                a = {'response': messages.saving_success}
                self.response.headers['Content-Type'] = 'application/json'
                self.response.write(json.dumps(a))  
            else:
                self.add_message(messages.saving_success, 'success')
                return self.get()
        except Exception as e:
            logging.info('error in branding post: %s' % e)
            self.add_message(messages.saving_error, 'danger')
            return self.get()


"""

    CATEGORIES HANDLERS

"""
class AdminCategoriesHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['groups'] = models.GroupCategory.query()
        params['group_color'] = self.app.config.get('brand_secondary_color')
        return self.render_template('reports/admin_categories.html', **params)
    
    def post(self):
        name = self.request.get('name').strip()
        color = self.request.get('color').upper()[1:]
        icon_url = self.request.get('subicon')
        groupCat = models.GroupCategory.query(models.GroupCategory.name == name).get()
        if groupCat is not None:
            agencies = groupCat.get_agencies()
            agenciesArr = [agency.name for agency in agencies]
            self.add_message(messages.nametaken, 'danger')
            message = ('<div>El nombre %s esta en uso por las siguientes {{second_level_mins_plural}}:</div><div> - %s</div>' %(name,', '.join(agenciesArr)))
            self.add_message(message, 'danger')
            logging.info(messages.nametaken)
        else:
            groupCat = models.GroupCategory()
            groupCat.name = name
            groupCat.color = color
            groupCat.icon_url = icon_url
        
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
                    icon_url = self.request.get('group_subicon')

                    groupCat = models.GroupCategory.get_by_id(long(group_id))
                    if groupCat.name != name:
                        possible_repeat = models.GroupCategory.query(models.GroupCategory.name == name).get()
                        if possible_repeat is not None and int(possible_repeat.key.id()) != int(group_id):
                            agencies = groupCat.get_agencies()
                            agenciesArr = [agency.name for agency in agencies]
                            self.add_message(messages.nametaken, 'danger')
                            message = ('<div>El nombre %s esta en uso por las siguientes {{second_level_mins_plural}}:</div><div> - %s</div>' %(name,', '.join(agenciesArr)))
                            self.add_message(message, 'danger')
                            logging.info(messages.nametaken)
                            return self.redirect_to("admin-category-edit", group_id=group_id)                  
                    
                    groupCat.name = name
                    groupCat.color = color
                    groupCat.icon_url = icon_url

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
                    return self.redirect_to("admin-categories")
                else:
                    #SUBCATEGORY ADD
                    logging.info("adding a new subcategory")
                    group_info = models.GroupCategory.get_by_id(long(group_id))
                    name = self.request.get('subname').strip()
                    description = self.request.get('subdescription').strip()
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
                        subcategory.description = description
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
        return self.render_template('reports/admin_subcategories.html', **params)

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
                    description = self.request.get('subdescription').strip()
                    icon = self.request.get('subicon')
                    image_req = True if self.request.get('subimagereq') else False
                    private = True if self.request.get('subprivate') else False
                    benchmark = int(self.request.get('subbenchmark'))

                    if subcategory.name != name:
                        possible_repeat = models.SubCategory.query(models.SubCategory.name == name).get()
                        if possible_repeat is not None and int(possible_repeat.key.id()) != int(category_id):
                            group = models.GroupCategory.get_by_id(long(possible_repeat.group_category_id))
                            self.add_message(messages.nametaken, 'danger')
                            message = ('<div>El nombre %s esta en uso por el grupo:</div><div> - %s</div>' %(name, group.name))
                            self.add_message(message, 'danger')
                            logging.info(messages.nametaken)
                            return self.redirect_to("admin-subcategory-edit", category_id=category_id)
                    
                    prevPrivate = subcategory.private
                    prevName = subcategory.name
                    subcategory.name = name
                    subcategory.description = description
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
        return self.render_template('reports/admin_subcategory.html', **params)


"""

    TOPICS HANDLERS

"""
class AdminTopicsHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['topics'] = models.Topic.query()
        params['group_color'] = self.app.config.get('brand_secondary_color')
        return self.render_template('petitions/admin_topics.html', **params)
    
    def post(self):
        name = self.request.get('name').strip()
        color = self.request.get('color').upper()[1:]
        icon_url = self.request.get('subicon')
        requires_image = True if self.request.get('subimagereq') else False
        benchmark = int(self.request.get('subbenchmark'))
        trigger = int(self.request.get('subtrigger'))

        topic = models.Topic.query(models.Topic.name == name).get()
        if topic is not None:
            self.add_message(messages.nametaken, 'danger')
        else:
            topic = models.Topic()
            topic.name = name
            topic.color = color
            topic.icon_url = icon_url
            topic.requires_image = requires_image
            topic.benchmark = benchmark
            topic.trigger = trigger
            topic.put()
            self.add_message(messages.saving_success, 'success')
        
        return self.get()  

class AdminTopicEditHandler(BaseHandler):
    def get_or_404(self, topic_id):
        try:
            topic = models.Topic.get_by_id(long(topic_id))
            if topic:
                return topic
        except ValueError:
            pass
        self.abort(404)

    def edit(self, topic_id):
        if self.request.POST:
            topic = self.get_or_404(topic_id)
            delete = self.request.get('delete')
            
            try:

                if delete == 'confirmed_deletion':
                    #DELETE TOPIC CATEGORY
                    topic.key.delete()

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-topics")
                elif delete == 'category_edition':
                    #TOPIC EDITION
                    name = self.request.get('name').strip()
                    color = self.request.get('color').upper()[1:]
                    icon_url = self.request.get('subicon')
                    requires_image = True if self.request.get('subimagereq') else False
                    benchmark = int(self.request.get('subbenchmark'))
                    trigger = int(self.request.get('subtrigger'))

                    _topic = models.Topic.query(models.Topic.name == name).get()
                    if _topic is not None and int(_topic.key.id()) != int(topic_id):
                        self.add_message(messages.nametaken, 'danger')
                    else:
                        topic.name = name
                        topic.color = color
                        topic.icon_url = icon_url
                        topic.requires_image = requires_image
                        topic.benchmark = benchmark
                        topic.trigger = trigger
                        topic.put()
                        self.add_message(messages.saving_success, 'success')

                    return self.redirect_to("admin-topics")
                
            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating topic: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("admin-topic-edit", topic_id=topic_id)
        else:
            topic = self.get_or_404(topic_id)

        params = {
            'topic': topic
        }

        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('petitions/admin_topic_edit.html', **params)


"""

    AREAS HANDLERS

"""
class AdminAreasHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['areas'] = models.Area.query()
        params['group_color'] = self.app.config.get('brand_secondary_color')
        return self.render_template('transparency/admin_areas.html', **params)
    
    def post(self):
        name = self.request.get('name').strip()
        color = self.request.get('color').upper()[1:]
        icon_url = self.request.get('subicon')
        area = models.Area.query(models.Area.name == name).get()
        if area is not None:
            self.add_message(messages.nametaken, 'danger')
        else:
            area = models.Area()
            area.name = name
            area.color = color
            area.icon_url = icon_url
            area.put()
            self.add_message(messages.saving_success, 'success')
        
        return self.get()  

class AdminAreaEditHandler(BaseHandler):
    def get_or_404(self, area_id):
        try:
            area = models.Area.get_by_id(long(area_id))
            if area:
                return area
        except ValueError:
            pass
        self.abort(404)

    def edit(self, area_id):
        if self.request.POST:
            area = self.get_or_404(area_id)
            delete = self.request.get('delete')
            
            try:

                if delete == 'confirmed_deletion':
                    #DELETE AREA CATEGORY
                    area.key.delete()

                    self.add_message(messages.saving_success, 'success')
                    return self.redirect_to("admin-areas")
                elif delete == 'category_edition':
                    #AREA EDITION
                    name = self.request.get('name').strip()
                    color = self.request.get('color').upper()[1:]
                    icon_url = self.request.get('subicon')

                    _area = models.Area.query(models.Area.name == name).get()
                    if _area is not None and int(_area.key.id()) != int(area_id):
                        self.add_message(messages.nametaken, 'danger')
                    else:
                        area.name = name
                        area.color = color
                        area.icon_url = icon_url
                        area.put()
                        self.add_message(messages.saving_success, 'success')

                    return self.redirect_to("admin-areas")
                
            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating area: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("admin-area-edit", area_id=area_id)
        else:
            area = self.get_or_404(area_id)

        params = {
            'area': area
        }

        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('transparency/admin_area_edit.html', **params)


"""

    REPORT HANDLERS

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

class AdminReportsHandler(BaseHandler):
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
            return self.uri_for('admin-reports', **params)



        self.view.pager_url = pager_url
        self.view.q = q

        params['statusval'] = get_status(status) if status else ""
        params['ticketval'] = ticket if ticket else ""
        params['folioval'] = folio if folio else ""
        params['catGroup'] = groupCat if groupCat else ""
        params['reports'] = reports
        params['count'] = count
        params['cats'] = sorted(names) if names else names
        params['inbox'] = 'admin-reports'
        params['nickname'] = g_users.get_current_user().email().lower()

        return self.render_template('reports/admin_inbox.html', **params)

class AdminMapHandler(BaseHandler):
    """
    Handler to show the map page
    """
    def get(self):
        """ Returns a simple HTML form for landing """
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')  
        params['right_sidenav_msg'] = self.app.config.get('right_sidenav_msg')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['has_cic'] = self.app.config.get('has_cic')
        params['cartodb_cic_user'] = self.app.config.get('cartodb_cic_user')
        params['cartodb_cic_reports_table'] = self.app.config.get('cartodb_cic_reports_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        params['cartodb_markers_url'] = self.uri_for("landing", _full=True)+"default/materialize/images/markers/"
        return self.render_template('reports/admin_map.html', **params)

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
                            "brand_logo": self.app.config.get('brand_logo'),
                            "brand_color": self.app.config.get('brand_color'),
                            "brand_secondary_color": self.app.config.get('brand_secondary_color'),
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

                        report_info = self.get_or_404(report_id)

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
        params['atts'] = models.Attachment.query(models.Attachment.report_id == report_info.key.id())
        params['atts'] = params['atts'].order(-models.Attachment.created)
        params['has_atts'] = True if params['atts'].count() > 0 else False
        params['nickname'] = g_users.get_current_user().email().lower()
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        return self.render_template('reports/admin_report_edit.html', **params)


"""

    PETITIONS HANDLERS

"""
class AdminPetitionsHandler(BaseHandler):
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
            return self.uri_for('admin-reports', **params)



        self.view.pager_url = pager_url
        self.view.q = q

        params['statusval'] = get_status(status) if status else ""
        params['ticketval'] = ticket if ticket else ""
        params['folioval'] = folio if folio else ""
        params['catGroup'] = groupCat if groupCat else ""
        params['reports'] = reports
        params['count'] = count
        params['cats'] = sorted(names) if names else names
        params['inbox'] = 'admin-reports'
        params['nickname'] = g_users.get_current_user().email().lower()

        return self.render_template('petitions/admin_petitions.html', **params)

class AdminPetitionsEditHandler(BaseHandler):
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
                            "brand_logo": self.app.config.get('brand_logo'),
                            "brand_color": self.app.config.get('brand_color'),
                            "brand_secondary_color": self.app.config.get('brand_secondary_color'),
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
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_category_dict_table'] = self.app.config.get('cartodb_category_dict_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        return self.render_template('reports/admin_report_edit.html', **params)


"""

    INITIATIVES HANDLERS

"""
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

class AdminInitiativesHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['initiatives'] = models.Initiative.query()
        params['group_color'] = self.app.config.get('brand_secondary_color')
        return self.render_template('transparency/admin_initiatives.html', **params)
    
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

class AdminInitiativeEditHandler(BaseHandler):
    def get_or_404(self, init_id):
        try:
            initiative = models.Initiative.get_by_id(long(init_id))
            if initiative:
                return initiative
        except ValueError:
            pass
        self.abort(404)

    def edit(self, init_id):
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
                            return self.redirect_to("admin-initiative-edit", init_id=init_id) 
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
                            upload_url = blobstore.create_upload_url('/admin/initiatives/image/upload/%s/' %(initiative.key.id()))
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
                                return self.redirect_to("admin-initiative-edit", init_id=init_id)
                                
                            else:
                                message = _(messages.attach_error)
                                self.add_message(message, 'danger')            
                                return self.redirect_to("admin-initiative-edit", init_id=init_id)
                                                  
                        else:
                            message = _(messages.saving_success)
                            self.add_message(message, 'success')
                            return self.redirect_to("admin-initiative-edit", init_id=init_id)
                            


                        self.add_message(messages.saving_success, 'success')

                return self.redirect_to("admin-initiatives")
                
            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating initiative: %s ' % e)
                self.add_message(messages.saving_error, 'danger')
                return self.redirect_to("admin-initiative-edit", init_id=init_id)
        else:
            initiative = self.get_or_404(init_id)

        params = {
            'initiative': initiative
        }

        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('transparency/admin_initiative_edit.html', **params)

class AdminInitiativeImageUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
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

"""
    GEOM
"""
class AdminGeomHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
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

        return self.render_template('transparency/admin_geom.html', **params)
    
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

class AdminGeomEditHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = g_users.get_current_user().email().lower()
        params['zoom'] = self.app.config.get('map_zoom')
        params['zoom_mobile'] = self.app.config.get('map_zoom_mobile')
        params['lat'] = self.app.config.get('map_center_lat')
        params['lng'] = self.app.config.get('map_center_lng')
        params['cartodb_user'] = self.app.config.get('cartodb_user')
        params['cartodb_pois_table'] = self.app.config.get('cartodb_pois_table')
        params['cartodb_reports_table'] = self.app.config.get('cartodb_reports_table')
        params['cartodb_polygon_table'] = self.app.config.get('cartodb_polygon_table')
        params['cartodb_polygon_name'] = self.app.config.get('cartodb_polygon_name')
        return self.render_template('transparency/admin_geom_edit.html', **params)
    
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


"""

    ORGANIZATION HANDLERS

"""
class AdminOrganizationHandler(BaseHandler):
    def get(self):
        params = {}
        params['secretaries']  = models.Secretary.query()
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('organization/admin_organization.html', **params)

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
                    "brand_logo": self.app.config.get('brand_logo'),
                    "brand_color": self.app.config.get('brand_color'),
                    "brand_secondary_color": self.app.config.get('brand_secondary_color'),
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
                            "brand_logo": self.app.config.get('brand_logo'),
                            "brand_color": self.app.config.get('brand_color'),
                            "brand_secondary_color": self.app.config.get('brand_secondary_color'),
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
                            "brand_logo": self.app.config.get('brand_logo'),
                            "brand_color": self.app.config.get('brand_color'),
                            "brand_secondary_color": self.app.config.get('brand_secondary_color'),
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
        return self.render_template('organization/admin_secretary.html', **params)

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
                            "brand_logo": self.app.config.get('brand_logo'),
                            "brand_color": self.app.config.get('brand_color'),
                            "brand_secondary_color": self.app.config.get('brand_secondary_color'),
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
                        "brand_logo": self.app.config.get('brand_logo'),
                        "brand_color": self.app.config.get('brand_color'),
                        "brand_secondary_color": self.app.config.get('brand_secondary_color'),
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
        return self.render_template('organization/admin_agency.html', **params)

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
                            "brand_logo": self.app.config.get('brand_logo'),
                            "brand_color": self.app.config.get('brand_color'),
                            "brand_secondary_color": self.app.config.get('brand_secondary_color'),
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
        return self.render_template('organization/admin_operator.html', **params)



"""

    CALL CENTER HANDLERS

"""
class AdminCallCenterHandler(BaseHandler):
    def get(self):
        params = {}
        params['operators']  = models.CallCenterOperator.query()
        params['nickname'] = g_users.get_current_user().email().lower()
        return self.render_template('organization/admin_callcenter.html', **params)

    def post(self):
        try:
            #SECRETARY ADD
            logging.info("adding a new callcenter operator")
            operator = models.CallCenterOperator()
            operator.email = self.request.get('adminemail') if self.request.get('adminemail') else ''
            operator.name = self.request.get('adminname') if self.request.get('adminname') else ''
            operator.role = self.request.get('adminrole') if self.request.get('adminrole') else 'callcenter'
            operator.put()

            #SEND EMAIL NOTIFICATION TO ADMIN_EMAIL
            template_val = {
                "_url": self.uri_for("landing", _full=True),
                "brand_logo": self.app.config.get('brand_logo'),
                "brand_color": self.app.config.get('brand_color'),
                "brand_secondary_color": self.app.config.get('brand_secondary_color'),
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
                    operator_info.name = self.request.get('opsadminname') if self.request.get('opsadminname') else operator_info.name
                    operator_info.role = self.request.get('opsadminrole') if self.request.get('opsadminrole') else operator_info.role
                    if operator_info.email != self.request.get('opsadminemail') and self.request.get('opsadminemail') != '':
                        operator_info.email = self.request.get('opsadminemail')
                        #SEND EMAIL NOTIFICATION TO ADMIN_EMAIL
                        template_val = {
                            "_url": self.uri_for("landing", _full=True),
                            "brand_logo": self.app.config.get('brand_logo'),
                            "brand_color": self.app.config.get('brand_color'),
                            "brand_secondary_color": self.app.config.get('brand_secondary_color'),
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
        return self.render_template('organization/admin_callcenter_operator.html', **params)
