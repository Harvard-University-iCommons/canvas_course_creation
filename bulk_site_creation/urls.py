from django.conf.urls import url

from bulk_site_creation import views, api


urlpatterns = [
    url(r'^lti_auth_error$', views.lti_auth_error, name='lti_auth_error'),
    url(r'^tool_config$', views.tool_config, name='tool_config'),
    url(r'^lti_launch$', views.lti_launch, name='lti_launch'),
    url(r'^index$', views.index, name='index'),
    url(r'^audit', views.audit, name='audit'),
    url(r'^course_selection$', views.course_selection, name='course_selection'),
    url(r'^create_job$', views.create_job, name='create_job'),
    url(r'^bulk_job_detail/(?P<bulk_job_id>[\d]+)$', views.bulk_job_detail, name='bulk_job_detail'),
    url(r'^api/schools$', api.schools, name='api_schools'),
    url(r'^api/schools/(?P<sis_account_id>[:\w]+)/terms$', api.terms, name='api_terms'),
    url(r'^api/schools/(?P<sis_account_id>[:\w]+)/departments$', api.departments, name='api_departments'),
    url(r'^api/schools/(?P<sis_account_id>[:\w]+)/course_groups$', api.course_groups, name='api_course_groups'),
    url(r'^api/terms/(?P<sis_term_id>[:\w]+)/accounts/(?P<sis_account_id>[:\w]+)/course_instances$', api.course_instances, name='api_course_instances'),
    url(r'^api/terms/(?P<sis_term_id>[:\w]+)/accounts/(?P<sis_account_id>[:\w]+)/course_instance_summary$', api.course_instance_summary, name='api_course_instance_summary'),
    url(r'^api/bulk_jobs/(?P<bulk_job_id>[\d]+)/course_jobs$', api.course_jobs, name='api_course_jobs'),
]
