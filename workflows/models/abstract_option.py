from django.db import models

from workflows.models.abstract_input import AbstractInput
from workflows.models.abstract_widget import AbstractWidget


class AbstractOption(models.Model):
    abstract_input = models.ForeignKey(AbstractInput, related_name="options")
    name = models.CharField(max_length=200)
    value = models.TextField(blank=True)

    uid = models.CharField(max_length=250, blank=True, default='')

    def __str__(self):
        return str(self.name)

    class Meta:
        ordering = ['name']

