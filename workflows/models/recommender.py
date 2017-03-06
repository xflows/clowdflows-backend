from django.db import models

from workflows.models import AbstractInput
from workflows.models import AbstractOutput


class Recommender(models.Model):
    inp = models.ForeignKey(AbstractInput, related_name='input')
    out = models.ForeignKey(AbstractOutput, related_name='output')
    count = models.IntegerField()

