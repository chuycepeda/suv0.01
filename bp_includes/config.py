# -*- coding: utf-8 -*-
"""
============= DON'T MODIFY THIS FILE ============
This is the boilerplate default configuration file.
Changes and additions to settings should be done in
/bp_content/themes/<YOUR_THEME>/config/ rather than this config.
"""

import os

config = {

    # jinja2 templates
    'webapp2_extras.jinja2': {'template_path': ['bp_admin/templates', 'bp_content/themes/%s/templates' % os.environ['theme']],
                              'environment_args': {'extensions': ['jinja2.ext.i18n']}},
   

    # --- --- --- start editing --- --- ---
   
    # webapp2 sessions
    'webapp2_extras.sessions': {'secret_key': 'u5nqp4ceg5rijeb15qf30vqia81nadqt'},
    # webapp2 authentication
    'webapp2_extras.auth': {'user_model': 'bp_includes.models.User',
                            'cookie_name': 'session_name'}, 
    # Password AES Encryption Parameters
    # aes_key must be only 16 (*AES-128*), 24 (*AES-192*), or 32 (*AES-256*) bytes (characters) long.
    'aes_key': "A1BED038702434F8358F799990208234",
    'salt': "634907BCD5EC4F29BE5DE8ED97637366B2C18E42E14EEEBA3925E9E0485FCCC9480BFC6CB2D8E4E8A9464F3C10ADFA0DB97451C8DB1033A6C2D6C4231D0645EF",
    'meta_tags_code': unicode("""

            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
            <meta name="apple-mobile-web-app-capable" content="yes">
            <meta name="mobile-web-app-capable" content="yes">
            <link rel="manifest" href="/manifest.json">
            <meta name="description" content="Ciudad Digital es una iniciativa del municipio para tener un gobierno más abierto." />
            <meta name="keywords" content="onesmartcity, onesmart, gobierno digital, smart city, reporte ciudadano, transparencia, gobierno, gobierno abierto"/>
            <meta property="og:site_name" content="demo.onesmart.city"/>
            <meta property="og:title" content="Demo.OneSmart.City"/>
            <meta property="og:type" content="website"/>
            <meta property="og:description" content="Ciudad Digital es una iniciativa del municipio para tener un gobierno más abierto."/>
            <meta property="og:url" content="http://demo.onesmart.city"/>
            <meta property="og:image" content="http://onesmart.city/default/materialize/images/landing/splashmeta.png"/>
            <meta name="twitter:card" content="summary_large_image">
            <meta name="twitter:site" content="Ciudad Digital es una iniciativa del municipio para tener un gobierno más abierto.">
            <meta name="twitter:creator" content="@chuycepeda,@chuydb">
            <meta name="twitter:title" content="Demo.OneSmart.City">
            <meta name="twitter:description" content="Ciudad Digital es una iniciativa del municipio para tener un gobierno más abierto.">
            <meta name="twitter:image" content="http://onesmart.city/default/materialize/images/landing/splashmeta.png">
            <meta property="twitter:url" content="http://demo.onesmart.city"/>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta name="viewport" content="width=device-width, minimum-scale=1.0, initial-scale=1.0, user-scalable=yes">""",'utf-8'),
    # application name
    'app_id': 'one-smart-city-demo',
    'app_domain':  'http://demo.onesmart.city',
    'app_name':  unicode('Mi Ciudad Digital','utf-8'),
    'city_name':  unicode('Mi Ciudad','utf-8'),
    'city_url':  'http://onesmart.city',
    'city_slogan':  unicode('Slogan de Mi Ciudad','utf-8'),
    'city_splash':  'http://one-smart-city-demo.appspot.com/default/materialize/images/landing/city.jpeg',
    'city_splash_light':  '45',
    'city_splash_secondary':  'http://one-smart-city-demo.appspot.com/default/materialize/images/landing/splash_secondary.png',
    'city_splash_secondary_light':  '45',
    'contact_recipient': "uno@onesmart.city",      
    'send_org_notifications': True,
    # application branding 
    'brand_logo': 'http://onesmart.city/default/materialize/images/_logo.png',
    'brand_favicon': 'http://onesmart.city/default/materialize/images/_logo.png',
    'brand_color' : '#59BAB9',
    'brand_secondary_color' : '#00273D',
    'brand_tertiary_color' : '#EAEAEA',
    # government naming
    'first_level_caps_singular' : unicode('Dirección','utf-8'),            #Secretaría 
    'first_level_caps_plural' : unicode('Direcciones','utf-8'),             #Secretarías 
    'first_level_mins_singular' : unicode('dirección','utf-8'),            #secretaría 
    'first_level_mins_plural' : unicode('direcciones','utf-8'),             #secretarías 
    'first_level_caps_person' : unicode('Director','utf-8'),              #Secretario 
    'second_level_caps_singular' : unicode('Subdirección','utf-8'),          #Dependencia 
    'second_level_caps_plural' : unicode('Subdirecciones','utf-8'),           #Dependencias 
    'second_level_mins_singular' : unicode('subdirección','utf-8'),          #dependencia 
    'second_level_mins_plural' : unicode('subdirecciones','utf-8'),           #dependencias 
    'second_level_caps_person' : unicode('Subdirector','utf-8'),               #Director 
    # landing specifics
    'landing_skin': '',
    'video_url':  'https://www.youtube.com/embed/RX7JMnsI7K0',
    'video_playlist':  'https://www.youtube.com/watch?v=FxozM2hAHXE',
    'right_sidenav_msg': unicode("""
        <p>
            A través de tu portal de atención, puedes contribuir a transformar nuestra ciudad en la que todos queremos. 
        </p>
        <p>
            Reportando, administrando y dando seguimiento a las necesidades que aquejan a nuestra comunidad, juntos cuidadanos y gobierno podremos ser más eficientes y demostrar que estamos para servir.
        </p>
        <p>
            ¡Felicidades por ser parte!
        </p>
    """,'utf-8'),
    # application services
    'has_ai': True,
    'has_reports': True,
    'has_petitions': True,
    'has_transparency': True,
    'has_social_media': True,
    'has_urbanism': True,
    'has_cic': False,
    # get your own recaptcha keys by registering at http://www.google.com/recaptcha/
    'captcha_public_key': "6LcMfv0SAAAAAGMJ9i-g5aJhXFvSHpPsqDLOHTUD",
    'captcha_private_key': "6LcMfv0SAAAAALMUmCmFt5NOAw_ZTHabWRHAFJI6",
    # application on social media
    'twitter_url': 'https://twitter.com/miciudadenlinea',
    'facebook_url': 'https://www.facebook.com/miciudadenlinea',
    'twitter_handle': 'gobloscabos',
    'facebook_handle':'ayuntamientodeloscabos',
    'google_clientID': '280514157419-ijeb15qf3u5nqp4ceg5r0vqia81nadqt.apps.googleusercontent.com', #get it new from https://console.cloud.google.com/apis/credentials?project=<APP_ID>
    'twitter_appID': '678306982604894208', #get it new from https://twitter.com/settings/widgets
    'facebook_appID': '523620084480399', #get it new from https://developers.facebook.com/apps/ or add redirect URI at https://developers.facebook.com/apps/523620084480399/fb-login/
    # indicoio sentiment analysis apikey, get it new from https://indico.io/dashboard/
    'indicoio_apikey': 'e778796ec0b3a2503585e9d1f736febf',
    # bitly Login & API KEY, get them from your bitly account under settings/advanced.
    'bitly_login' : "mboilerplate",
    'bitly_apikey' : "R_c7794de8fef148c6b950578064492e95",
    # slack webhook url
    'slack_webhook_url' : "https://hooks.slack.com/services/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",
    # cartodb + gmaps + cic integration
    # gmaps enabler apikey: https://console.developers.google.com/flows/enableapi?apiid=maps_backend,geocoding_backend,directions_backend,distance_matrix_backend,elevation_backend&keyType=CLIENT_SIDE&reusekey=true
    'gmaps_apikey':'AIzaSyAwOfCLYHEH2BLQ5L4UILvrR9w4mRWhYRE', #get new from https://console.developers.google.com/apis/credentials/key?type=CLIENT_SIDE&project=<APP_ID>
    'glang_apikey':'AIzaSyDsgX0qQmS35DW0_ETc-LoJ9E8c9TKw7h8', #get new from https://console.developers.google.com/apis/credentials/key?type=CLIENT_SIDE&project=<APP_ID>
    'gvisi_apikey':'AIzaSyDqj35BomwVIr2VIQStpluJtwFvYqHfkaU', #get new from https://console.developers.google.com/apis/credentials/key?type=CLIENT_SIDE&project=<APP_ID>
    'map_center_lat': 25.7657687, 
    'map_center_lng': -100.2050788,
    'map_zoom': 12,
    'map_zoom_mobile': 10,
    'cartodb_user': 'onesmartcity', #remember to import from onesmartcity.cartodb.com 4 tables with queried LIMIT 0, plus fix datatypes after import (e.g. public_reports pvt must be boolean)
    'cartodb_apikey': '2dd2b08fe09c23bc977b051a85b2d6d725a58a54', #get new from https://<cartodb_user>.cartodb.com/your_apps
    'cartodb_reports_table': 'public_reports',  # own cartodb account reports table
    'cartodb_pois_table': 'public_pois',  # own cartodb account pois table
    'cartodb_category_dict_table': 'cat_dict',  # own cartodb account categories table
    'cartodb_polygon_table': 'mun_poly', # own cartodb account city polygon table
    'cartodb_polygon_name': 'APO', # own cartodb account city polygon name; overwritten by cartodb_polygon_full_name, bring row as is from mexico's nacional_municipios
    'cartodb_polygon_full_name': unicode('Apodaca','utf-8'), # nom_mun @ mexico.cartodb.com table nacional_municipios
    'cartodb_polygon_cve_ent': 19,          # cve_ent @ mexico.cartodb.com table nacional_municipios
    'cartodb_polygon_cve_mun': 6,          # cve_mun @ mexico.cartodb.com table nacional_municipios
    'cartodb_cic_user': 'cicadmin',
    'cartodb_cic_reports_table': 'nl_public',
    # application endpoints
    'users_export_url': "https://one-smart-city-demo.appspot.com/_ah/api/onesmartcity/v1/export/users/86F7EB9A06F708A9673198AA8DA4ABD17E54A5AA/0/?fields=items",
    'reports_export_url': "https://one-smart-city-demo.appspot.com/_ah/api/onesmartcity/v1/export/reports/86F7EB9A06F708A9673198AA8DA4ABD17E54A5AA/0/?fields=items",
    #sendgrid integration
    'sendgrid_priority' : False,
    'sendgrid_login' : '',
    'sendgrid_passkey' : '',


    # --- --- --- stop editing --- --- ---


    # the default language code for the application.
    # should match whatever language the site uses when i18n is disabled
    'app_lang': 'en',
    # contact page email settings
    'contact_sender': '',
    # jinja2 base layout template
    'base_layout': '/materialize/users/base.html',
    'landing_layout': '/materialize/landing/base.html',
    # Locale code = <language>_<territory> (ie 'en_US')
    # to pick locale codes see http://cldr.unicode.org/index/cldr-spec/picking-the-right-language-code
    # also see http://www.sil.org/iso639-3/codes.asp
    # Language codes defined under iso 639-1 http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
    # Territory codes defined under iso 3166-1 alpha-2 http://en.wikipedia.org/wiki/ISO_3166-1
    # disable i18n if locales array is empty or None
    'locales': ['en_US', 'es_ES', 'it_IT', 'zh_CN', 'id_ID', 'fr_FR', 'de_DE', 'ru_RU', 'pt_BR', 'cs_CZ','vi_VN','nl_NL'],
    # Use a complete Google Analytics code, no just the Tracking ID
    # In config/boilerplate.py there is an example to fill out this value
    'google_analytics_code': """
        <script>
          (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
          (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
          m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
          })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

          ga('create', 'UA-73362805-1', 'auto');
          ga('send', 'pageview');

        </script>""",

    # add status codes and templates used to catch and display errors
    # if a status code is not listed here it will use the default app engine
    # stacktrace error page or browser error page
    'error_templates': {
        403: 'errors/default_error.html',
        404: 'errors/404.html',
        500: 'errors/500.html',
    },

    # Enable Federated login (OpenID and OAuth)
    # Google App Engine Settings must be set to Authentication Options: Federated Login
    'enable_federated_login': True,

    # fellas' list
    'developers': (
        ('chuycepeda', 'chuycepeda@gmail.com'),
        ('chuydelbosque', 'jesus.delbosque@gmail.com'),
    ),
    # send error emails to developers
    'send_mail_developer': False,
   
    # If true, it will write in datastore a log of every email sent
    'log_email': True,

    # If true, it will write in datastore a log of every visit
    'log_visit': True, 

    #zendesk integration
    'zendesk_imports': '',
    'zendesk_code': '',

    #mailchimp integration
    'mailchimp_code': '',



} # end config
