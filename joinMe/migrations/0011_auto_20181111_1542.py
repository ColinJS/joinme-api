# Generated by Django 2.0.7 on 2018-11-11 14:42

import datetime
import django.contrib.gis.db.models.fields
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('joinMe', '0010_auto_20181029_1446'),
    ]

    operations = [
        migrations.AddField(
            model_name='place',
            name='location',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, geography=True, null=True, srid=4326, verbose_name='longitude/lattitude'),
        ),
        migrations.AlterField(
            model_name='event',
            name='ending_time',
            field=models.DateTimeField(default=datetime.datetime(2018, 11, 11, 17, 42, 42, 988507, tzinfo=utc)),
        ),
    ]
