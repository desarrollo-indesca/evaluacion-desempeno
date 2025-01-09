from django.db import models
from core.models import Periodo, DatosPersonal, TipoPersonal
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.

ESTADOS = (
    ("P", "PENDIENTE"),
    ("E", "EMPEZADA"),
    ("S", "REVISIÓN POR SUPERVISOR"),
    ("G", "ENVIADO A LA GERENCIA"),
    ("H", "ENVIADO A GESTIÓN HUMANA"),
    ("A", "APROBADA"),
)

ROLES = (
    ("E", "EMPLEADO"),
    ("S", "SUPERVISOR"),
    ("G", "GERENTE"),
    ("H", "GESTION HUMANA"),
)

PERIODO_METAS = (
    ("A", "ACTUAL"),
    ("P", "PRÓXIMO"),
)

PRIORIDADES = (
    (1,1),
    (2,2),
    (3,3),
)

class Formulario(models.Model):
    tipo_personal = models.ForeignKey(TipoPersonal, on_delete=models.CASCADE, related_name="formularios")
    activo = models.BooleanField(default=True)

class Instrumento(models.Model):
    nombre = models.CharField(max_length=50)
    peso = models.SmallIntegerField()
    estado = models.CharField(max_length=1, choices=ESTADOS, default="P")
    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE, related_name="instrumentos")

class Seccion(models.Model):
    nombre = models.CharField(max_length=50)
    peso = models.SmallIntegerField()
    instrumento = models.ForeignKey(Instrumento, on_delete=models.CASCADE, related_name="secciones")

class Pregunta(models.Model):
    pregunta = models.CharField(max_length=200)
    peso = models.SmallIntegerField()
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE, related_name="preguntas")

class Respuesta(models.Model):
    comentario_empleado = models.CharField(max_length=200, null=True, blank=True)
    comentario_supervisor = models.CharField(max_length=200, null=True, blank=True)
    comentario_gghh = models.CharField(max_length=200, null=True, blank=True)
    respuesta_empleado = models.SmallIntegerField()
    respuesta_supervisor = models.SmallIntegerField(null=True, blank=True)
    respuesta_definitiva = models.SmallIntegerField(null=True, blank=True)
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name="respuestas")
    evaluacion = models.ForeignKey("Evaluacion", on_delete=models.CASCADE, related_name="respuestas")

class Opciones(models.Model):
    opcion = models.CharField(max_length=200)
    valor = models.SmallIntegerField()
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name="opciones")

class Evaluacion(models.Model):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name="evaluaciones")
    evaluado = models.ForeignKey(DatosPersonal, on_delete=models.CASCADE, related_name="evaluaciones")
    fecha_inicio = models.DateField(auto_now_add=True)
    fecha_fin = models.DateField(null=True, blank=True)
    fecha_revision = models.DateField(null=True, blank=True)
    fecha_envio = models.DateField(null=True, blank=True)
    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE, related_name="evaluaciones")
    estado = models.CharField(max_length=1, choices=ESTADOS, default="P")

class LogrosYMetas(models.Model):
    descripcion = models.CharField(max_length=200)
    porc_cumplimiento = models.SmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    anadido_por = models.CharField(max_length=1, choices=ROLES)
    activo = models.BooleanField(default=True)
    periodo = models.CharField(max_length=1, choices=PERIODO_METAS)
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="logros_y_metas")

class ClasificacionFormacion(models.Model):
    clasificacion = models.CharField(max_length=200)

class Competencias(models.Model):
    nombre = models.CharField(max_length=45)
    tipo_personal = models.ForeignKey(TipoPersonal, on_delete=models.CASCADE, related_name="competencias")
    tipo = models.CharField(max_length=1, choices=ROLES)

class Formacion(models.Model):
    necesidad_formacion = models.CharField(max_length=200)
    prioridad = models.CharField(max_length=1, choices=PRIORIDADES)
    clasificacion = models.ForeignKey(ClasificacionFormacion, on_delete=models.CASCADE, related_name="formaciones")
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="formaciones")
    anadido_por = models.CharField(max_length=1, choices=ROLES)
    activo = models.BooleanField(default=True)
    competencias = models.ManyToManyField(Competencias, related_name="formaciones")