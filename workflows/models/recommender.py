from django.db import models

from workflows.models import AbstractInput, Connection, Input, Output
from workflows.models import AbstractOutput


class Recommender(models.Model):
    abstract_input = models.ForeignKey(AbstractInput, related_name='recommender')
    abstract_output = models.ForeignKey(AbstractOutput, related_name='recommender')
    count = models.IntegerField()

