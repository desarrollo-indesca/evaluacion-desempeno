# Generated by Django 4.2.17 on 2025-03-11 08:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('evaluacion', '0027_alter_formacion_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='AspectoPromocion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120, verbose_name='Nombre del Aspecto a Considerar')),
            ],
        ),
        migrations.CreateModel(
            name='DetalleAspectoPromocion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor_asociado', models.SmallIntegerField()),
                ('descripcion', models.CharField(blank=True, max_length=200, null=True)),
                ('aspecto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalle_aspectos', to='evaluacion.aspectopromocion')),
            ],
        ),
        migrations.AlterModelOptions(
            name='evaluacion',
            options={'ordering': ('periodo', '-id')},
        ),
        migrations.AlterField(
            model_name='evaluacion',
            name='estado',
            field=models.CharField(choices=[('P', 'PENDIENTE POR EMPEZAR'), ('E', 'EMPEZADA'), ('S', 'REVISIÓN POR SUPERVISOR'), ('G', 'ENVIADO A LA GERENCIA'), ('H', 'ENVIADO A GESTIÓN HUMANA'), ('A', 'APROBADA'), ('R', 'RECHAZADA')], default='P', max_length=1),
        ),
        migrations.CreateModel(
            name='SolicitudPromocion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aprobado', models.BooleanField(blank=True, null=True)),
                ('fecha_envio', models.DateTimeField(auto_now_add=True, null=True)),
                ('fecha_aprobacion', models.DateTimeField(blank=True, null=True)),
                ('evaluacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='solicitudes_promocion', to='evaluacion.evaluacion')),
            ],
        ),
        migrations.CreateModel(
            name='RespuestaSolicitudPromocion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cumple', models.BooleanField(blank=True, null=True)),
                ('justificacion', models.TextField(blank=True, null=True)),
                ('detalle_aspecto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='respuestas_solicitud_promocion', to='evaluacion.detalleaspectopromocion')),
                ('respuesta_asociada', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='respuestas_solicitud_promocion', to='evaluacion.respuesta')),
                ('solicitud_promocion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='respuestas_solicitud_promocion', to='evaluacion.solicitudpromocion')),
            ],
        ),
        migrations.CreateModel(
            name='FormularioPromocion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activo', models.BooleanField(default=True)),
                ('nivel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='formularios_promocion', to='evaluacion.nivelescalafon')),
            ],
        ),
        migrations.AddField(
            model_name='detalleaspectopromocion',
            name='formulario_promocion',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalle_aspectos', to='evaluacion.formulariopromocion'),
        ),
        migrations.AddField(
            model_name='detalleaspectopromocion',
            name='opcion_asociada',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='detalle_aspectos', to='evaluacion.opciones'),
        ),
        migrations.AddField(
            model_name='detalleaspectopromocion',
            name='pregunta_asociada',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalle_aspectos', to='evaluacion.pregunta'),
        ),
    ]
