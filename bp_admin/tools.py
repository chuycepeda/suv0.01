# -*- coding: utf-8 -*-
from bp_includes.lib.basehandler import BaseHandler
from google.appengine.api import users #https://cloud.google.com/appengine/docs/python/refdocs/modules/google/appengine/api/users#get_current_user


class AdminCSSHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = users.get_current_user().email().lower()
        return self.render_template('admin_tools_css.html', **params)

class AdminIconsHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = users.get_current_user().email().lower()
        return self.render_template('admin_tools_icons.html', **params)

class AdminMediaHandler(BaseHandler):
    def get(self):
        params = {}
        params['nickname'] = users.get_current_user().email().lower()
        return self.render_template('admin_tools_media.html', **params)
