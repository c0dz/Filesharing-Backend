# Generated by Django 5.0.6 on 2024-06-16 12:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filesharing', '0005_rename_cloud_name_filemodel_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filepermissionmodel',
            name='permission',
            field=models.CharField(choices=[('R', 'Read Permission'), ('F', 'Full Permission')], max_length=10),
        ),
    ]
