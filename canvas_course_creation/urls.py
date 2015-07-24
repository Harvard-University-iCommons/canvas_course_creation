"""canvas_course_creation URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from canvas_course_site_wizard import urls as ccsw_urls

urlpatterns = [
    #url(r'^admin/', include(admin.site.urls)),
    url(r'^course_creation/not_authorized/', 'icommons_ui.views.not_authorized', name="not_authorized"),
    url(r'^course_creation/pin/', include('icommons_common.auth.urls', namespace="pin")),
    url(r'^course_creation/bulk_site_creation/', include('bulk_site_creation.urls', namespace='bulk_site_creation')),
    url(r'^course_creation/canvas-course-site-wizard/', include(ccsw_urls)),
]

handler403 = 'icommons_ext_tools.views.handler403'
handler404 = 'icommons_ext_tools.views.handler404'
handler500 = 'icommons_ext_tools.views.handler500'

