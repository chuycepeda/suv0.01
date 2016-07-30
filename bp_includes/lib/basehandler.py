# *-* coding: UTF-8 *-*

# standard library imports
import logging
import re
import pytz
import os
# related third party imports
import webapp2
from webapp2_extras import jinja2
from webapp2_extras import auth
from webapp2_extras import sessions
# local application/library specific imports
from bp_includes import models
from bp_includes.lib import utils, i18n, jinja_bootstrap
from babel import Locale
import logging
from google.appengine.api import users as g_users #https://cloud.google.com/appengine/docs/python/refdocs/modules/google/appengine/api/users#get_current_user

class ViewClass:
    """
        ViewClass to insert variables into the template.

        ViewClass is used in BaseHandler to promote variables automatically that can be used
        in jinja2 templates.
        Use case in a BaseHandler Class:
            self.view.var1 = "hello"
            self.view.array = [1, 2, 3]
            self.view.dict = dict(a="abc", b="bcd")
        Can be accessed in the template by just using the variables like {{var1}} or {{dict.b}}
    """
    pass


class BaseHandler(webapp2.RequestHandler):
    """
        BaseHandler for all requests

        Holds the auth and session properties so they
        are reachable for all requests
    """

    def __init__(self, request, response):
        """ Override the initialiser in order to set the language.
        """
        self.initialize(request, response)
        self.locale = i18n.set_locale(self, request)
        self.view = ViewClass()

    def dispatch(self):
        """
            Get a session store for this request.
        """
        self.session_store = sessions.get_store(request=self.request)

        try:
            # csrf protection
            if self.request.method == "POST" and not self.request.path.startswith('/taskqueue') and not self.request.path.startswith('/mbapi'):
                token = self.session.get('_csrf_token')
                if not token or (token != self.request.get('_csrf_token') and
                         token != self.request.headers.get('_csrf_token')):
                    self.abort(403)

            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def user_model(self):
        """Returns the implementation of the user model.

        Keep consistency when config['webapp2_extras.auth']['user_model'] is set.
        """
        return self.auth.store.user_model

    @webapp2.cached_property
    def auth(self):
        return auth.get_auth()

    @webapp2.cached_property
    def session_store(self):
        return sessions.get_store(request=self.request)

    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()

    @webapp2.cached_property
    def get_theme(self):
        return os.environ['theme']

    @webapp2.cached_property
    def messages(self):
        return self.session.get_flashes(key='_messages')

    def add_message(self, message, level=None):
        self.session.add_flash(message, level, key='_messages')

    @webapp2.cached_property
    def auth_config(self):
        """
              Dict to hold urls for login/logout
        """
        return {
            'login_url': self.uri_for('login'),
            'logout_url': self.uri_for('logout')
        }

    @webapp2.cached_property
    def language(self):
        return str(Locale.parse(self.locale).language)

    @webapp2.cached_property
    def has_reports(self):
        return self.app.config.get('has_reports')

    @webapp2.cached_property
    def has_petitions(self):
        return self.app.config.get('has_petitions')

    @webapp2.cached_property
    def has_transparency(self):
        return self.app.config.get('has_transparency')

    @webapp2.cached_property
    def has_social_media(self):
        return self.app.config.get('has_social_media')

    @webapp2.cached_property
    def has_cic(self):
        return self.app.config.get('has_cic')

    @webapp2.cached_property
    def google_clientID(self):
        return self.app.config.get('google_clientID')

    @webapp2.cached_property
    def facebook_appID(self):
        return self.app.config.get('facebook_appID')

    @webapp2.cached_property
    def twitter_appID(self):
        return self.app.config.get('twitter_appID')

    @webapp2.cached_property
    def gmaps_apikey(self):
        return self.app.config.get('gmaps_apikey')

    @webapp2.cached_property
    def user(self):

        return self.auth.get_user_by_session()

    @webapp2.cached_property
    def user_id(self):
        return str(self.user['user_id']) if self.user else None

    @webapp2.cached_property
    def user_is_admin(self):
        if self.user:
            return g_users.is_current_user_admin()
        return False

    @webapp2.cached_property
    def user_is_secretary(self):
        if self.user:
            user_info = self.user_model.get_by_id(long(self.user_id))
            return user_info.is_secretary()
        return False

    @webapp2.cached_property
    def user_is_agent(self):
        if self.user:
            user_info = self.user_model.get_by_id(long(self.user_id))
            return user_info.is_agent()
        return False

    @webapp2.cached_property
    def user_is_operator(self):
        if self.user:
            user_info = self.user_model.get_by_id(long(self.user_id))
            return user_info.is_operator()
        return False

    @webapp2.cached_property
    def user_is_callcenter(self):
        if self.user:
            user_info = self.user_model.get_by_id(long(self.user_id))
            return user_info.is_callcenter()
        return False

    @webapp2.cached_property
    def user_callcenter_role(self):
        if self.user:
            user_info = self.user_model.get_by_id(long(self.user_id))
            return user_info.has_callcenter_role()
        return False

    @webapp2.cached_property
    def user_key(self):
        if self.user:
            user_info = self.user_model.get_by_id(long(self.user_id))
            return user_info.key
        return None

    @webapp2.cached_property
    def username(self):
        if self.user:
            try:
                user_info = self.user_model.get_by_id(long(self.user_id))
                if not user_info.activated:
                    self.auth.unset_session()
                    self.redirect_to('landing')
                else:
                    return str(user_info.username)
            except AttributeError, e:
                # avoid AttributeError when the session was delete from the server
                logging.error(e)
                self.auth.unset_session()
                self.redirect_to('landing')
        return None

    @webapp2.cached_property
    def name(self):
        if self.user:
            try:
                user_info = self.user_model.get_by_id(long(self.user_id))
                if not user_info.activated:
                    self.auth.unset_session()
                    self.redirect_to('landing')
                else:
                    return user_info.name
            except AttributeError, e:
                # avoid AttributeError when the session was delete from the server
                logging.error(e)
                self.auth.unset_session()
                self.redirect_to('landing')
        return None

    @webapp2.cached_property
    def email(self):
        if self.user:
            try:
                user_info = self.user_model.get_by_id(long(self.user_id))
                return user_info.email
            except AttributeError, e:
                # avoid AttributeError when the session was delete from the server
                logging.error(e)
                self.auth.unset_session()
                self.redirect_to('landing')
        return None

    @webapp2.cached_property
    def path_for_language(self):
        """
        Get the current path + query_string without language parameter (hl=something)
        Useful to put it on a template to concatenate with '&hl=NEW_LOCALE'
        Example: .../?hl=en_US
        """
        path_lang = re.sub(r'(^hl=(\w{5})\&*)|(\&hl=(\w{5})\&*?)', '', str(self.request.query_string))

        return self.request.path + "?" if path_lang == "" else str(self.request.path) + "?" + path_lang

    @property
    def locales(self):
        """
        returns a dict of locale codes to locale display names in both the current locale and the localized locale
        example: if the current locale is es_ES then locales['en_US'] = 'Ingles (Estados Unidos) - English (United States)'
        """
        if not self.app.config.get('locales'):
            return None
        locales = {}
        for l in self.app.config.get('locales'):
            current_locale = Locale.parse(self.locale)
            language = current_locale.languages[l.split('_')[0]]
            territory = current_locale.territories[l.split('_')[1]]
            localized_locale_name = Locale.parse(l).display_name.capitalize()
            locales[l] = language.capitalize() + " (" + territory.capitalize() + ") - " + localized_locale_name
        return locales

    @webapp2.cached_property
    def tz(self):
        tz = [(tz, tz.replace('_', ' ')) for tz in pytz.all_timezones]
        tz.insert(0, ("", ""))
        return tz

    @webapp2.cached_property
    def get_user_tz(self):
        user = self.current_user
        if user:
            if hasattr(user, 'tz') and user.tz:
                return pytz.timezone(user.tz)
        return pytz.timezone('UTC')

    @webapp2.cached_property
    def countries(self):
        return Locale.parse(self.locale).territories if self.locale else []

    @webapp2.cached_property
    def countries_tuple(self):
        countries = self.countries
        if "001" in countries:
            del (countries["001"])
        countries = [(key, countries[key]) for key in countries]
        countries.append(("", ""))
        countries.sort(key=lambda tup: tup[1])
        return countries

    @webapp2.cached_property
    def current_user(self):
        user = self.auth.get_user_by_session()
        if user:
            return self.user_model.get_by_id(user['user_id'])
        return None

    @webapp2.cached_property
    def is_mobile(self):
        return utils.set_device_cookie_and_return_bool(self)

    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(factory=jinja_bootstrap.jinja2_factory, app=self.app)

    @webapp2.cached_property
    def get_base_layout(self):
        """
        Get the current base layout template for jinja2 templating. Uses the variable base_layout set in config
        or if there is a base_layout defined, use the base_layout.
        """
        return self.base_layout if hasattr(self, 'base_layout') else self.app.config.get('base_layout')

    def set_base_layout(self, layout):
        """
        Set the base_layout variable, thereby overwriting the default layout template name in config.py.
        """
        self.base_layout = layout

    @webapp2.cached_property
    def get_landing_layout(self):
        """
        Get the current landing layout template for jinja2 templating. Uses the variable landing_layout set in config
        or if there is a landing_layout defined, use the landing_layout.
        """
        return self.landing_layout if hasattr(self, 'landing_layout') else self.app.config.get('landing_layout')

    def set_landing_layout(self, layout):
        """
        Set the landing_layout variable, thereby overwriting the default layout template name in config.py.
        """
        self.landing_layout = layout

    @webapp2.cached_property
    def brand(self):
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
        return params

    @webapp2.cached_property
    def right_sidenav_msg(self):
        return self.app.config.get('right_sidenav_msg')
    
    def render_template(self, filename, **kwargs):
        locales = self.app.config.get('locales') or []
        locale_iso = None
        language = ''
        territory = ''
        language_id = self.app.config.get('app_lang')

        if self.locale and len(locales) > 1:
            locale_iso = Locale.parse(self.locale)
            language_id = locale_iso.language
            territory_id = locale_iso.territory
            language = locale_iso.languages[language_id]
            territory = locale_iso.territories[territory_id]

        # make all self.view variables available in jinja2 templates
        if hasattr(self, 'view'):
            kwargs.update(self.view.__dict__)

        # set or overwrite special vars for jinja templates
        kwargs.update({
            'google_analytics_code': self.app.config.get('google_analytics_code'),
            'meta_tags_code': self.app.config.get('meta_tags_code'),
            'app_id': self.app.config.get('app_id'),
            'app_name': self.brand['app_name'],
            'app_domain': self.app.config.get('app_domain'),
            'city_name': self.brand['city_name'],
            'city_url': self.app.config.get('city_url'),
            'city_slogan': self.brand['city_slogan'],
            'city_splash': self.brand['city_splash'],
            'city_splash_secondary': self.brand['city_splash_secondary'],
            'city_splash_light': self.brand['city_splash_light'],
            'city_splash_secondary_light': self.brand['city_splash_secondary_light'],
            'brand_logo': self.brand['brand_logo'],
            'brand_favicon': self.brand['brand_favicon'],
            'brand_color': self.brand['brand_color'],
            'brand_secondary_color': self.brand['brand_secondary_color'],
            'brand_tertiary_color': self.brand['brand_tertiary_color'],
            'user_id': self.user_id,
            'user_is_admin': self.user_is_admin,
            'user_is_secretary': self.user_is_secretary,
            'user_is_agent': self.user_is_agent,
            'user_is_operator': self.user_is_operator,
            'user_is_callcenter': self.user_is_callcenter,
            'user_callcenter_role': self.user_callcenter_role,
            'username': self.username,
            'name': self.name,
            'email': self.email,
            'url': self.request.url,
            'path': self.request.path,
            'query_string': self.request.query_string,
            'path_for_language': self.path_for_language,
            'is_mobile': self.is_mobile,
            'right_sidenav_msg': self.right_sidenav_msg,
            'locale_iso': locale_iso, # babel locale object
            'locale_language': language.capitalize() + " (" + territory.capitalize() + ")", # babel locale object
            'locale_language_id': language_id, # babel locale object
            'locales': self.locales,
            'enable_federated_login': self.app.config.get('enable_federated_login'),
            'theme': self.get_theme,
            'base_layout': self.get_base_layout,
            'landing_layout': self.get_landing_layout,
            'zendesk_code': self.app.config.get('zendesk_code'),
            'zendesk_imports': self.app.config.get('zendesk_imports'),
            'has_reports': self.has_reports,
            'has_petitions': self.has_petitions,
            'has_transparency': self.has_transparency,
            'has_social_media': self.has_social_media,
            'has_cic': self.has_cic,
            'google_clientID': self.google_clientID,
            'facebook_appID': self.facebook_appID,
            'twitter_appID': self.twitter_appID,
            'gmaps_apikey': self.gmaps_apikey,
        })
        kwargs.update(self.auth_config)
        if hasattr(self, 'form'):
            kwargs['form'] = self.form
        if self.messages:
            kwargs['messages'] = self.messages

        self.response.headers.add_header('X-UA-Compatible', 'IE=Edge,chrome=1')
        self.response.headers.add_header('Content-Type', 'text/html; charset=utf-8')
        self.response.write(self.jinja2.render_template(filename, **kwargs))
