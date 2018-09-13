# Generated by Django 2.0.7 on 2018-08-29 16:38

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('joinMe', '0014_auto_20180818_1440'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_of_notification', models.SmallIntegerField(choices=[(0, 'NEW_INVITATION'), (1, 'SOMEONE_COMING')], default='NEW_INVITATION')),
                ('state', models.SmallIntegerField(choices=[(0, 'UNSEEN'), (1, 'SEEN')], default='UNSEEN')),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AlterField(
            model_name='event',
            name='ending_time',
            field=models.DateTimeField(default=datetime.datetime(2018, 8, 29, 19, 38, 51, 344691, tzinfo=utc)),
        ),
        migrations.AddField(
            model_name='notification',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='joinMe.Event'),
        ),
        migrations.AddField(
            model_name='notification',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL),
        ),
    ]