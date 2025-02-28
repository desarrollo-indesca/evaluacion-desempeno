# Generated by Django 4.2.17 on 2025-01-15 09:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('evaluacion', '0004_remove_instrumento_estado'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResultadoInstrumento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resultado_empleado', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('resultado_supervisor', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('resultado_final', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('evaluacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resultados', to='evaluacion.evaluacion')),
                ('instrumento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resultados', to='evaluacion.instrumento')),
            ],
        ),
        migrations.AddField(
            model_name='opciones',
            name='tip',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.CreateModel(
            name='ResultadoSeccion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resultado_empleado', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('resultado_supervisor', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('resultado_final', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('resultado_instrumento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resultados_secciones', to='evaluacion.resultadoinstrumento')),
                ('seccion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resultados', to='evaluacion.seccion')),
            ],
        ),
    ]
