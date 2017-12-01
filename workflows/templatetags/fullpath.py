from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def static_fullpath(request, path):
    protocol = 'https://' if request.is_secure() else 'http://'
    host = request.get_host()
    static_url = settings.STATIC_URL
    return protocol + host + static_url + path
