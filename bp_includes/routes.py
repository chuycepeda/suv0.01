"""
Using redirect route instead of simple routes since it supports strict_slash
Simple route: http://webapp-improved.appspot.com/guide/routing.html#simple-routes
RedirectRoute: http://webapp-improved.appspot.com/api/webapp2_extras/routes.html#webapp2_extras.routes.RedirectRoute
"""
from webapp2_extras.routes import RedirectRoute
from bp_includes import handlers as handlers

secure_scheme = 'https'

_routes = [
    RedirectRoute('/_ah/login_required', handlers.LoginRequiredHandler),

    # Landing
    RedirectRoute('/', handlers.MaterializeLandingRequestHandler, name='landing', strict_slash=True),   
    RedirectRoute('/map/', handlers.MaterializeLandingMapRequestHandler, name='landing-map', strict_slash=True),   
    RedirectRoute('/blog/', handlers.MaterializeLandingBlogRequestHandler, name='blog', strict_slash=True),
    RedirectRoute('/blog/<post_id>/', handlers.MaterializeLandingBlogPostRequestHandler, name='blog-post', strict_slash=True),
    RedirectRoute('/contact/', handlers.MaterializeLandingContactRequestHandler, name='contact', strict_slash=True),
    RedirectRoute('/faq/', handlers.MaterializeLandingFaqRequestHandler, name='faq', strict_slash=True),
    RedirectRoute('/tou/', handlers.MaterializeLandingTouRequestHandler, name='tou', strict_slash=True),
    RedirectRoute('/privacy/', handlers.MaterializeLandingPrivacyRequestHandler, name='privacy', strict_slash=True),
    RedirectRoute('/license/', handlers.MaterializeLandingLicenseRequestHandler, name='license', strict_slash=True),
    RedirectRoute('/register/', handlers.MaterializeRegisterRequestHandler, name='register', strict_slash=True),
    RedirectRoute('/activation/<user_id>/<token>', handlers.MaterializeAccountActivationHandler, name='account-activation', strict_slash=True),
    RedirectRoute('/resend/<user_id>/<token>', handlers.ResendActivationEmailHandler, name='resend-account-activation', strict_slash=True),
    RedirectRoute('/register/referral/<user_id>/', handlers.MaterializeRegisterReferralHandler, name='register-referral', strict_slash=True),
    RedirectRoute('/activation/<ref_user_id>/<token>/<user_id>', handlers.MaterializeAccountActivationReferralHandler, name='account-activation-referral', strict_slash=True),
    RedirectRoute('/login/', handlers.MaterializeLoginRequestHandler, name='login', strict_slash=True),
    RedirectRoute('/logout/', handlers.MaterializeLogoutRequestHandler, name='logout', strict_slash=True),
    RedirectRoute('/password-reset/', handlers.PasswordResetHandler, name='password-reset', strict_slash=True),
    RedirectRoute('/password-reset/<user_id>/<token>', handlers.PasswordResetCompleteHandler, name='password-reset-check', strict_slash=True),

    # Reports
    RedirectRoute('/report/list/', handlers.MaterializeReportCardlistHandler, name='materialize-report-cardlist', strict_slash=True),
    RedirectRoute('/report/new/', handlers.MaterializeNewReportHandler, name='materialize-report-new', strict_slash=True),
    RedirectRoute('/report/image/upload/<report_id>', handlers.MaterializeReportUploadImageHandler, name='report-image-upload', strict_slash=True),
    RedirectRoute('/report/attachment/upload/<att_id>', handlers.MaterializeReportUploadAttachmentHandler, name='report-attachment-upload', strict_slash=True),
    RedirectRoute('/report/success/', handlers.MaterializeNewReportSuccessHandler, name='materialize-report-success', strict_slash=True),
    RedirectRoute('/report/categories/', handlers.MaterializeCategoriesHandler, name='materialize-report-categories', strict_slash=True),
    RedirectRoute('/report/comments/<report_id>/', handlers.MaterializeReportCommentsHandler, name='materialize-report-comments', strict_slash=True),
    RedirectRoute('/report/comments/ticket/<ticket>/', handlers.MaterializeReportCommentsByTicketHandler, name='materialize-report-comments-ticket', strict_slash=True),
    RedirectRoute('/report/comment/add/', handlers.MaterializeReportCommentsAddHandler, name='materialize-report-comments-add', strict_slash=True),
    RedirectRoute('/report/follow/', handlers.MaterializeFollowRequestHandler, name='materialize-report-follow', strict_slash=True),   
    RedirectRoute('/report/rate/', handlers.MaterializeRateRequestHandler, name='materialize-report-rate', strict_slash=True),   
    RedirectRoute('/report/author/<uuid>', handlers.MaterializeReportAuthorRequestHandler, name='materialize-report-author', strict_slash=True),   
    RedirectRoute('/report/urgent/', handlers.MaterializeUrgentRequestHandler, name='materialize-report-urgent', strict_slash=True),   
    RedirectRoute('/report/log/delete/<log_id>/', handlers.MaterializeLogChangeDeleteHandler, name='materialize-log-delete', strict_slash=True, handler_method='edit'),
    RedirectRoute('/report/att/delete/<att_id>/', handlers.MaterializeAttachmentDeleteHandler, name='materialize-att-delete', strict_slash=True, handler_method='edit'),
    
    # Petitions
    RedirectRoute('/petition/list/', handlers.MaterializePetitionCardlistHandler, name='materialize-petition-cardlist', strict_slash=True),
    RedirectRoute('/petition/new/', handlers.MaterializeNewPetitionHandler, name='materialize-petition-new', strict_slash=True),
    RedirectRoute('/petition/image/upload/<petition_id>', handlers.MaterializePetitionUploadImageHandler, name='petition-image-upload', strict_slash=True),
    RedirectRoute('/petition/success/', handlers.MaterializeNewPetitionSuccessHandler, name='materialize-petition-success', strict_slash=True),
    RedirectRoute('/petition/topics/', handlers.MaterializeTopicsHandler, name='materialize-petition-topics', strict_slash=True),

    # Transparency
    RedirectRoute('/transparency/city/', handlers.MaterializeTransparencyCityHandler, name='materialize-transparency-city', strict_slash=True),
    RedirectRoute('/transparency/budget/', handlers.MaterializeTransparencyBudgetHandler, name='materialize-transparency-budget', strict_slash=True),
    RedirectRoute('/transparency/budget/new/', handlers.MaterializeTransparencyBudgetNewHandler, name='materialize-transparency-budget-new', strict_slash=True),
    RedirectRoute('/transparency/initiatives/', handlers.MaterializeTransparencyInitiativesHandler, name='materialize-transparency-init', strict_slash=True),
    RedirectRoute('/transparency/initiatives/<initiative_id>/', handlers.MaterializeTransparencyInitiativeHandler, name='materialize-transparency-initiative', strict_slash=True, handler_method='edit'),
    RedirectRoute('/transparency/areas/', handlers.MaterializeAreasHandler, name='materialize-transparency-areas', strict_slash=True),
    RedirectRoute('/transparency/budget/user.json', handlers.MaterializeUserBudgetHandler, name='materialize-transparency-budget-user', strict_slash=True),

    # User: all
    RedirectRoute('/user/welcome/', handlers.MaterializeWelcomeRequestHandler, name='materialize-welcome', strict_slash=True),
    RedirectRoute('/user/profile/<profile_id>/', handlers.MaterializeProfileRequestHandler, name='materialize-profile', strict_slash=True),
    RedirectRoute('/user/referrals/', handlers.MaterializeReferralsRequestHandler, name='materialize-referrals', strict_slash=True),
    RedirectRoute('/user/reports/', handlers.MaterializeReportsRequestHandler, name='materialize-reports', strict_slash=True),
    RedirectRoute('/user/reports/<report_id>/', handlers.MaterializeReportsEditRequestHandler, name='materialize-reports-edit', strict_slash=True),
    RedirectRoute('/user/petitions/', handlers.MaterializePetitionsRequestHandler, name='materialize-petitions', strict_slash=True),
    RedirectRoute('/user/settings/profile/', handlers.MaterializeSettingsProfileRequestHandler, name='materialize-settings-profile', strict_slash=True),
    RedirectRoute('/user/settings/social/', handlers.MaterializeSettingsSocialRequestHandler, name='materialize-settings-social', strict_slash=True),
    RedirectRoute('/user/settings/email/', handlers.MaterializeSettingsEmailRequestHandler, name='materialize-settings-email', strict_slash=True),
    RedirectRoute('/user/settings/password/', handlers.MaterializeSettingsPasswordRequestHandler, name='materialize-settings-password', strict_slash=True),
    RedirectRoute('/user/settings/delete/', handlers.MaterializeSettingsDeleteRequestHandler, name='materialize-settings-delete', strict_slash=True),
    RedirectRoute('/user/settings/referrals/', handlers.MaterializeSettingsReferralsRequestHandler, name='materialize-settings-referrals', strict_slash=True),
    RedirectRoute('/user/settings/account/', handlers.MaterializeSettingsAccountRequestHandler, name='materialize-settings-account', strict_slash=True),
    RedirectRoute('/user/change-email/<user_id>/<encoded_email>/<token>', handlers.MaterializeEmailChangedCompleteHandler, name='materialize-email-changed-check', strict_slash=True),    
    # User: special access
    RedirectRoute('/user/organization/directory/', handlers.MaterializeOrganizationDirectoryRequestHandler, name='materialize-organization-directory', strict_slash=True),
    RedirectRoute('/user/organization/dashboard/', handlers.MaterializeOrganizationDashboardRequestHandler, name='materialize-organization-dashboard', strict_slash=True),
    RedirectRoute('/user/organization/report/', handlers.MaterializeOrganizationNewReportHandler, name='materialize-organization-report', strict_slash=True),
    RedirectRoute('/user/organization/report/success/', handlers.MaterializeOrganizationNewReportSuccessHandler, name='materialize-organization-report-success', strict_slash=True),
    RedirectRoute('/user/organization/urgents/', handlers.MaterializeOrganizationUrgentsHandler, name='materialize-organization-urgents', strict_slash=True),
    RedirectRoute('/user/organization/manual/', handlers.MaterializeOrganizationManualHandler, name='materialize-organization-manual', strict_slash=True),
    RedirectRoute('/user/organization/users/', handlers.MaterializeOrganizationUsersHandler, name='materialize-organization-users', strict_slash=True),
    RedirectRoute('/user/organization/users/<user_id>/', handlers.MaterializeOrganizationUserReportsHandler, name='materialize-organization-user-reports', strict_slash=True),
    RedirectRoute('/user/organization/export/reports/', handlers.MaterializeOrganizationExportReportsHandler, name='materialize-organization-export-reports', strict_slash=True),
    RedirectRoute('/user/organization/export/users/', handlers.MaterializeOrganizationExportUsersHandler, name='materialize-organization-export-users', strict_slash=True),
    # User: secretary access
    RedirectRoute('/user/secretary/inbox/', handlers.MaterializeOrganizationInboxRequestHandler, name='materialize-secretary-inbox', strict_slash=True),
    RedirectRoute('/user/secretary/report/<report_id>/', handlers.MaterializeSecretaryReportRequestHandler, name='materialize-secretary-report', strict_slash=True, handler_method='edit'),
    # User: agent access
    RedirectRoute('/user/agent/inbox/', handlers.MaterializeOrganizationInboxRequestHandler, name='materialize-agent-inbox', strict_slash=True),
    RedirectRoute('/user/agent/report/<report_id>/', handlers.MaterializeAgentReportRequestHandler, name='materialize-agent-report', strict_slash=True, handler_method='edit'),
    # User: operator access
    RedirectRoute('/user/operator/inbox/', handlers.MaterializeOrganizationInboxRequestHandler, name='materialize-operator-inbox', strict_slash=True),
    RedirectRoute('/user/operator/report/<report_id>/', handlers.MaterializeOperatorReportRequestHandler, name='materialize-operator-report', strict_slash=True, handler_method='edit'),
    # User: callcenter access
    RedirectRoute('/user/callcenter/inbox/', handlers.MaterializeOrganizationInboxRequestHandler, name='materialize-callcenter-inbox', strict_slash=True),
    RedirectRoute('/user/callcenter/report/<report_id>/', handlers.MaterializeCallCenterReportRequestHandler, name='materialize-callcenter-report', strict_slash=True, handler_method='edit'),
    # User: callcenter access for social networks
    RedirectRoute('/user/callcenter/facebook/', handlers.MaterializeCallCenterFacebookRequestHandler, name='materialize-callcenter-facebook', strict_slash=True),
    RedirectRoute('/user/callcenter/twitter/', handlers.MaterializeCallCenterTwitterRequestHandler, name='materialize-callcenter-twitter', strict_slash=True),
    # User: callcenter access for initiatives
    RedirectRoute('/user/callcenter/initiatives/', handlers.MaterializeInitiativesHandler, name='materialize-callcenter-initiatives', strict_slash=True),
    RedirectRoute('/user/callcenter/initiatives/<init_id>/', handlers.MaterializeInitiativeEditHandler, name='materialize-callcenter-initiative-edit', strict_slash=True, handler_method='edit'),
    RedirectRoute('/user/callcenter/initiatives/image/upload/<initiative_id>/', handlers.MaterializeInitiativeImageUploadHandler, name='materialize-callcenter-initiative-image-upload', strict_slash=True),
    # User: callcenter access for geo transparency
    RedirectRoute('/user/callcenter/geom/', handlers.MaterializeGeomHandler, name='materialize-callcenter-geom', strict_slash=True),
    RedirectRoute('/user/callcenter/geom/edit/', handlers.MaterializeGeomEditHandler, name='materialize-callcenter-geom-edit', strict_slash=True),

    #Cronjobs
    RedirectRoute('/cronjob-auto72/', handlers.Auto72CronjobHandler, name='cronjob-auto72', strict_slash=True),  
    RedirectRoute('/cronjob-forgot/', handlers.ForgotCronjobHandler, name='cronjob-forgot', strict_slash=True),  
    
    #Taskqueues
    RedirectRoute('/taskqueue-auto72/', handlers.Auto72Handler, name='taskqueue-auto72', strict_slash=True),
    RedirectRoute('/taskqueue-forgot/', handlers.ForgotHandler, name='taskqueue-forgot', strict_slash=True),
    RedirectRoute('/taskqueue-send-email/', handlers.SendEmailHandler, name='taskqueue-send-email', strict_slash=True),

    #API
    RedirectRoute('/api/', handlers.APIDocHandler, name='api-doc', strict_slash=True),
    RedirectRoute('/mbapi/in/', handlers.APIIncomingHandler, name='mbapi-in', strict_slash=True),
    RedirectRoute('/mbapi/out/', handlers.APIOutgoingHandler, name='mbapi-out', strict_slash=True),
    RedirectRoute('/mbapi/test/', handlers.APITestingHandler, name='mbapi-test', strict_slash=True),
    RedirectRoute('/mboilerplate/users/', handlers.MBoiUsersHandler, name='mboi-users', strict_slash=True),

    # Blob handlers for media
    RedirectRoute('/media/serve/<kind>/<media_id>/', handlers.MediaDownloadHandler, name='media-serve', strict_slash=True),
    RedirectRoute('/blobstore/form/', handlers.BlobFormHandler, name='blob-form', strict_slash=True),
    RedirectRoute('/blobstore/upload/', handlers.BlobUploadHandler, name='blob-upload', strict_slash=True),
    RedirectRoute('/blobstore/serve/<photo_key>', handlers.BlobDownloadHandler, name='blob-serve', strict_slash=True),

    # Statics
    RedirectRoute(r'/robots.txt', handlers.RobotsHandler, name='robots', strict_slash=True),
    RedirectRoute(r'/humans.txt', handlers.HumansHandler, name='humans', strict_slash=True),
    RedirectRoute(r'/sitemap.xml', handlers.SitemapHandler, name='sitemap', strict_slash=True),
    RedirectRoute(r'/crossdomain.xml', handlers.CrossDomainHandler, name='crossdomain', strict_slash=True),

    #Email Bouncer
    RedirectRoute('/_ah/bounce/', handlers.LogBounceHandler, name='bouncer', strict_slash=True),
        
]

def get_routes():
    return _routes

def add_routes(app):
    if app.debug:
        secure_scheme = 'http'
    for r in _routes:
        app.router.add(r)
