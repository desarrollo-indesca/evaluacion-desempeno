from django.db import models
from core.models import Periodo, DatosPersonal, TipoPersonal

# Create your models here.

class Formulario(models.Model):
    tipo_personal = models.ForeignKey(TipoPersonal, on_delete=models.CASCADE, related_name="formularios")
    activo = models.BooleanField(default=True)

class Evaluacion(models.Model):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name="evaluaciones")
    evaluado = models.ForeignKey(DatosPersonal, on_delete=models.CASCADE, related_name="evaluaciones")
    fecha_inicio = models.DateField(auto_now_add=True)
    fecha_fin = models.DateField(null=True, blank=True)
    fecha_revision = models.DateField(null=True, blank=True)
    fecha_envio = models.DateField(null=True, blank=True)
    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE, related_name="evaluaciones")