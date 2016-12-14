# -*- coding: utf-8 -*-
from webapp2_extras.appengine.auth.models import User
from google.appengine.ext import ndb, blobstore
import datetime

#---------------------------------------  B R A N D    M O D E L -------------------------------------------------------------------          
class Brand(ndb.Model):
    app_name = ndb.StringProperty(default = '')
    city_name = ndb.StringProperty(default = '')
    city_slogan = ndb.StringProperty(default = '')
    city_splash = ndb.StringProperty(default = '')
    city_splash_light = ndb.StringProperty(default = '')
    city_splash_secondary = ndb.StringProperty(default = '')
    city_splash_secondary_light = ndb.StringProperty(default = '')
    brand_logo = ndb.StringProperty(default = '')
    brand_favicon = ndb.StringProperty(default = '')
    brand_color = ndb.StringProperty(default = '')
    brand_secondary_color = ndb.StringProperty(default = '')
    brand_tertiary_color = ndb.StringProperty(default = '')

class Configuration(ndb.Model):
    first_level_caps_singular = ndb.StringProperty(default = '')
    first_level_caps_plural = ndb.StringProperty(default = '')
    first_level_mins_singular = ndb.StringProperty(default = '')
    first_level_mins_plural = ndb.StringProperty(default = '')
    first_level_caps_person = ndb.StringProperty(default = '')
    second_level_caps_singular = ndb.StringProperty(default = '')
    second_level_caps_plural = ndb.StringProperty(default = '')
    second_level_mins_singular = ndb.StringProperty(default = '')
    second_level_mins_plural = ndb.StringProperty(default = '')
    second_level_caps_person = ndb.StringProperty(default = '')
    has_reports = ndb.BooleanProperty(default = True)
    has_petitions = ndb.BooleanProperty(default = True)
    has_transparency = ndb.BooleanProperty(default = True)
    has_social_media = ndb.BooleanProperty(default = True)
    has_cic = ndb.BooleanProperty(default = False)
    captcha_public_key = ndb.StringProperty(default = '')
    captcha_private_key = ndb.StringProperty(default = '')
    twitter_url = ndb.StringProperty(default = '')
    facebook_url = ndb.StringProperty(default = '')
    twitter_handle = ndb.StringProperty(default = '')
    facebook_handle = ndb.StringProperty(default = '')
    google_clientID = ndb.StringProperty(default = '')
    twitter_appID = ndb.StringProperty(default = '')
    facebook_appID = ndb.StringProperty(default = '')
    indicoio_apikey = ndb.StringProperty(default = '')
    bitly_login = ndb.StringProperty(default = '')
    bitly_apikey = ndb.StringProperty(default = '')
    gmaps_apikey = ndb.StringProperty(default = '')
    map_center_lat = ndb.FloatProperty(default = -1)
    map_center_lng = ndb.FloatProperty(default = -1)
    map_zoom = ndb.IntegerProperty(default = -1)
    map_zoom_mobile = ndb.IntegerProperty(default = -1)
    cartodb_user = ndb.StringProperty(default = '')
    cartodb_apikey = ndb.StringProperty(default = '')
    cartodb_reports_table = ndb.StringProperty(default = '')
    cartodb_pois_table = ndb.StringProperty(default = '')
    cartodb_category_dict_table = ndb.StringProperty(default = '')
    cartodb_polygon_table = ndb.StringProperty(default = '')
    cartodb_polygon_name = ndb.StringProperty(default = '')
    cartodb_polygon_full_name = ndb.StringProperty(default = '')
    cartodb_polygon_cve_ent = ndb.IntegerProperty(default = -1)
    cartodb_polygon_cve_mun = ndb.IntegerProperty(default = -1)
    cartodb_cic_user = ndb.StringProperty(default = '')
    cartodb_cic_reports_table = ndb.StringProperty(default = '')
    users_export_url = ndb.StringProperty(default = '')
    reports_export_url = ndb.StringProperty(default = '')
    sendgrid_priority = ndb.BooleanProperty()
    sendgrid_login = ndb.StringProperty(default = '')
    sendgrid_passkey = ndb.StringProperty(default = '')

#--------------------------------------- ENDOF    B R A N D     M O D E L -------------------------------------------------------------------          

#--------------------------------------- U S E R    M O D E L -------------------------------------------------------------------          
class Rewards(ndb.Model):
    amount = ndb.IntegerProperty()                                                                  #: number of points acquired 
    earned = ndb.BooleanProperty()                                                                  #: to identify if earned or spent
    category = ndb.StringProperty(choices = ['invite','donation','purchase','configuration'])       #: to identify main reason of rewards attribution
    content = ndb.StringProperty()                                                                  #: used to track referred emails
    timestamp = ndb.StringProperty()                                                                #: when was it assigned
    status = ndb.StringProperty(choices = ['invited','joined','completed','inelegible'])            #: current status of reward

class Notifications(ndb.Model):  
    sms = ndb.BooleanProperty()
    email = ndb.BooleanProperty()
    endpoint = ndb.BooleanProperty()
    twitter = ndb.StringProperty()

class Address(ndb.Model):
    address_from_coord = ndb.GeoPtProperty()                                                        #: lat/long address
    address_from = ndb.StringProperty()                                                             #: text address

class User(User):
    """
    Universal user model. Can be used with App Engine's default users API,
    own auth or third party authentication methods (OpenID, OAuth etc).
    """
    created = ndb.DateTimeProperty(auto_now_add=True)                                              #: Creation date.
    updated = ndb.DateTimeProperty(auto_now=True)                                                  #: Modification date.    
    last_login = ndb.StringProperty()                                                              #: Last user login.    
    username = ndb.StringProperty()                                                                #: User defined unique name, also used as key_name. >>Replaced as an email duplicate to avoid same emails several accounts
    name = ndb.StringProperty()                                                                    #: User Name    
    last_name = ndb.StringProperty()                                                               #: User Last Name    
    last_name2 = ndb.StringProperty()                                                              #: User Last Name 
    email = ndb.StringProperty()                                                                   #: User email
    phone = ndb.StringProperty()                                                                   #: User phone
    twitter_handle = ndb.StringProperty()                                                          #: User twitter handle for future notification purposes
    facebook_ID = ndb.StringProperty()                                                             #: User facebook ID for profile purposes
    google_ID = ndb.StringProperty()                                                               #: User google ID for profile purposes
    address = ndb.StructuredProperty(Address)                                                      #: User georeference
    password = ndb.StringProperty()                                                                #: Hashed password. Only set for own authentication.    
    birth = ndb.DateProperty()                                                                     #: User birthday.
    gender = ndb.StringProperty(choices = ['male','female'])                                       #: User sex    
    scholarity = ndb.StringProperty(choices = ['elementary','middleschool','highschool','technical','undergraduate','graduate'])  #: User scholarity    
    activated = ndb.BooleanProperty(default=False)                                                 #: Account activation verifies email    
    link_referral = ndb.StringProperty()                                                           #: Once verified, this link is used for referral sign ups (uses bit.ly)    
    rewards = ndb.StructuredProperty(Rewards, repeated = True)                                     #: Rewards allocation property, includes referral email tracking.    
    role = ndb.StringProperty(choices = ['NA','Member','Admin'], default = 'Admin')                #: Role in account
    notifications = ndb.StructuredProperty(Notifications)                                          #: Setup of notifications
    picture = ndb.BlobProperty()                                                                   #: User profile picture as an element in datastore of type blob
    credibility = ndb.IntegerProperty(default = 5)                                                 #: To identify spammers or very good citizens
	
    @classmethod
    def get_by_email(cls, email):
        """Returns a user object based on an email.

        :param email:
            String representing the user email. Examples:

        :returns:
            A user object.
        """
        return cls.query(cls.email == email).get()

    @classmethod
    def create_resend_token(cls, user_id):
        entity = cls.token_model.create(user_id, 'resend-activation-mail')
        return entity.token

    @classmethod
    def validate_resend_token(cls, user_id, token):
        return cls.validate_token(user_id, 'resend-activation-mail', token)

    @classmethod
    def delete_resend_token(cls, user_id, token):
        cls.token_model.get_key(user_id, 'resend-activation-mail', token).delete()
 
    def is_secretary(self):
        return True if Secretary.get_admin_by_email(self.email) else False

    def is_agent(self):
        return True if Agency.get_admin_by_email(self.email).count() >= 1 else False

    def is_operator(self):
        return True if Operator.get_by_email(self.email).count() >= 1 else False

    def is_callcenter(self):
        return True if CallCenterOperator.get_by_email(self.email) else False

    def has_callcenter_role(self):
        return CallCenterOperator.get_by_email(self.email).role if CallCenterOperator.get_by_email(self.email) else False

    def get_image_url(self):
        if self.picture:
            return "/media/serve/profile/%s/" % self._key.id()
        elif self.facebook_ID is not None or self.google_ID is not None:
            if self.facebook_ID is not None:
                social = UserFB.query(UserFB.user_id == int(self._key.id())).get()
            elif self.google_ID is not None:
                social = UserGOOG.query(UserGOOG.user_id == int(self._key.id())).get()
            if social is not None:
                return social.picture if social.picture is not None else -1
        else:
            return -1

    def get_social_providers_names(self):
        social_user_objects = SocialUser.get_by_user(self.key)
        result = []
        for social_user_object in social_user_objects:
            result.append(social_user_object.provider)
        return result

    def get_social_providers_info(self):
        providers = self.get_social_providers_names()
        result = {'used': [], 'unused': []}
        for k,v in SocialUser.PROVIDERS_INFO.items():
            if k in providers:
                result['used'].append(v)
            else:
                result['unused'].append(v)
        return result

    def get_rewards(self):
        amount = 0
        for reward in self.rewards:
            amount += reward.amount

        amount += 100*self.get_reports_count()
        amount += 30*self.get_follows_count()

        return amount

    def get_reports_count(self):
        reports = Report.query(Report.user_id == int(self.key.id()))
        return reports.count()

    def get_follows_count(self):
        follows = Followers.query(Followers.user_id == int(self.key.id()))
        return follows.count()

    def get_petitions_count(self):
        petitions = Petition.query(Petition.user_id == int(self.key.id()))
        return petitions.count()

class UserFB(ndb.Model):
    user_id = ndb.IntegerProperty(required = True)
    age_range = ndb.IntegerProperty()
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    gender = ndb.StringProperty()
    picture = ndb.StringProperty()
    cover = ndb.StringProperty()

class UserGOOG(ndb.Model):
    user_id = ndb.IntegerProperty(required = True)
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    gender = ndb.StringProperty()
    picture = ndb.StringProperty()
    cover = ndb.StringProperty()

#--------------------------------------- ENDOF   U S E R    M O D E L -----------------------------------------------------------   

#--------------------------------------- R E P O R T    M O D E L ---------------------------------------------------------------          
class Report(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add = True)                                                                             #: Creation date on ndb
    updated = ndb.DateTimeProperty(auto_now = True)                                                                                 #: Modification date on ndb
    terminated = ndb.DateTimeProperty()                                                                                             #: Solved or closed date for report
    when = ndb.DateProperty()                                                                                                       #: date the event took place
    title =  ndb.StringProperty()                                                                                                   #: Report title
    description = ndb.TextProperty()                                                                                                #: Report description
    status = ndb.StringProperty(choices = ['open', 'halted', 'assigned', 'spam', 'archived', 'forgot', 'answered', 'rejected', 'working', 'solved', 'failed'], default = 'open') #: Report status
    address_from_coord = ndb.GeoPtProperty()                                                                                        #: lat/long address for report 
    address_from = ndb.StringProperty()                                                                                             #: text address for report from gmaps API
    address_detail = ndb.StringProperty(default = "")                                                                               #: text address for report
    cdb_id = ndb.IntegerProperty(default = -1)                                                                                      #: ID in CartoDB PostGIS DB
    folio = ndb.StringProperty(default = '-1')                                                                                      #: ID in Government database
    contact_info = ndb.StringProperty()                                                                                             #: User contact information
    contact_name = ndb.ComputedProperty(lambda self: self.get_contact_name())
    contact_lastname = ndb.ComputedProperty(lambda self: self.get_contact_lastname())
    contact_phone = ndb.ComputedProperty(lambda self: self.get_contact_phone())
    user_id = ndb.IntegerProperty(required = True, default = -1)                                                                    #: Reporting user ID
    image_url = ndb.StringProperty()                                                                                                #: Report media 
    group_category = ndb.StringProperty()                                                                                           #: Parent category
    sub_category  = ndb.StringProperty()                                                                                            #: Child category
    follows = ndb.IntegerProperty(default = 0)                                                                                      #: Followers as votes/relevance for this report
    rating = ndb.IntegerProperty(choices = [0,1,2,3,4,5], default = 0)                                                                #: Report satisfaction
    via = ndb.StringProperty(choices = ['web','whatsapp','phone','street','networks','office','event','letter', 'media'], default = 'web')   #: Report via
    req_deletion = ndb.BooleanProperty(default = False)                                                                             #: Raised flag for user requesting deletion
    emailed_72 = ndb.BooleanProperty(default = False)                                                                               #: Raised flag for detecting if user has been emailed at most 72 hours.
    urgent = ndb.BooleanProperty(default = False)                                                                                   #: Raised flag for urgent reports
    is_manual = ndb.BooleanProperty(default = False)                                                                               #: Raised flag for manual reports
    simple_status = ndb.ComputedProperty(lambda self: self.get_status())
    simple_contact = ndb.ComputedProperty(lambda self: self.get_contact_info())
    simple_via = ndb.ComputedProperty(lambda self: self.get_via())
    simple_stakeholder = ndb.ComputedProperty(lambda self: self.get_stakeholder())
    simple_priority = ndb.ComputedProperty(lambda self: self.get_priority())
    simple_creator_email = ndb.ComputedProperty(lambda self: self.get_user_email())
    
    def get_id(self):
        return self._key.id()

    def get_user_email(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            return user.email
        else:
            return ''

    def get_user_name(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            return user.name
        else:
            return ''

    def get_user_lastname(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            return user.last_name
        else:
            return ''

    def get_user_phone(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            return user.phone
        else:
            return ''

    def get_user_address(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            if user.address:
                return user.address.address_from
        else:
            return ''

    def get_user_phone(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            return user.phone
        else:
            return ''

    def get_secretary(self):
        group = GroupCategory.get_by_name(self.group_category)
        if group:
            agency = Agency.get_by_group_id(group._key.id())
            if agency:
                secretary = Secretary.get_by_id(long(agency.secretary_id))
                return secretary.name
            return ''
        return ''

    def get_agency(self):
        group = GroupCategory.get_by_name(self.group_category)
        if group:
            agency = Agency.get_by_group_id(group._key.id())
            if agency:
                return agency.name
            return ''
        return ''

    def get_benchmark(self):
        subcat = SubCategory.get_by_name(self.sub_category)
        if subcat:
            benchmark = subcat.benchmark
        else:
            benchmark = 3
        return u"Solución ideal en: %s días" % benchmark

    def get_priority(self):
        d1 = datetime.datetime(self.created.year,self.created.month,self.created.day)
        d2 = datetime.datetime(datetime.date.today().year,datetime.date.today().month,datetime.date.today().day)
        diff = (d2-d1).days
        if self.status in ['open', 'halted', 'assigned', 'rejected', 'working', 'answered']:
            subcat = SubCategory.get_by_name(self.sub_category)
            if subcat:
                benchmark = subcat.benchmark
            else:
                benchmark = 3
            if diff <= 1:
                return "A tiempo"
            elif diff == benchmark-1:
                return "Por vencer"
            elif diff == benchmark:
                return "Vencido"
            else:
                return "Retrasado"
        else:
            return "---"

    def get_priority_color(self):
        d1 = datetime.datetime(self.created.year,self.created.month,self.created.day)
        d2 = datetime.datetime(datetime.date.today().year,datetime.date.today().month,datetime.date.today().day)
        diff = (d2-d1).days
        if self.status in ['open', 'halted', 'assigned', 'rejected', 'working', 'answered']:
            subcat = SubCategory.get_by_name(self.sub_category)
            if subcat:
                benchmark = subcat.benchmark
            else:
                benchmark = 3
            if diff <= 1:
                return "#F0FED7"
            elif diff == benchmark-1:
                return "#FFEAA9"
            elif diff == benchmark:
                return "#F4C0A4"
            else:
                return "#FF9A97"
        else:
            return ""

    def get_human_date(self):
        d1 = datetime.datetime(self.created.year,self.created.month,self.created.day)
        d2 = datetime.datetime(datetime.date.today().year,datetime.date.today().month,datetime.date.today().day)
        diff = (d2-d1).days
        return "Hace " + str(diff) + " dias"

    def get_human_updated_date(self):
        d1 = datetime.datetime(self.updated.year,self.updated.month,self.updated.day)
        d2 = datetime.datetime(datetime.date.today().year,datetime.date.today().month,datetime.date.today().day)
        diff = (d2-d1).days
        return "Hace " + str(diff) + " dias"

    def get_created_date(self):
        return datetime.date(self.created.year,self.created.month,self.created.day).strftime("%Y-%m-%d")

    def get_updated_date(self):
        return datetime.date(self.updated.year,self.updated.month,self.updated.day).strftime("%Y-%m-%d")

    def get_formatted_date(self):
        return datetime.date(self.when.year,self.when.month,self.when.day).strftime("%Y-%m-%d")

    def get_status(self):
        if self.status == 'open':
            return 'Abierto'        
        if self.status == 'halted':
            return 'En espera'
        if self.status == 'assigned':
            return 'Asignado'
        if self.status == 'spam':
            return 'Spam'
        if self.status == 'archived':
            return 'Archivado'
        if self.status == 'forgot':
            return 'Olvidado'
        if self.status == 'rejected':
            return 'Rechazado'
        if self.status == 'working':
            return 'En proceso'
        if self.status == 'answered':
            return 'Respondido'
        if self.status == 'solved':
            return 'Resuelto'
        if self.status == 'failed':
            return 'Fallo'

    def get_via(self):
        if self.via == 'web':
            return 'Web'
        if self.via == 'whatsapp':
            return 'Whatsapp'
        if self.via == 'phone':
            return u'Teléfono'
        if self.via == 'street':
            return 'Alcalde en tu calle'
        if self.via == 'networks':
            return 'Redes sociales'
        if self.via == 'office':
            return 'Oficina'
        if self.via == 'event':
            return 'Evento'
        if self.via == 'letter':
            return 'Oficio'
        if self.via == 'media':
            return 'Medios'

    def get_group_color(self):
        group = GroupCategory.get_by_name(self.group_category)
        if group:
            return group.color
        return "FFFFFF"

    def get_log_count(self):
        logs = LogChange.query(LogChange.report_id == self._key.id())
        return logs.count()

    def get_last_log(self):
        logs = LogChange.query(LogChange.report_id == int(self._key.id()))
        logs = logs.order(-LogChange.created)
        for log in logs:
            return log.user_email
        return '---'
    
    def get_contact_info(self):
        if self.is_manual:
            return self.contact_info
        return u"%s, %s, %s, %s" % (self.contact_name, self.contact_lastname, self.contact_phone, self.get_user_email())

    def get_contact_name(self):
        if self.is_manual:
            try:
                return u"%s" % self.contact_info.split(',')[0].strip()
            except:
                return ""
        return u"%s" % (self.get_user_name())

    def get_contact_lastname(self):
        if self.is_manual:
            try:
                return u"%s" % self.contact_info.split(',')[1].strip()
            except:
                return ""
        return u"%s" % (self.get_user_lastname())

    def get_contact_phone(self):
        if self.is_manual:
            try:
                return u"%s" % self.contact_info.split(',')[-2].strip()
            except:
                return ""
        return u"%s" % (self.get_user_phone())

    def get_stakeholder(self):
        group = GroupCategory.get_by_name(self.group_category)
        if group:
            agency = Agency.get_by_group_id(group._key.id())
            if agency:
                return u"%s, %s" % (agency.admin_name, agency.admin_email)
        return '-'

    @classmethod
    def get_by_cdb(cls, cdb_id):
        return cls.query(cls.cdb_id == cdb_id).get()

class Secretary(ndb.Model):
    name= ndb.StringProperty(required = True)
    description= ndb.StringProperty()
    phone = ndb.StringProperty(default = '')
    address = ndb.StringProperty(default = '')
    admin_name = ndb.StringProperty()
    admin_email = ndb.StringProperty()  

    @classmethod
    def get_admin_by_email(cls, email):
        """Returns a secretary object based on an email.

        :param email:
            String representing the admin email. Examples:

        :returns:
            A secretary object.
        """
        return cls.query(cls.admin_email == email).get()  

    def get_agencies_count(self):
        agencies = Agency.query(Agency.secretary_id == long(self._key.id()))
        return agencies.count() 

    def get_agencies(self):        
        return Agency.query(Agency.secretary_id == long(self._key.id()))

    def get_id(self):
        return self._key.id()                                                                                     

class Agency(ndb.Model):
    name= ndb.StringProperty(required = True)
    description= ndb.StringProperty()
    admin_name = ndb.StringProperty()
    admin_email = ndb.StringProperty()
    secretary_id = ndb.IntegerProperty(required = True)
    group_category_id = ndb.IntegerProperty()

    @classmethod
    def get_admin_by_email(cls, email):
        """Returns an agency object based on an email.

        :param email:
            String representing the admin email. Examples:

        :returns:
            An agency object.
        """
        return cls.query(cls.admin_email == email)    

    @classmethod
    def get_by_group_id(cls, group_id):
        return cls.query(cls.group_category_id == group_id).get()                                                                                      

    def get_operators_count(self):
        operators = Operator.query(Operator.agency_id == long(self._key.id()))
        return operators.count()

    def get_operators(self):        
        return Operator.query(Operator.agency_id == long(self._key.id()))

    def get_group_name(self):
        if self.group_category_id:
            group = GroupCategory.get_by_id(long(self.group_category_id))
            if group:
                return group.name
        return ""

    def get_id(self):
        return self._key.id() 

class Operator(ndb.Model):
    email= ndb.StringProperty(required = True)
    name= ndb.StringProperty()
    agency_id = ndb.IntegerProperty(required = True)

    @classmethod
    def get_by_email(cls, email):
        """Returns an operator object based on an email.

        :param email:
            String representing the user email. Examples:

        :returns:
            A operator object.
        """
        return cls.query(cls.email == email) 

    def get_id(self):
        return self._key.id()     

    def get_secretary_id(self):
        agency = Agency.get_by_id(long(self.agency_id))
        return agency.secretary_id if agency else None

    def is_active(self):
        _user = User.get_by_email(self.email)
        if _user:
            return "Si"
        else:
            return "No"

class CallCenterOperator(ndb.Model):
    email= ndb.StringProperty(required = True)
    name= ndb.StringProperty()
    role = ndb.StringProperty(required = True, choices = ['callcenter','transparency', 'socialnetworks', 'admin'], default = 'callcenter')

    @classmethod
    def get_by_email(cls, email):
        """Returns an operator object based on an email.

        :param email:
            String representing the user email. Examples:

        :returns:
            A operator object.
        """
        return cls.query(cls.email == email).get()

    def get_id(self):
        return self._key.id()    

    def is_active(self):
        _user = User.get_by_email(self.email)
        if _user:
            return "Si"
        else:
            return "No"

    def has_role(self):
        if self.role == 'callcenter':
            return u"Atención ciudadana"
        elif self.role == 'transparency':
            return "Transparencia"     
        elif self.role == 'socialnetworks':
            return "Redes sociales"     
        else:
            return "Acceso universal"

class GroupCategory(ndb.Model):
    name = ndb.StringProperty(required = True)
    color = ndb.StringProperty(required = True, default = "4EC8BC")
    icon_url = ndb.StringProperty(required = True)
    cdb_id = ndb.IntegerProperty(default = -1)                                                                                      #: ID in CartoDB PostGIS DB

    def get_agencies(self):
        return Agency.query(Agency.group_category_id == long(self._key.id()))
        
    def get_subcategories_count(self):
        subcategories = SubCategory.query(SubCategory.group_category_id == long(self._key.id()))
        return subcategories.count()

    def get_subcategories(self):        
        return SubCategory.query(SubCategory.group_category_id == long(self._key.id()))

    @classmethod
    def get_by_name(cls, name):
        return cls.query(cls.name == name).get()

    def get_id(self):
        return self._key.id()

class SubCategory(ndb.Model):
    group_category_id = ndb.IntegerProperty(required = True)
    name = ndb.StringProperty()
    description= ndb.StringProperty(default = "")
    icon = ndb.StringProperty(required = True, default="http://one-smart-city-demo.appspot.com/default/materialize/images/google_icons/postal-code-prefix.svg")         #duplicated
    icon_url = ndb.StringProperty(required = True, default="http://one-smart-city-demo.appspot.com/default/materialize/images/google_icons/postal-code-prefix.svg")         
    requires_image = ndb.BooleanProperty(default = False)                                                                               
    benchmark = ndb.IntegerProperty(default = 3)
    cdb_id = ndb.IntegerProperty(default = -1)                                                                                      #: ID in CartoDB PostGIS DB
    private = ndb.BooleanProperty(default = False)   

    @classmethod
    def get_by_name(cls, name):
        return cls.query(cls.name == name).get()                                                                            

    def get_id(self):
        return self._key.id()

class Attachment(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)   #creation date                              
    file_name = ndb.StringProperty(required = True)      #blobstore url                                                                         
    file_url = ndb.StringProperty(required = True, default = '')      #blobstore url                                                                         
    report_id = ndb.IntegerProperty(required = True)    #report to attach
    user_id = ndb.IntegerProperty(required = True)      #creator

    def get_user_image(self):
        user = User.get_by_id(long(self.user_id))
        if user.picture:
            return "/media/serve/profile/%s/" % user.key.id()
        elif user.facebook_ID is not None or user.google_ID is not None:
            if user.facebook_ID is not None:
                social = UserFB.query(UserFB.user_id == int(user.key.id())).get()
            elif user.google_ID is not None:
                social = UserGOOG.query(UserGOOG.user_id == int(user.key.id())).get()
            if social is not None:
                return social.picture if social.picture is not None else -1
        else:
            return -1

    def get_user_name(self):
        user = User.get_by_id(long(self.user_id))
        return user.name

    def get_user_email(self):
        user = User.get_by_id(long(self.user_id))
        return user.email

    def get_formatted_date(self):
        return datetime.datetime(self.created.year,self.created.month,self.created.day, self.created.hour, self.created.minute, self.created.second).strftime("%Y-%m-%d a las %X %p (GMT-00)")

class LogChange(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)                                               
    user_email = ndb.StringProperty(required = True)
    report_id = ndb.IntegerProperty(required = True)
    title = ndb.StringProperty(required = True)
    contents = ndb.TextProperty(required = True)
    kind = ndb.StringProperty(choices = ['status','fixes','comment','note'])

    def get_id(self):
        return self._key.id()

    def get_user(self):
        user = User.get_by_email(self.user_email)
        if user:
            return user
        else:
            return None

    def get_report(self):
        report = Report.get_by_id(long(self.report_id))
        if report:
            return report
        else:
            return None

    def get_formatted_date(self):
        return datetime.datetime(self.created.year,self.created.month,self.created.day, self.created.hour, self.created.minute, self.created.second).strftime("%Y-%m-%d a las %X %p (GMT-00)")

class Followers(ndb.Model):
    user_id = ndb.IntegerProperty(required = True)
    report_id = ndb.IntegerProperty(required = True)

    @classmethod
    def get_user_follows(cls, user_id):
        return cls.query(cls.user_id == user_id)

    @classmethod
    def get_report_follows(cls, report_id):
        return cls.query(cls.report_id == report_id)

#--------------------------------------- ENDOF   R E P O R T   M O D E L --------------------------------------------------------          

#--------------------------------------- P E T I T I O N    M O D E L ---------------------------------------------------------------     

class Petition(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add = True)                                                                             #: Creation date on ndb
    updated = ndb.DateTimeProperty(auto_now = True)                                                                                 #: Modification date on ndb
    title =  ndb.StringProperty()                                                                                                   #: Petition title
    description = ndb.TextProperty()                                                                                                #: Petition description
    kind = ndb.StringProperty(required = True, default = 'citizen', choices = ['citizen', 'official'])                              #: Petition kind for citizen or official
    status = ndb.StringProperty(required = True, default = 'open', choices = ['open', 'triggered', 'expired', 'responded'])         #: Petition status
    contact_info = ndb.StringProperty()                                                                                             #: User contact information for flexibility
    contact_name = ndb.ComputedProperty(lambda self: self.get_contact_name())                                                       #: Contact additionals as computed props    
    contact_lastname = ndb.ComputedProperty(lambda self: self.get_contact_lastname())                                               #: Contact additionals as computed props
    user_id = ndb.IntegerProperty(required = True, default = -1)                                                                    #: Author user ID
    url = ndb.StringProperty(required = True, default = '')                                                                         #: Petition url 
    image_url = ndb.StringProperty()                                                                                                #: Petition media 
    topic  = ndb.StringProperty(repeated = True)                                                                                    #: Petition topic
    votes = ndb.ComputedProperty(lambda self: self.get_petition_votes())                                                            #: Petition votes in favor                                                             
    flags = ndb.ComputedProperty(lambda self: self.get_petition_flags())                                                            #: Petition flags as inappropriate                                                             
    expiration = ndb.ComputedProperty(lambda self: self.get_petition_expiration())                                                  #: Petition expiration date according to topic                                                              
    
    def get_id(self):
        return self._key.id()

    def get_user_email(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            return user.email
        else:
            return ''

    def get_user_name(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            return user.name
        else:
            return ''

    def get_user_lastname(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            return user.last_name
        else:
            return ''

    def get_user_address(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            if user.address:
                return user.address.address_from
        else:
            return ''

    def get_user_phone(self):
        user = User.get_by_id(long(self.user_id)) if self.user_id != -1 else None
        if user:
            return user.phone
        else:
            return ''

    def get_human_date(self):
        d1 = datetime.datetime(self.created.year,self.created.month,self.created.day)
        d2 = datetime.datetime(datetime.date.today().year,datetime.date.today().month,datetime.date.today().day)
        diff = (d2-d1).days
        return "Hace " + str(diff) + " dias"

    def get_human_updated_date(self):
        d1 = datetime.datetime(self.updated.year,self.updated.month,self.updated.day)
        d2 = datetime.datetime(datetime.date.today().year,datetime.date.today().month,datetime.date.today().day)
        diff = (d2-d1).days
        return "Hace " + str(diff) + " dias"

    def get_created_date(self):
        return datetime.date(self.created.year,self.created.month,self.created.day).strftime("%Y-%m-%d")

    def get_updated_date(self):
        return datetime.date(self.updated.year,self.updated.month,self.updated.day).strftime("%Y-%m-%d")

    def get_formatted_date(self):
        return datetime.date(self.when.year,self.when.month,self.when.day).strftime("%Y-%m-%d")

    def get_status(self):
        if self.status == 'open':
            return 'Abierta'        
        if self.status == 'triggered':
            return 'En espera'
        if self.status == 'expired':
            return 'Expirada'
        if self.status == 'responded':
            return 'Atendida'
    
    def get_contact_info(self):
        if self.contact_info:
            if len(self.contact_info) > 3:
                return self.contact_info
        return u"%s, %s" % (self.get_user_name(), self.get_user_email())

    def get_contact_name(self):
        if self.contact_info:
            if len(self.contact_info.split(',')) > 1:
                return self.contact_info.split(',')[0].strip()
        return u"%s" % (self.get_user_name())

    def get_contact_lastname(self):
        if self.contact_info:
            if len(self.contact_info.split(',')) > 2:
                return self.contact_info.split(',')[1].strip()
        return u"%s" % (self.get_user_lastname())

    def get_petition_votes(self):
        _votes = Votes.query(Votes.petition_id == int(self.key.id()))
        return _votes.count()

    def get_petition_flags(self):
        _flags = Flags.query(Flags.petition_id == int(self.key.id()))
        return _flags.count()

    def get_petition_expiration(self):
        if self.status == 'open' or self.status == 'expired':
            d1 = datetime.datetime(self.created.year,self.created.month,self.created.day)
            d2 = datetime.datetime(datetime.date.today().year,datetime.date.today().month,datetime.date.today().day)
            diff = (d2-d1).days
            
            min_benchmark = self.topic[0].benchmark
            for x in self.topic:
                _topic = Topic.get_by_name(x)
                if _topic.benchmark < min_benchmark:
                    min_benchmark = _topic.benchmark

            runway = min_benchmark - diff
            if runway > 0:
                return u"A esta propuesta le restan %s días para expirar." % runway
            else:
                return u"Esta propuesta expiró hace %s días." % abs(runway)
        elif self.status == 'triggered':
            return u"Esta propuesta está en espera de ser respondida." % runway
        elif self.status == 'responded':
            return u"Esta propuesta ya ha sido respondida." % runway

class Topic(ndb.Model):
    name = ndb.StringProperty(required = True)
    color = ndb.StringProperty(required = True, default = "AEAEAE")
    icon_url = ndb.StringProperty(required = True, default="http://one-smart-city-demo.appspot.com/default/materialize/images/google_icons/postal-code-prefix.svg")         
    requires_image = ndb.BooleanProperty(default = False)                                                                               
    benchmark = ndb.IntegerProperty(default = 90)
    trigger = ndb.IntegerProperty(default = 1000)

    @classmethod
    def get_by_name(cls, name):
        return cls.query(cls.name == name).get()                                                                            

    def get_id(self):
        return self._key.id()

class Votes(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add = True)                                                                             
    petition_id = ndb.IntegerProperty(required = True, default = -1)
    user_id = ndb.IntegerProperty(required = True, default = -1)

class Flags(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add = True)                                                                             
    petition_id = ndb.IntegerProperty(required = True, default = -1)
    user_id = ndb.IntegerProperty(required = True, default = -1)

class Comments(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add = True)                                                                             
    petition_id = ndb.IntegerProperty(required = True, default = -1)
    user_id = ndb.IntegerProperty(required = True, default = -1)

#--------------------------------------- ENDOF   P E T I T I O N   M O D E L --------------------------------------------------------          

#--------------------------------------- T R A N S P A R E N C Y      M O D E L -------------------------------------------------------------
class Initiative(ndb.Model):
    updated = ndb.DateTimeProperty(auto_now = True)                                                                                 #: Modification date on ndb
    name = ndb.StringProperty(required = True)
    color = ndb.StringProperty(required = True, default = "AEAEAE")
    icon_url = ndb.StringProperty(required = True, default="http://one-smart-city-demo.appspot.com/default/materialize/images/google_icons/postal-code-prefix.svg")
    image_url = ndb.StringProperty(required = True, default="http://one-smart-city-demo.appspot.com/default/materialize/images/landing/splash_secondary.png")
    value = ndb.StringProperty(required = True, default = "0")
    status = ndb.StringProperty(required = True, default = "open", choices=['open', 'measuring', 'delayed', 'near', 'completed'])
    lead = ndb.StringProperty()
    description = ndb.TextProperty()
    relevance = ndb.TextProperty()
    area_id = ndb.IntegerProperty(required = True)

    @classmethod
    def get_by_name(cls, name):
        return cls.query(cls.name == name).get()                                                                            

    @classmethod
    def get_by_area_id(cls, area_id):
        return cls.query(cls.area_id == area_id).get()                                                                                      

    def get_id(self):
        return self._key.id()

    def get_status(self):
        if self.status == 'open':
            return 'Iniciado'        
        if self.status == 'measuring':
            return 'En progreso'
        if self.status == 'delayed':
            return 'Retrasado'
        if self.status == 'near':
            return 'A punto de cumplir'
        if self.status == 'completed':
            return 'Cumplido'

    def get_status_color(self):
        if self.status == 'open':
            return '9e9e9e' #grey    
        if self.status == 'measuring':
            return '03a9f4' #light-blue
        if self.status == 'delayed':
            return 'ffc107' #amber
        if self.status == 'near':
            return '8bc34a' #light-green
        if self.status == 'completed':
            return '4caf50' #green

    def get_area_name(self):
        if self.area_id:
            area = Area.get_by_id(long(self.area_id))
            if area:
                return area.name
        return ""

    def get_human_updated_date(self):
        d1 = datetime.datetime(self.updated.year,self.updated.month,self.updated.day)
        d2 = datetime.datetime(datetime.date.today().year,datetime.date.today().month,datetime.date.today().day)
        diff = (d2-d1).days
        return "Hace " + str(diff) + " dias"

    def get_updated_date(self):
        return datetime.date(self.updated.year,self.updated.month,self.updated.day).strftime("%Y-%m-%d")

class Area(ndb.Model):
    name = ndb.StringProperty(required = True)
    color = ndb.StringProperty(required = True, default = "AEAEAE")
    icon_url = ndb.StringProperty(required = True, default="http://one-smart-city-demo.appspot.com/default/materialize/images/google_icons/postal-code-prefix.svg")
    inits_count = ndb.ComputedProperty(lambda self: self.get_inits_count())

    @classmethod
    def get_by_name(cls, name):
        return cls.query(cls.name == name).get()                                                                            

    def get_id(self):
        return self._key.id()

    def get_inits_count(self):        
        return Initiative.query(Initiative.area_id == self._key.id()).count()


#--------------------------------------- ENDOF   T R A N S P A R E N C Y   M O D E L --------------------------------------------------------          

#--------------------------------------- H E L P E R S    M O D E L S -----------------------------------------------------------          

class Media(ndb.Model):
    blob_key = ndb.BlobKeyProperty()                                                                #: Refer to https://cloud.google.com/appengine/docs/python/blobstore/

class BlogPost(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)                                               #: Creation date.
    updated = ndb.DateTimeProperty(auto_now=True)                                                   #: Modification date.    
    blob_key = ndb.BlobKeyProperty()                                                                #: Refer to https://cloud.google.com/appengine/docs/python/blobstore/
    title = ndb.StringProperty(required = True)
    subtitle = ndb.StringProperty(indexed = False)
    author = ndb.StringProperty()
    brief = ndb.TextProperty(required = True, indexed = False)
    content = ndb.TextProperty(required = True, indexed = False)
    category = ndb.StringProperty(repeated = True)

    def get_id(self):
        return self._key.id()
        
class LogVisit(ndb.Model):
    user = ndb.KeyProperty(kind=User)
    uastring = ndb.StringProperty()
    ip = ndb.StringProperty()
    timestamp = ndb.StringProperty()

    def get_user_count(self, user_id):
        logs = LogVisit.query(LogVisit.user == ndb.Key('User',user_id))
        return logs.count()

class OptionsSite(ndb.Model):
    name = ndb.KeyProperty
    value = ndb.StringProperty()
    @classmethod
    def get_option(cls,option_name):
        return cls.query(name=option_name)

class LogEmail(ndb.Model):
    sender = ndb.StringProperty(required=True)
    to = ndb.StringProperty(required=True)
    subject = ndb.StringProperty(required=True)
    body = ndb.TextProperty()
    when = ndb.DateTimeProperty()

    def get_id(self):
        return self._key.id()

class SocialUser(ndb.Model):
    PROVIDERS_INFO = { # uri is for OpenID only (not OAuth)
        'google': {'name': 'google', 'label': 'Google', 'uri': 'gmail.com'},
        'github': {'name': 'github', 'label': 'Github', 'uri': ''},
        'facebook': {'name': 'facebook', 'label': 'Facebook', 'uri': ''},
        'linkedin': {'name': 'linkedin', 'label': 'LinkedIn', 'uri': ''},
        'myopenid': {'name': 'myopenid', 'label': 'MyOpenid', 'uri': 'myopenid.com'},
        'twitter': {'name': 'twitter', 'label': 'Twitter', 'uri': ''},
        'yahoo': {'name': 'yahoo', 'label': 'Yahoo!', 'uri': 'yahoo.com'},
    }

    user = ndb.KeyProperty(kind=User)
    provider = ndb.StringProperty()
    uid = ndb.StringProperty()
    extra_data = ndb.JsonProperty()

    @classmethod
    def get_by_user(cls, user):
        return cls.query(cls.user == user).fetch()

    @classmethod
    def get_by_user_and_provider(cls, user, provider):
        return cls.query(cls.user == user, cls.provider == provider).get()

    @classmethod
    def get_by_provider_and_uid(cls, provider, uid):
        return cls.query(cls.provider == provider, cls.uid == uid).get()

    @classmethod
    def check_unique_uid(cls, provider, uid):
        # pair (provider, uid) should be unique
        test_unique_provider = cls.get_by_provider_and_uid(provider, uid)
        if test_unique_provider is not None:
            return False
        else:
            return True
    
    @classmethod
    def check_unique_user(cls, provider, user):
        # pair (user, provider) should be unique
        test_unique_user = cls.get_by_user_and_provider(user, provider)
        if test_unique_user is not None:
            return False
        else:
            return True

    @classmethod
    def check_unique(cls, user, provider, uid):
        # pair (provider, uid) should be unique and pair (user, provider) should be unique
        return cls.check_unique_uid(provider, uid) and cls.check_unique_user(provider, user)
    
    @staticmethod
    def open_id_providers():
        return [k for k,v in SocialUser.PROVIDERS_INFO.items() if v['uri']]

#--------------------------------------- ENDOF   H E L P E R S   M O D E L S -----------------------------------------------------          
