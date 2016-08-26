from django.conf.urls import patterns, include, url
from rest_framework import routers
from rest_framework.authtoken import views
from workflows import api_views, api_workflow_viewset, api_widget_viewset, api_connection_viewset

router = routers.DefaultRouter()

router.register(r'inputs', api_views.InputViewSet, base_name='input')
router.register(r'outputs', api_views.OutputViewSet, base_name='output')
router.register(r'users', api_views.UserViewSet, base_name='user')
router.register(r'workflows', api_workflow_viewset.WorkflowViewSet, base_name='workflow')
router.register(r'widgets', api_widget_viewset.WidgetViewSet, base_name='widget')
router.register(r'connections', api_connection_viewset.ConnectionViewSet, base_name='connection')
router.register(r'inputs', api_views.InputViewSet, base_name='input')
router.register(r'outputs', api_views.OutputViewSet, base_name='output')
router.register(r'widget-library', api_views.CategoryViewSet, base_name='widget-library')

urlpatterns = patterns('',
   url(r'^register/$', api_views.user_register),
   url(r'^login/$', api_views.user_login),
   url(r'^logout/$', api_views.user_logout),
   url(r'^', include(router.urls)),
   url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
   url(r'^api-token-auth/', views.obtain_auth_token)
)
