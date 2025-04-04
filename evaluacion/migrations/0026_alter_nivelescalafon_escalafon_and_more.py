# Generated by Django 4.2.17 on 2025-02-07 10:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('evaluacion', '0025_escalafon_activo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nivelescalafon',
            name='escalafon',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='niveles_escalafon', to='evaluacion.escalafon'),
        ),
        migrations.AlterField(
            model_name='resultadoescalafon',
            name='escalafon',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='escalafones', to='evaluacion.nivelescalafon'),
        ),
    ]
