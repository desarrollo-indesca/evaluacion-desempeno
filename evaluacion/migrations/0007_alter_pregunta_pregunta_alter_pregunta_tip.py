# Generated by Django 4.2.17 on 2025-01-15 09:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluacion', '0006_remove_opciones_tip_pregunta_tip'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pregunta',
            name='pregunta',
            field=models.CharField(max_length=400),
        ),
        migrations.AlterField(
            model_name='pregunta',
            name='tip',
            field=models.CharField(blank=True, max_length=400, null=True),
        ),
    ]
