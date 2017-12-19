# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-19 10:32
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import workflows.thumbs


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0008_auto_20171009_1053'),
    ]

    operations = [
        migrations.AddField(
            model_name='abstractwidget',
            name='always_save_results',
            field=models.BooleanField(default=False, help_text='Require that the results are always stored in the DB.'),
        ),
    ]
