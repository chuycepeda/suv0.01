"""
============= DON'T MODIFY THIS FILE ============
This is the boilerplate default configuration file.
Changes and additions to settings should be done in
/bp_content/themes/<YOUR_THEME>/config/ rather than this config.
"""

import os

config = {

    # webapp2 sessions
    'webapp2_extras.sessions': {'secret_key': '_PUT_KEY_HERE_YOUR_SECRET_KEY_'},

    # webapp2 authentication
    'webapp2_extras.auth': {'user_model': 'bp_includes.models.User',
                            'cookie_name': 'session_name'},

    # jinja2 templates
    'webapp2_extras.jinja2': {'template_path': ['bp_admin/templates', 'bp_content/themes/%s/templates' % os.environ['theme']],
                              'environment_args': {'extensions': ['jinja2.ext.i18n']}},

    # application name
    'app_name':  unicode('Mi Ciudad en Línea','utf-8'),
    'city_name':  unicode('Mi Ciudad','utf-8'),
    'city_url':  'http://onesmart.city',
    'city_slogan':  'Slogan de Mi Ciudad',
    'city_splash':  'http://one-smart-city-demo.appspot.com/default/materialize/images/landing/city.jpeg',
    'city_splash_secondary':  'http://one-smart-city-demo.appspot.com/default/materialize/images/landing/splash_secondary.png',
    'app_id': 'one-smart-city-demo',
    # application branding 
    'brand_logo': 'http://one-smart-city-demo.appspot.com/default/materialize/images/favicon/rhexlogo.png',
    'brand_favicon': 'http://one-smart-city-demo.appspot.com/default/materialize/images/favicon/rhexlogo.png',
    'brand_color' : '#DD3DA1',
    'brand_secondary_color' : '#4254A0',
    'brand_tertiary_color' : '#A5AFDC',
    'landing_skin': '',
    'video_url':  'https://www.youtube.com/embed/RX7JMnsI7K0',
    'video_playlist':  'https://www.youtube.com/watch?v=FxozM2hAHXE',
    'right_sidenav_msg': unicode("""
        <p class="center"><img src="/default/materialize/images/favicon/rhexlogo.png" style="margin-top:3px; margin-left:5px; height:60px; "></p>
        <p>
            A través de tu portal de atención, puedes contribuir a transformar Mi Ciudad en la ciudad que todos queremos. 
        </p>
        <p>
            Reportando, administrando y dando seguimiento a las necesidades que aquejan a nuestra comunidad, juntos cuidadanos y gobierno podremos ser más eficientes y demostrar que estamos para servir.
        </p>
        <p>
            ¡Felicidades por ser parte! Comienza a contribuir hacia la mejora de nuestra ciudad Mi Ciudad.
        </p>
    """,'utf-8'),
    # application on social media
    'twitter_url': 'https://twitter.com/ciudadguadalupe',
    'twitter_appID': '201422020200516',
    'twitter_handle': 'ciudadguadalupe',
    'facebook_url': 'https://www.facebook.com/GuadalupeNuevoLeon',
    'facebook_handle':'GuadalupeNuevoLeon',
    'facebook_appID': '201422020200516',
    'google_clientID': '470636988216-hlgtlpo9rj85k27c5cm8r7abjceatndo.apps.googleusercontent.com',
    'indicoio_apikey': 'bfb2bd9d8307bc472297287bac8f68c9',  
    #cartodb integration
    'map_center_lat': 25.683956577519417, 
    'map_center_lng': -100.20524472216799,
    'cartodb_user': 'onesmartcity',
    'cartodb_apikey': '2dd2b08fe09c23bc977b051a85b2d6d725a58a54',
    'cartodb_reports_table': 'public_reports',
    'cartodb_category_dict_table': 'cat_dict',
    'cartodb_polygon_table': 'mun_poly',
    'cartodb_polygon_name': 'GPE',
    'cartodb_has_cic': False,
    'cartodb_cic_user': 'cicadmin',
    'cartodb_cic_reports_table': 'nl_public',
    # contact page email settings
    'contact_sender': '',
    'contact_recipient': "uno@onesmart.city",  
    # application on the web
    'meta_tags_code': """
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
            <meta name="description" content="This an amazing, magical, materialized app built with Mboilerplate for the Google AppEngine." />
            <meta name="keywords" content="mboilerplate, appengine, materialize, boilerplate, webcomponents, google cloud, gae"/>
            <meta property="og:site_name" content="demo.onesmart.city"/>
            <meta property="og:title" content="OneSmart.City"/>
            <meta property="og:type" content="website"/>
            <meta property="og:description" content="This an amazing, magical, materialized app built with Mboilerplate for the Google AppEngine."/>
            <meta property="og:url" content="http://demo.onesmart.city"/>
            <meta property="og:image" content="http://demo.onesmart.city/{{theme}}/materialize/images/landing/250H.png"/>
            <meta name="twitter:card" content="summary_large_image">
            <meta name="twitter:site" content="This an amazing, magical, materialized app built with Mboilerplate for the Google AppEngine.">
            <meta name="twitter:creator" content="@chuycepeda">
            <meta name="twitter:title" content="OneSmart.City">
            <meta name="twitter:description" content="This an amazing, magical, materialized app built with Mboilerplate for the Google AppEngine.">
            <meta name="twitter:image" content="http://demo.onesmart.city/{{theme}}/materialize/images/landing/250H.png">
            <meta property="twitter:url" content="http://demo.onesmart.city"/>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta name="viewport" content="width=device-width, minimum-scale=1.0, initial-scale=1.0, user-scalable=yes">""",
    #application endpoints
    'users_export_url': "https://one-smart-city-demo.appspot.com/_ah/api/one-smart-city-demo/v1/users?fields=items",
    'reports_export_url': "https://one-smart-city-demo.appspot.com/_ah/api/one-smart-city-demo/v1/reports?fields=items",
    # the default language code for the application.
    # should match whatever language the site uses when i18n is disabled
    'app_lang': 'en',

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

    # get your own recaptcha keys by registering at http://www.google.com/recaptcha/
    'captcha_public_key': "6LcMfv0SAAAAAGMJ9i-g5aJhXFvSHpPsqDLOHTUD",
    'captcha_private_key': "6LcMfv0SAAAAALMUmCmFt5NOAw_ZTHabWRHAFJI6",

    # Password AES Encryption Parameters
    # aes_key must be only 16 (*AES-128*), 24 (*AES-192*), or 32 (*AES-256*) bytes (characters) long.
    'aes_key': "A1BED038702434F8358F799990208234",
    'salt': "634907BCD5EC4F29BE5DE8ED97637366B2C18E42E14EEEBA3925E9E0485FCCC9480BFC6CB2D8E4E8A9464F3C10ADFA0DB97451C8DB1033A6C2D6C4231D0645EF",

    # send error emails to developers
    'send_mail_developer': False,

    #bitly Login & API KEY, get them from your bitly account under settings/advanced.
    'bitly_login' : "mboilerplate",
    'bitly_apikey' : "R_c7794de8fef148c6b950578064492e95",

    #slack webhook url
    'slack_webhook_url' : "https://hooks.slack.com/services/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",

    # fellas' list
    'developers': (
        ('chuycepeda', 'chuycepeda@gmail.com'),
        ('chuydelbosque', 'jesus.delbosque@gmail.com'),
    ),
   
    # If true, it will write in datastore a log of every email sent
    'log_email': True,

    # If true, it will write in datastore a log of every visit
    'log_visit': True,    
    
    #sendgrid integration
    'sendgrid_login' : '',
    'sendgrid_passkey' : '',

    #zendesk integration
    'zendesk_imports': '',
    'zendesk_code': '',

    #mailchimp integration
    'mailchimp_code': '',



} # end config
