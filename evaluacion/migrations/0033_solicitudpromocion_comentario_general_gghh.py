# Generated by Django 4.2.17 on 2025-03-17 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluacion', '0032_aspectopromocion_antiguedad'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudpromocion',
            name='comentario_general_gghh',
            field=models.TextField(blank=True, null=True),
        ),
    ]
