# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-17 13:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion

from workflows.helpers import fix_inputs_and_outputs_without_abstract_ids


def remove_old_recommenders(apps, schema_editor):
    Recommender = apps.get_model("workflows", "Recommender")

    Recommender.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0006_widget_save_results'),
    ]

    operations = [
        migrations.RunPython(remove_old_recommenders),
        migrations.RemoveField(
            model_name='recommender',
            name='inp',
        ),
        migrations.RemoveField(
            model_name='recommender',
            name='out',
        ),
        migrations.AddField(
            model_name='input',
            name='abstract_input',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='workflows.AbstractInput'),
        ),
        migrations.AddField(
            model_name='output',
            name='abstract_output',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='workflows.AbstractOutput'),
        ),
        migrations.AddField(
            model_name='recommender',
            name='abstract_input',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommender', to='workflows.AbstractInput'),
        ),
        migrations.AddField(
            model_name='recommender',
            name='abstract_output',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommender', to='workflows.AbstractOutput'),
        ),
        fix_inputs_and_outputs_without_abstract_ids
    ]
