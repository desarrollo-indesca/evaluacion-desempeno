from django.db import models
from core.models import Periodo, DatosPersonal, TipoPersonal
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.

ESTADOS = (
    ("P", "PENDIENTE POR EMPEZAR"),
    ("E", "EMPEZADA"),
    ("S", "REVISIÓN POR SUPERVISOR"),
    ("G", "ENVIADO A LA GERENCIA"),
    ("H", "ENVIADO A GESTIÓN HUMANA"),
    ("A", "APROBADA"),
    ("R", "RECHAZADA")
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
    (1, "1 - Asociado a Competencias Técnicas"),
    (2, "2 - Asociado a Competencias Genéricas"),
    (3, "3 - Otras"),
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
    escalafon = models.ForeignKey("evaluacion.Escalafon", on_delete=models.SET_NULL, null=True, blank=True)
    calculo_escalafon = models.CharField(max_length=1, choices=CALCULOS, null=True, blank=True)
    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE, related_name="instrumentos")

    def __str__(self):
        return self.nombre

class Seccion(models.Model):
    nombre = models.CharField(max_length=300)
    peso = models.SmallIntegerField()
    calculo = models.CharField(max_length=1, choices=ROLES, default="S")
    instrumento = models.ForeignKey(Instrumento, on_delete=models.CASCADE, related_name="secciones")

    def __str__(self):
        return self.titulo().upper()

    def titulo(self):
        return self.nombre.split(":")[0]

    def descripcion(self):
        return self.nombre.split(":")[1] if self.nombre.find(":") != -1 else ""

class Pregunta(models.Model):
    pregunta = models.CharField(max_length=400)
    peso = models.DecimalField(max_digits=5, decimal_places=2)
    tip = models.CharField(max_length=400, null=True, blank=True)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE, related_name="preguntas")

class Opciones(models.Model):
    opcion = models.CharField(max_length=300)
    valor = models.SmallIntegerField()
    pregunta = models.ManyToManyField(Pregunta, related_name="opciones")

    def __str__(self):
        return self.opcion.upper()

    class Meta:
        ordering = ["valor"]

class Evaluacion(models.Model):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name="evaluaciones")
    evaluado = models.ForeignKey(DatosPersonal, on_delete=models.CASCADE, related_name="evaluaciones")
    fecha_inicio = models.DateTimeField(auto_now_add=True, null=True, blank=True) # Inicio de la Evaluación
    fecha_envio = models.DateTimeField(null=True, blank=True) # Envio al Supervisor
    fecha_revision = models.DateTimeField(null=True, blank=True) # Revisión
    fecha_entrega = models.DateTimeField(null=True, blank=True) # Entrega GH
    fecha_fin = models.DateTimeField(null=True, blank=True) # Fecha al aprobar/rechazar
    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE, related_name="evaluaciones")
    estado = models.CharField(max_length=1, choices=ESTADOS, default="P")
    comentario_evaluado = models.TextField(null=True, blank=True) 
    comentario_supervisor = models.TextField(null=True, blank=True) 
    comentario_gghh = models.TextField(null=True, blank=True) 

    def estado_largo(self):
        return list(filter(lambda x: x[0] == self.estado, ESTADOS))[0][1]
    
    def total_definitivo(self):
        return self.resultados.aggregate(models.Sum('resultado_final')).get('resultado_final__sum')
    
    def total_supervisor(self):
        return self.resultados.aggregate(models.Sum('resultado_supervisor')).get('resultado_supervisor__sum')

    def total(self):
        return self.resultados.aggregate(models.Sum('resultado_empleado')).get('resultado_empleado__sum')
    
    def peso(self):
        return self.formulario.instrumentos.aggregate(models.Sum('peso')).get('peso__sum')
    
    class Meta:
        ordering = ("periodo","-id",)

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
    nivel_prioridad = models.CharField(max_length=1, choices=NIVELES_PRIORIDAD, null=True, blank=True)
    anadido_por = models.CharField(max_length=1, choices=ROLES)
    activo = models.BooleanField(default=True)
    periodo = models.CharField(max_length=1, choices=PERIODO_METAS)
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="logros_y_metas")

    def prioridad_larga(self):
        return [p[1] for p in NIVELES_PRIORIDAD if self.nivel_prioridad == p[0]][0] if self.nivel_prioridad else "N/A"

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

    class Meta:
        ordering = ["prioridad"]

class Escalafon(models.Model):
    tipo_personal = models.ForeignKey(TipoPersonal, on_delete=models.CASCADE, related_name="escalafones")
    activo = models.BooleanField(default=True)

class NivelEscalafon(models.Model):
    nivel = models.CharField(max_length=80)
    valor_requerido = models.IntegerField()
    escalafon = models.ForeignKey("evaluacion.Escalafon", on_delete=models.CASCADE, null=True, blank=True, related_name="niveles_escalafon")

    def __str__(self):
        return self.nivel
    
class ResultadoEscalafon(models.Model):
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="escalafones")
    escalafon = models.ForeignKey(NivelEscalafon, on_delete=models.CASCADE, related_name="escalafones")
    asignado_por = models.CharField(max_length=1, choices=ROLES)

    def __str__(self):
        return self.escalafon.nivel
    
# Promocion del Personal
class AspectoPromocion(models.Model):
    nombre = models.CharField("Nombre del Aspecto a Considerar", max_length=120)

class FormularioPromocion(models.Model):
    nivel = models.ForeignKey(NivelEscalafon, on_delete=models.CASCADE, related_name="formularios_promocion")
    activo = models.BooleanField(default=True)

class DetalleAspectoPromocion(models.Model):
    aspecto = models.ForeignKey(AspectoPromocion, on_delete=models.CASCADE, related_name="detalle_aspectos")
    formulario_promocion = models.ForeignKey(FormularioPromocion, on_delete=models.CASCADE, null=True, blank=True, related_name="detalle_aspectos")
    pregunta_asociada = models.ForeignKey(Pregunta, on_delete=models.CASCADE, null=True, blank=True, related_name="detalle_aspectos")
    valor_asociado = models.SmallIntegerField()
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    opcion_asociada = models.ForeignKey(Opciones, on_delete=models.CASCADE, related_name="detalle_aspectos", null=True, blank=True)

class SolicitudPromocion(models.Model):
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.CASCADE, related_name="solicitudes_promocion")
    aprobado = models.BooleanField(null=True, blank=True)
    fecha_envio = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

class RespuestaSolicitudPromocion(models.Model):
    solicitud_promocion = models.ForeignKey(SolicitudPromocion, on_delete=models.CASCADE, related_name="respuestas_solicitud_promocion")
    respuesta_asociada = models.ForeignKey(Respuesta, on_delete=models.CASCADE, related_name="respuestas_solicitud_promocion")
    cumple = models.BooleanField(null=True, blank=True)
    justificacion = models.TextField(null=True, blank=True)
    detalle_aspecto = models.ForeignKey(DetalleAspectoPromocion, on_delete=models.CASCADE, related_name="respuestas_solicitud_promocion")
    comentario_gghh = models.TextField(null=True, blank=True)