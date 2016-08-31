from django.conf.urls import include, url
import workflows.latino.views as latino_views

urlpatterns = [
    url(r'^get-adc-index/widget(?P<widget_id>[0-9]+)/nx/Index.html$', latino_views.get_adc_index, name='get adc index'),
    url(r'^get-adc-index/widget(?P<widget_id>[0-9]+)/(?P<narrow_doc>n?)x/Index.html$', latino_views.get_adc_index, name='get adc index'),
    url(r'^get-adc-index/widget(?P<widget_id>[0-9]+)/(?P<narrow_doc>n?)x/Index(?P<document_id_from>[0-9]+)-(?P<document_id_to>[0-9]+).html$', latino_views.get_adc_index, name='get adc index'),
    url(r'^get-adc-index/widget(?P<widget_id>[0-9]+)/(?P<narrow_doc>n?)x/Document(?P<document_id>[0-9]+).html', latino_views.get_adc_page, name='get adc page'),
]