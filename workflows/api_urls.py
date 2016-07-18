from django.conf.urls import patterns, include, url
from rest_framework import routers
from workflows import api_views

router = routers.DefaultRouter()
router.register(r'users', api_views.UserViewSet)
router.register(r'workflows', api_views.WorkflowViewSet)
router.register(r'widgets', api_views.WidgetViewSet)
router.register(r'connections', api_views.ConnectionViewSet)
router.register(r'inputs', api_views.InputViewSet)
router.register(r'outputs', api_views.OutputViewSet)
router.register(r'abstract-widget', api_views.AbstractWidgetViewSet)
router.register(r'abstract-input', api_views.AbstractInputViewSet)
router.register(r'abstract-option', api_views.AbstractOptionViewSet)
router.register(r'abstract-output', api_views.AbstractOutputViewSet)
router.register(r'widget-library', api_views.CategoryViewSet)

urlpatterns = patterns('',
   url(r'^register/$', api_views.user_register),
   url(r'^login/$', api_views.user_login),
   url(r'^logout/$', api_views.user_logout),
   url(r'^', include(router.urls)),
   url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
)
