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

NIVELES_PRIORIDAD = (
    ("P", "PRIORITARIO"),
    ("N", "NO PRIORITARIO")
)

CALCULOS = (
    ("S", "SUMA"),
    ("P", "PROMEDIO"),
    ("M", "MÍNIMO")
)

class Formulario(models.Model):
    tipo_personal = models.ForeignKey(TipoPersonal, on_delete=models.CASCADE, related_name="formularios")
    activo = models.BooleanField(default=True)

class Instrumento(models.Model):
    nombre = models.CharField(max_length=50)
    peso = models.SmallIntegerField()
    calculo = models.CharField(max_length=1, choices=ROLES, default="S")
    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE, related_name="instrumentos")

    def __str__(self):
        return self.nombre

class Seccion(models.Model):
    nombre = models.CharField(max_length=300)
    peso = models.SmallIntegerField()
    calculo = models.CharField(max_length=1, choices=ROLES, default="S")
    instrumento = models.ForeignKey(Instrumento, on_delete=models.CASCADE, related_name="secciones")

    def titulo(self):
        return self.nombre.split(":")[0]

    def descripcion(self):
        return self.nombre.split(":")[1] if self.nombre.find(":") != -1 else ""

class Pregunta(models.Model):
    pregunta = models.CharField(max_length=400)
    peso = models.SmallIntegerField()
    tip = models.CharField(max_length=400, null=True, blank=True)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE, related_name="preguntas")

class Opciones(models.Model):
    opcion = models.CharField(max_length=300)
    valor = models.SmallIntegerField()
    pregunta = models.ManyToManyField(Pregunta, related_name="opciones")

    class Meta:
        ordering = ["valor"]

class Evaluacion(models.Model):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name="evaluaciones")
    evaluado = models.ForeignKey(DatosPersonal, on_delete=models.CASCADE, related_name="evaluaciones")
    fecha_inicio = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE, related_name="evaluaciones")
    estado = models.CharField(max_length=1, choices=ESTADOS, default="P")

class ResultadoInstrumento(models.Model):
    resultado_empleado = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    resultado_supervisor = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    resultado_final = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="resultados")
    instrumento = models.ForeignKey(Instrumento, on_delete=models.CASCADE, related_name="resultados")

class ResultadoSeccion(models.Model):
    resultado_empleado = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    resultado_supervisor = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    resultado_final = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE, related_name="resultados")
    resultado_instrumento = models.ForeignKey(ResultadoInstrumento, on_delete=models.CASCADE, related_name="resultados_secciones")

class Respuesta(models.Model):
    comentario_empleado = models.CharField(max_length=200, null=True, blank=True)
    comentario_supervisor = models.CharField(max_length=200, null=True, blank=True)
    comentario_gghh = models.CharField(max_length=200, null=True, blank=True)
    respuesta_empleado = models.SmallIntegerField()
    respuesta_supervisor = models.SmallIntegerField(null=True, blank=True)
    respuesta_definitiva = models.SmallIntegerField(null=True, blank=True)
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name="respuestas")
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="respuestas")

class LogrosYMetas(models.Model):
    descripcion = models.CharField(max_length=200)
    porc_cumplimiento = models.SmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], null=True, blank=True)
    nivel_prioridad = models.CharField(max_length=1, choices=NIVELES_PRIORIDAD)
    anadido_por = models.CharField(max_length=1, choices=ROLES)
    activo = models.BooleanField(default=True)
    periodo = models.CharField(max_length=1, choices=PERIODO_METAS)
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="logros_y_metas")

class ClasificacionFormacion(models.Model):
    clasificacion = models.CharField(max_length=200)

    def __str__(self):
        return self.clasificacion.upper()

class Competencias(models.Model):
    nombre = models.CharField(max_length=45)
    tipo_personal = models.ForeignKey(TipoPersonal, on_delete=models.CASCADE, related_name="competencias")
    tipo = models.CharField(max_length=1, choices=ROLES)

    def __str__(self):
        return self.nombre.upper()

class Formacion(models.Model):
    necesidad_formacion = models.CharField(max_length=200)
    prioridad = models.CharField(max_length=1, choices=PRIORIDADES)
    clasificacion = models.ForeignKey(ClasificacionFormacion, on_delete=models.CASCADE, related_name="formaciones")
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="formaciones")
    anadido_por = models.CharField(max_length=1, choices=ROLES)
    activo = models.BooleanField(default=True)
    competencias = models.ManyToManyField(Competencias, related_name="formaciones")