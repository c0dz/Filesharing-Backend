# Generated by Django 5.0.6 on 2024-06-16 00:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filesharing', '0003_alter_filepermissionmodel_file'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='filemodel',
            name='file',
        ),
    ]
