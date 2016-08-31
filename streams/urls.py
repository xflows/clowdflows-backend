from django.conf.urls import include, url
import streams.views as streams_views

urlpatterns = [
    url(r'^data/(?P<stream_id>[0-9]+)/(?P<widget_id>[0-9]+)/$', streams_views.stream_widget_visualization, name='stream widget visualization'),
]
