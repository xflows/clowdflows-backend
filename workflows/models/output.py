from django.db import models

from picklefield import PickledObjectField
from workflows.models import Input, AbstractOutput


class Output(models.Model):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=5)
    description = models.TextField(blank=True)
    variable = models.CharField(max_length=50)
    widget = models.ForeignKey('Widget', related_name="outputs")
    value = PickledObjectField(null=True)
    abstract_output = models.ForeignKey('AbstractOutput',blank=True, null=True)

    inner_input = models.ForeignKey(Input, related_name="outer_output_rel", blank=True, null=True)  # za subprocess
    outer_input = models.ForeignKey(Input, related_name="inner_output_rel", blank=True, null=True)  # za subprocess
    order = models.PositiveIntegerField(default=1)

    def import_from_json(self, json_data, input_conversion, output_conversion):
        self.name = json_data['name']
        self.short_name = json_data['short_name']
        self.description = json_data['description']
        self.variable = json_data['variable']
        if json_data('abstract_output_uid'):
            self.abstract_output= AbstractOutput.objects.get(uid=json_data['abstract_output_uid'])
        self.order = json_data['order']
        self.save()
        output_conversion[json_data['pk']] = self.pk
        if json_data['outer_input']:
            self.outer_input = Input.objects.get(pk=input_conversion[json_data['outer_input']])
            self.outer_input.inner_output = self
            self.outer_input.save()
            self.save()

    def export(self):
        d = {}
        d['name'] = self.name
        d['short_name'] = self.short_name
        d['description'] = self.description
        d['variable'] = self.variable
        if self.abstract_output:
            d['abstract_output_uid'] = self.abstract_output.uid
        d['order'] = self.order
        d['pk'] = self.pk
        try:
            d['inner_input'] = self.inner_input.pk
        except:
            d['inner_input'] = None
        try:
            d['outer_input'] = self.outer_input.pk
        except:
            d['outer_input'] = None
        return d

    class Meta:
        ordering = ('order',)

    def __unicode__(self):
        return unicode(self.name)

