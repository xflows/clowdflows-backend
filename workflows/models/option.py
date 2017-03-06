from django.db import models


class Option(models.Model):
    input = models.ForeignKey('Input', related_name="options")
    name = models.CharField(max_length=200)
    value = models.TextField(blank=True, null=True)

    def import_from_json(self, json_data, input_conversion, output_conversion):
        self.name = json_data['name']
        self.value = json_data['value']
        self.save()

    def export(self):
        d = {}
        d['name'] = self.name
        d['value'] = self.value
        return d

    class Meta:
        ordering = ['name']