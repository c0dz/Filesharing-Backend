# Generated by Django 5.0.6 on 2024-06-16 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filesharing', '0007_alter_filepermissionmodel_permission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='filepermissionmodel',
            name='permission',
            field=models.CharField(choices=[('R', 'Read Permission'), ('F', 'Full Permission')], max_length=10),
        ),
    ]
