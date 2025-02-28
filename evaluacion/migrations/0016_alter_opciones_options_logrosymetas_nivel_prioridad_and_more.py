# Generated by Django 4.2.17 on 2025-01-23 07:50

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluacion', '0015_alter_opciones_opcion'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='opciones',
            options={'ordering': ['valor']},
        ),
        migrations.AddField(
            model_name='logrosymetas',
            name='nivel_prioridad',
            field=models.CharField(choices=[('P', 'PRIORITARIO'), ('N', 'NO PRIORITARIO')], default=1, max_length=1),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='logrosymetas',
            name='porc_cumplimiento',
            field=models.SmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)]),
        ),
    ]
