# Generated by Django 2.0.7 on 2018-07-28 14:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('joinMe', '0009_auto_20180724_0049'),
    ]

    operations = [
        migrations.CreateModel(
            name='GuestToEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('state', models.SmallIntegerField(choices=[(0, 'PENDING'), (1, 'ACCEPTED'), (2, 'REFUSED')], default='PENDING')),
            ],
        ),
        migrations.RemoveField(
            model_name='event',
            name='guests',
        ),
        migrations.AddField(
            model_name='guesttoevent',
            name='event',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='guests', to='joinMe.Event'),
        ),
        migrations.AddField(
            model_name='guesttoevent',
            name='guest',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='events', to=settings.AUTH_USER_MODEL),
        ),
    ]