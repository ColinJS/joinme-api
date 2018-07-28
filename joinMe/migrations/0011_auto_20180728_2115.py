# Generated by Django 2.0.7 on 2018-07-28 19:15

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('joinMe', '0010_auto_20180728_1645'),
    ]

    operations = [
        migrations.CreateModel(
            name='Place',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('formatted_address', models.CharField(max_length=200)),
                ('place_id', models.CharField(max_length=200)),
            ],
        ),
        migrations.AddField(
            model_name='event',
            name='duration',
            field=models.DurationField(blank=True, default=datetime.timedelta(0, 10800)),
        ),
        migrations.AddField(
            model_name='event',
            name='ending_time',
            field=models.DateTimeField(default=datetime.datetime(2018, 7, 29, 0, 15, 54, 66804)),
        ),
        migrations.AddField(
            model_name='place',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='place', to='joinMe.Event'),
        ),
    ]