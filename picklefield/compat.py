import django
from django.db import models
from django.utils import six

from pickle import loads, dumps  # noqa

if django.VERSION >= (1, 8):
    _PickledObjectField = models.Field
else:
    _PickledObjectField = six.with_metaclass(models.SubfieldBase, models.Field)
