# Generated by Django 5.1.4 on 2024-12-25 08:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accesskey',
            name='Groups',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='auth.group'),
        ),
    ]
