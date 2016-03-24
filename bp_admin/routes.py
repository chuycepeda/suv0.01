from webapp2_extras.routes import RedirectRoute
import operator
import users
import admin
import blog
import logsemails
import logsvisits
import crontasks
import tools


_routes = [
    RedirectRoute('/admin/', admin.AdminRequestHandler, name='admin', strict_slash=True),
    RedirectRoute('/admin/stats/reports/', admin.AdminStatsReportsHandler, name='admin-stats-reports', strict_slash=True),
    RedirectRoute('/admin/stats/organization/', admin.AdminStatsOrganizationHandler, name='admin-stats-organization', strict_slash=True),
    RedirectRoute('/admin/send/email/', admin.AdminSendEmailListHandler, name='admin-send-email', strict_slash=True),
    RedirectRoute('/admin/logout/', admin.AdminLogoutHandler, name='admin-logout', strict_slash=True),
    RedirectRoute('/admin/manual/', admin.AdminManualHandler, name='admin-manual', strict_slash=True),


    # CONFIG Brand
    RedirectRoute('/admin/brand/', operator.AdminBrandHandler, name='admin-brand', strict_slash=True),

    # CONFIG Categories
    RedirectRoute('/admin/categories/', operator.AdminCategoriesHandler, name='admin-categories', strict_slash=True),
    RedirectRoute('/admin/categories/<group_id>/', operator.AdminSubcategoriesHandler, name='admin-category-edit', strict_slash=True, handler_method='edit'),
    RedirectRoute('/admin/categories/subcategory/<category_id>/', operator.AdminSubcategoriesEditHandler, name='admin-subcategory-edit', strict_slash=True, handler_method='edit'),
    
    # CONFIG Topics
    RedirectRoute('/admin/topics/', operator.AdminTopicsHandler, name='admin-topics', strict_slash=True),
    RedirectRoute('/admin/topics/<topic_id>/', operator.AdminTopicEditHandler, name='admin-topic-edit', strict_slash=True, handler_method='edit'),

    # CONFIG Initiatives
    RedirectRoute('/admin/areas/', operator.AdminAreasHandler, name='admin-areas', strict_slash=True),
    RedirectRoute('/admin/areas/<area_id>/', operator.AdminAreaEditHandler, name='admin-area-edit', strict_slash=True, handler_method='edit'),
    
    # CONFIG Organization
    RedirectRoute('/admin/organization/', operator.AdminOrganizationHandler, name='admin-organization', strict_slash=True),
    RedirectRoute('/admin/organization/secretary/<secretary_id>/', operator.AdminOrganizationSecretaryHandler, name='admin-secretary-edit', strict_slash=True, handler_method='edit'),
    RedirectRoute('/admin/organization/agency/<agency_id>/', operator.AdminOrganizationAgencyHandler, name='admin-agency-edit', strict_slash=True, handler_method='edit'),
    RedirectRoute('/admin/organization/operator/<operator_id>/', operator.AdminOrganizationOperatorHandler, name='admin-operator-edit', strict_slash=True, handler_method='edit'),
    
    # CONFIG Callcenter
    RedirectRoute('/admin/callcenter/', operator.AdminCallCenterHandler, name='admin-callcenter', strict_slash=True),
    RedirectRoute('/admin/callcenter/<operator_id>/', operator.AdminCallCenterOperatorHandler, name='admin-callcenter-edit', strict_slash=True, handler_method='edit'),
    
    # OPERATIONS Reports
    RedirectRoute('/admin/map/', operator.AdminMapHandler, name='admin-map', strict_slash=True),
    RedirectRoute('/admin/reports/', operator.AdminReportsHandler, name='admin-reports', strict_slash=True),
    RedirectRoute('/admin/reports/<report_id>/', operator.AdminReportEditHandler, name='admin-report-edit', strict_slash=True, handler_method='edit'),
    
    # OPERATIONS Petitions
    RedirectRoute('/admin/petitions/', operator.AdminPetitionsHandler, name='admin-petitions', strict_slash=True),
    RedirectRoute('/admin/petitions/<petition_id>/', operator.AdminPetitionsEditHandler, name='admin-petitions-edit', strict_slash=True, handler_method='edit'),

    # OPERATIONS Initiatives
    RedirectRoute('/admin/initiatives/', operator.AdminInitiativesHandler, name='admin-initiatives', strict_slash=True),
    RedirectRoute('/admin/initiatives/<init_id>/', operator.AdminInitiativeEditHandler, name='admin-initiative-edit', strict_slash=True, handler_method='edit'),
    
    # BLOG
    RedirectRoute('/admin/blog/', blog.AdminBlogHandler, name='admin-blog', strict_slash=True),
    RedirectRoute('/admin/blog/<post_id>/', blog.AdminBlogEditHandler, name='admin-blog-edit', strict_slash=True),
    RedirectRoute('/admin/blog/upload/<post_id>/', blog.AdminBlogUploadHandler, name='admin-blog-upload', strict_slash=True),
    RedirectRoute('/admin/tools/css/', tools.AdminCSSHandler, name='admin-tools-css', strict_slash=True),
    RedirectRoute('/admin/tools/icons/', tools.AdminIconsHandler, name='admin-tools-icons', strict_slash=True),
    RedirectRoute('/admin/tools/media/', tools.AdminMediaHandler, name='admin-tools-media', strict_slash=True),

    # PLATFORM USAGE & LOGS
    RedirectRoute('/admin/users/', users.AdminUserListHandler, name='admin-users-list', strict_slash=True),
    RedirectRoute('/admin/users/export/', users.AdminExportUsers, name='admin-export-users', strict_slash=True),
    RedirectRoute('/admin/users/<user_id>/', users.AdminUserEditHandler, name='admin-user-edit', strict_slash=True, handler_method='edit'),
    RedirectRoute('/admin/logs/emails/', logsemails.AdminLogsEmailsHandler, name='admin-logs-emails', strict_slash=True),
    RedirectRoute('/admin/logs/emails/<email_id>/', logsemails.AdminLogsEmailViewHandler, name='admin-logs-email-view', strict_slash=True),
    RedirectRoute('/admin/logs/visits/', logsvisits.AdminLogsVisitsHandler, name='admin-logs-visits', strict_slash=True),
    
    # HELPERS
    RedirectRoute('/admin/crontasks/cleanuptokens/', crontasks.AdminCleanupTokensHandler, name='admin-crontasks-cleanuptokens', strict_slash=True),
]

def get_routes():
    return _routes

def add_routes(app):
    for r in _routes:
        app.router.add(r)
