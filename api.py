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

api = endpoints.api(name='gpegobmx', version='v1')

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

def getUsers():
  users = models.User.query()
  users = users.order(models.User.created)
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

  return UsersCollection(total_rows = len(users_array), items=users_array)


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

def getReports():
  reports = models.Report.query()
  reports = reports.order(-models.Report.created)
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

  return ReportsCollection(total_rows = len(reports_array), items=reports_array)


"""

  MAIN API

"""
@api.api_class(resource_name='main')
class MainApi(remote.Service):
    """Main GPEGOBMX API v1."""

    #USERS INFO METHOD
    @endpoints.method(message_types.VoidMessage, UsersCollection,
                      path='users', http_method='GET',
                      name='users.list')
    def users_list(self, unused_request):
        return getUsers()

    #REPORTS INFO METHOD
    @endpoints.method(message_types.VoidMessage, ReportsCollection,
                      path='reports', http_method='GET',
                      name='reports.list')
    def reports_list(self, unused_request):
        return getReports()


#Endpoints yaml pointer
APPLICATION = endpoints.api_server([api])