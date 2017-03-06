from django.db import models

from workflows.models.abstract_widget import AbstractWidget


class AbstractOutput(models.Model):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=3)
    description = models.TextField(blank=True)
    variable = models.CharField(max_length=50,
                                help_text='The variable attribute of both the input and the output are important because this is how the data will be accessed in the python function that is executed when the widget runs.')
    widget = models.ForeignKey(AbstractWidget, related_name="outputs")

    order = models.PositiveIntegerField(default=1)

    uid = models.CharField(max_length=250, blank=True, default='')

    class Meta:
        ordering = ('order',)

    def __unicode__(self):
        return unicode(self.name)
