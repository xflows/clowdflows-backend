from django.db import models


class Connection(models.Model):
    output = models.ForeignKey("Output", related_name="connections")
    input = models.ForeignKey("Input", related_name="connections")
    workflow = models.ForeignKey("Workflow", related_name="connections")

    def export(self):
        d = {}
        d['output_id'] = self.output_id
        d['input_id'] = self.input_id
        return d

    def import_from_json(self, json_data, input_conversion, output_conversion):
        self.output_id = output_conversion[json_data['output_id']]
        self.input_id = input_conversion[json_data['input_id']]
        self.save()

