# Generated by Django 2.1 on 2018-08-28 01:17

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ha_integration', '0002_auto_20180827_2328'),
    ]

    operations = [
        migrations.AddField(
            model_name='statechange',
            name='attributes_json',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
    ]