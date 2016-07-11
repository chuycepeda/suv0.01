from google.appengine.datastore.datastore_query import Cursor
from collections import OrderedDict, Counter
from bp_includes import models
from datetime import datetime, date, time, timedelta
import logging
#endpoints related libraries
import endpoints
from google.appengine.ext import ndb
from protorpc import messages
from protorpc import message_types
from protorpc import remote


# TODO: Replace the following lines with client IDs obtained from the APIs
# Console or Cloud Console.
# WEB_CLIENT_ID = 'replace this with your web client application ID'
# ANDROID_CLIENT_ID = 'replace this with your Android client ID'
# IOS_CLIENT_ID = 'replace this with your iOS client ID'
# ANDROID_AUDIENCE = WEB_CLIENT_ID

# Endpoints API is accessible at: <app_id>.appspot.com/_ah/api/explorer
# Field types available at: https://cloud.google.com/appengine/docs/python/tools/protorpc/messages/fieldclasses

package = 'Hello'

api = endpoints.api(name='onesmartcity', version='v1')

API_KEY = "86F7EB9A06F708A9673198AA8DA4ABD17E54A5AA"

MAX_SIZE = 1000

class KeyPage(messages.Message):
  api_key = messages.StringField(1)
  page = messages.IntegerField(2)

KEYPAGE_RESOURCE = endpoints.ResourceContainer(
      KeyPage)

GET_KEYPAGE_RESOURCE = endpoints.ResourceContainer(
      message_types.VoidMessage,
      api_key=messages.StringField(1),
      page=messages.IntegerField(2))

class PostResponse(messages.Message):
  status = messages.StringField(1)
  response = messages.StringField(2)


"""

  USERS INFO API

"""
class Users(messages.Message):
    """Users that stores a message."""
    identifier = messages.StringField(1)
    created_at = messages.StringField(2)
    last_login = messages.StringField(3)
    name = messages.StringField(4)
    last_name = messages.StringField(5)
    email = messages.StringField(6)
    image_url = messages.StringField(7)
    birth = messages.StringField(8)
    gender = messages.StringField(9)
    credibility = messages.IntegerField(10)
    address = messages.StringField(11)
    phone = messages.StringField(12)   

class UsersCollection(messages.Message):
    """Collection of Users."""
    total_rows = messages.IntegerField(1)
    items = messages.MessageField(Users, 2, repeated=True)
    pages = messages.IntegerField(3)

def getUsers(page):
  users = models.User.query()
  users = users.order(-models.User.created)
  count = users.count()
  users = users.fetch(MAX_SIZE, offset = MAX_SIZE*page)
  users_array = []
  for user in users:
    users_array.append(Users(identifier=str(user.key.id()), 
      created_at=user.created.strftime("%Y-%m-%d"), 
      last_login=user.last_login if user.last_login else '', 
      name= user.name,
      last_name = user.last_name, 
      email = user.email, 
      image_url=user.get_image_url() if user.get_image_url() != -1 else '', 
      birth=user.birth.strftime("%Y-%m-%d") if user.birth else '', 
      gender=user.gender if user.gender else '', 
      credibility=user.credibility,
      address=user.address.address_from if user.address else '', 
      phone=user.phone if user.phone else ''))

  return UsersCollection(total_rows = len(users_array), items=users_array, pages=count/MAX_SIZE)


"""

  REPORTS INFO API

"""
class Reports(messages.Message):
    """Reports that stores a message."""
    created = messages.StringField(1)
    updated = messages.StringField(2)
    terminated = messages.StringField(3)
    when = messages.StringField(4)
    title =  messages.StringField(5)
    description = messages.StringField(6)
    status = messages.StringField(7)
    address_from = messages.StringField(8)
    address_lat = messages.StringField(9)
    address_lon = messages.StringField(10)
    cdb_id = messages.IntegerField(11)
    folio = messages.StringField(12)
    contact_info = messages.StringField(13)
    user_id = messages.StringField(14)
    image_url = messages.StringField(15)
    group_category = messages.StringField(16)
    sub_category  = messages.StringField(17)
    follows = messages.IntegerField(18)
    rating = messages.IntegerField(19)
    via = messages.StringField(20)
    req_deletion = messages.BooleanField(21)
    emailed_72 = messages.BooleanField(22)
    urgent = messages.BooleanField(23)
    
class ReportsCollection(messages.Message):
    """Collection of Reports."""
    total_rows = messages.IntegerField(1)
    items = messages.MessageField(Reports, 2, repeated=True)
    pages = messages.IntegerField(3)

def getReports(page):
  reports = models.Report.query()
  reports = reports.order(-models.Report.created)
  count = reports.count()
  reports = reports.fetch(MAX_SIZE, offset = MAX_SIZE*page)
  reports_array = []
  for report in reports:
    reports_array.append(Reports(created = report.created.strftime("%Y-%m-%d"),
      updated = report.updated.strftime("%Y-%m-%d"),
      terminated = report.terminated.strftime("%Y-%m-%d") if report.terminated else '',
      when = report.when.strftime("%Y-%m-%d"),
      title =  report.title ,
      description = report.description,
      status = report.status,
      address_lat= str(report.address_from_coord.lat),
      address_lon= str(report.address_from_coord.lon),
      address_from = report.address_from,
      cdb_id = report.cdb_id,
      folio = report.folio,
      contact_info = report.contact_info if report.contact_info else '',
      user_id = str(report.user_id),
      image_url = report.image_url if report.image_url else '',
      group_category = report.group_category,
      sub_category  = report.sub_category ,
      follows = report.follows,
      rating = report.rating,
      via = report.via,
      req_deletion = report.req_deletion,
      emailed_72 = report.emailed_72,
      urgent = report.urgent))   

  return ReportsCollection(total_rows = len(reports_array), items=reports_array, pages=count/MAX_SIZE)


"""  
  
  MEDIA GETTER  

"""
class ReportsMedias(messages.Message):
    """Reports medias that stores a message."""
    created = messages.StringField(1)
    status = messages.StringField(2)
    image_url = messages.StringField(3)
    group_category = messages.StringField(4)
    sub_category  = messages.StringField(5)
      
class ReportsMediasCollection(messages.Message):
    """Collection of Reports."""
    total_rows = messages.IntegerField(1)
    items = messages.MessageField(ReportsMedias, 2, repeated=True)
    pages = messages.IntegerField(3)

def getReportsMedias(page):
  reports = models.Report.query()
  reports = reports.order(-models.Report.created)
  reports = reports.fetch(MAX_SIZE, offset = MAX_SIZE*page)
  reports_array = []
  for report in reports:
    if report.image_url:
      reports_array.append(ReportsMedias(created = report.created.strftime("%Y-%m-%d"),
        status = report.status,
        image_url = report.image_url if report.image_url else '',
        group_category = report.group_category,
        sub_category  = report.sub_category))   

  return ReportsMediasCollection(total_rows = len(reports_array), items=reports_array, pages=int(len(reports_array)/MAX_SIZE))

"""  
  
  REGISTER & LOGIN METHODS

"""

class SignIn(messages.Message):
    email = messages.StringField(1)
    password = messages.StringField(2)

class SignUp(messages.Message):
    email = messages.StringField(1)
    password = messages.StringField(2)
    name = messages.StringField(3)


SIGNIN_RESOURCE = endpoints.ResourceContainer(
    SignIn)

SIGNUP_RESOURCE = endpoints.ResourceContainer(
    SignUp)

def getCredentials(method, email, password, name):
  logging.info('request got for email %s, at method %s' % (email, method))
  status = 'success'
  response = 'got %s it! with email %s' % (method, email)
  return PostResponse(status=status, response=response)

# -------------------------------------------------------------
# -------------------------------------------------------------
# -------------------------------------------------------------

"""

  MAIN API

"""
@api.api_class(resource_name='main')
class MainApi(remote.Service):
    """
        Main onesmartcity API v1.

    """

    #SIGN UP METHOD
    @endpoints.method(SIGNUP_RESOURCE, PostResponse,
                      path='signup',
                      http_method='POST',
                      name='users.signup')
    def sign_up(self, request):
      return getCredentials('signup', request.email, request.password, request.name)

    #SIGN IN METHOD
    @endpoints.method(SIGNIN_RESOURCE, PostResponse,
                      path='signin',
                      http_method='POST',
                      name='users.signin')
    def sign_in(self, request):
      return getCredentials('signin', request.email, request.password, '')


    #USERS INFO METHOD
    @endpoints.method(KEYPAGE_RESOURCE, UsersCollection,
                      path='users', http_method='POST',
                      name='users.list')
    def users_list(self, request):
      if request.api_key == API_KEY:
        page = request.page if request.page is not None else 0
        return getUsers(int(page))

    #REPORTS INFO METHOD
    @endpoints.method(KEYPAGE_RESOURCE, ReportsCollection,
                      path='reports', http_method='POST',
                      name='reports.list')
    def reports_list(self, request):
      if request.api_key == API_KEY:
        page = request.page if request.page is not None else 0
        return getReports(int(page))

    #REPORTS MEDIAS METHOD
    @endpoints.method(KEYPAGE_RESOURCE, ReportsMediasCollection,
                      path='media', http_method='POST',
                      name='reports.media')
    def reports_media(self, request):
      if request.api_key == API_KEY:
        page = request.page if request.page is not None else 0
        return getReportsMedias(int(page))

    #EXPORTS
    @endpoints.method(GET_KEYPAGE_RESOURCE, UsersCollection,
                      path='export/users/{api_key}/{page}', http_method='GET',
                      name='export.users')
    def export_users_list(self, request):
      if request.api_key == API_KEY:
        return getUsers(int(request.page))

    @endpoints.method(GET_KEYPAGE_RESOURCE, ReportsCollection,
                      path='export/reports/{api_key}/{page}', http_method='GET',
                      name='export.reports')
    def export_reports_list(self, request):
      if request.api_key == API_KEY:
        return getReports(int(request.page))


#Endpoints yaml pointer
APPLICATION = endpoints.api_server([api])