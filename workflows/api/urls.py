from django.conf.urls import include, url
from rest_framework import routers
import rest_framework.authtoken.views as drf_views

from workflows.api import views

router = routers.DefaultRouter()

router.register(r'inputs', views.InputViewSet, base_name='input')
router.register(r'abstract_inputs', views.AbstractInputViewSet, base_name='abstractinput')
router.register(r'abstract_outputs', views.AbstractOutputViewSet, base_name='abstractoutput')
router.register(r'outputs', views.OutputViewSet, base_name='output')
router.register(r'users', views.UserViewSet, base_name='user')
router.register(r'workflows', views.WorkflowViewSet, base_name='workflow')
router.register(r'widgets', views.WidgetViewSet, base_name='widget')
router.register(r'connections', views.ConnectionViewSet, base_name='connection')
router.register(r'inputs', views.InputViewSet, base_name='input')
router.register(r'outputs', views.OutputViewSet, base_name='output')
router.register(r'widget-library', views.CategoryViewSet, base_name='widget-library')

urlpatterns = [
   url(r'^register/$', views.user_register, name='api-user-register'),
   url(r'^login/$', views.user_login, name='api-user-login'),
   url(r'^logout/$', views.user_logout, name='api-user-logout'),
   url(r'^', include(router.urls)),
   url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
   url(r'^api-token-auth/', drf_views.obtain_auth_token)
]
