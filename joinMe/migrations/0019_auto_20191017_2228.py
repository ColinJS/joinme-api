# Generated by Django 2.0.7 on 2019-10-17 20:28

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('joinMe', '0018_auto_20190923_1741'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='ending_time',
            field=models.DateTimeField(default=datetime.datetime(2019, 10, 17, 23, 28, 2, 544343, tzinfo=utc)),
        ),
    ]