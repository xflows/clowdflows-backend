from django.db import models

from picklefield import PickledObjectField
from workflows.models import AbstractInput
from workflows.models.option import Option


class Input(models.Model):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=3)
    description = models.TextField(blank=True, null=True)
    variable = models.CharField(max_length=50)
    widget = models.ForeignKey('Widget', related_name="inputs")
    required = models.BooleanField(default=False)
    parameter = models.BooleanField(default=False)
    value = PickledObjectField(null=True)
    multi_id = models.IntegerField(default=0)
    abstract_input = models.ForeignKey('AbstractInput', blank=True, null=True)

    inner_output = models.ForeignKey('Output', related_name="outer_input_rel", blank=True, null=True)  # za subprocess
    outer_output = models.ForeignKey('Output', related_name="inner_input_rel", blank=True, null=True)  # za subprocess
    PARAMETER_CHOICES = (
        ('text', 'Single line'),
        ('textarea', 'Multi line text'),
        ('select', 'Select box'),
        ('file', 'File field'),
        ('bigfile', 'Big file field'),
        ('checkbox', 'Checkbox'),
    )
    parameter_type = models.CharField(max_length=50, choices=PARAMETER_CHOICES, blank=True, null=True)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ('order','pk')

    def import_from_json(self, json_data, input_conversion, output_conversion):
        self.name = json_data['name']
        self.short_name = json_data['short_name']
        self.description = json_data['description']
        self.variable = json_data['variable']
        self.required = json_data['required']
        self.parameter = json_data['parameter']
        self.multi_id = json_data['multi_id']
        if json_data.get('abstract_input_uid'):
            self.abstract_input = AbstractInput.objects.get(uid=json_data['abstract_input_uid'])
        self.parameter_type = json_data['parameter_type']
        self.order = json_data['order']
        if self.parameter:
            self.value = json_data['value']
        self.save()
        input_conversion[json_data['pk']] = self.pk
        for option in json_data['options']:
            o = Option()
            o.input = self
            o.import_from_json(option, input_conversion, output_conversion)
            o.save()
        if json_data['outer_output']:
            from .output import Output
            self.outer_output = Output.objects.get(pk=output_conversion[json_data['outer_output']])
            self.outer_output.inner_input = self
            self.outer_output.save()
            self.save()

    def export(self):
        d = {}
        d['name'] = self.name
        d['short_name'] = self.short_name
        d['description'] = self.description
        d['variable'] = self.variable
        d['required'] = self.required
        d['parameter'] = self.parameter
        d['value'] = None
        if self.abstract_input:
            d['abstract_input_uid'] = self.abstract_input.uid

        if self.parameter:
            d['value'] = self.value
        d['multi_id'] = self.multi_id
        d['parameter_type'] = self.parameter_type
        d['order'] = self.order
        d['options'] = []
        d['pk'] = self.pk
        for o in self.options.all():
            d['options'].append(o.export())
        try:
            d['inner_output'] = self.inner_output_id
        except:
            d['inner_output'] = None
        try:
            d['outer_output'] = self.outer_output_id
        except:
            d['outer_output'] = None
        return d

    def __unicode__(self):
        return str(self.name)
