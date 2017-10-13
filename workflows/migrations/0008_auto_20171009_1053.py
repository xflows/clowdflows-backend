# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-10-09 10:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0007_auto_20170317_1325'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='input',
            options={'ordering': ('order', 'pk')},
        ),
        migrations.AlterModelOptions(
            name='output',
            options={'ordering': ('order', 'pk')},
        ),
        migrations.AddField(
            model_name='workflow',
            name='staff_pick',
            field=models.BooleanField(default=False),
        ),
    ]