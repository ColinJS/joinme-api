# Generated by Django 2.0.7 on 2019-08-21 17:07

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('joinMe', '0016_auto_20190505_1249'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='place',
            name='event',
        ),
        migrations.RemoveField(
            model_name='video',
            name='event',
        ),
        migrations.AddField(
            model_name='event',
            name='place',
            field=models.ManyToManyField(related_name='event', to='joinMe.Place'),
        ),
        migrations.AddField(
            model_name='event',
            name='videos',
            field=models.ManyToManyField(related_name='event', to='joinMe.Video'),
        ),
        migrations.AddField(
            model_name='video',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='my_videos', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='event',
            name='ending_time',
            field=models.DateTimeField(default=datetime.datetime(2019, 8, 21, 20, 7, 56, 123710, tzinfo=utc)),
        ),
    ]
