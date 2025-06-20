# Generated by Django 5.2.3 on 2025-06-13 06:21

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CollectorProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('official_address', models.TextField(verbose_name='Office Address')),
                ('collector_id', models.CharField(max_length=20, unique=True, verbose_name='Collector ID')),
                ('tenure_start', models.DateField(verbose_name='Tenure Start Date')),
                ('profile_picture', models.ImageField(blank=True, help_text='Upload a profile image for the collector.', null=True, upload_to='collector_profiles/', verbose_name='Profile Picture')),
            ],
            options={
                'verbose_name': 'Collector Profile',
                'verbose_name_plural': 'Collector Profiles',
            },
        ),
    ]
