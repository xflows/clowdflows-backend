from django.conf.urls import url
from django.contrib.auth import views as auth_views
import signuplogin.views as signuplogin_views

urlpatterns = [
    url(r'^signuplogin/$', signuplogin_views.signuplogin, name='signuplogin'),
]