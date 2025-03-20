import datetime
from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.
class NombreMixin():
    def __str__(self):
        return self.nombre

class Periodo(models.Model):
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.fecha_inicio} - {self.fecha_fin}"
    
    def todas_evaluaciones_terminadas(self):
        return self.evaluaciones.filter(estado__in=("A", "R")).count() == self.evaluaciones.count()
    
    class Meta:
        ordering = ("-activo", "-fecha_inicio",)

class TipoPersonal(NombreMixin, models.Model):
    nombre = models.CharField(max_length=50)

class Cargo(NombreMixin, models.Model):
    nombre = models.CharField(max_length=50)

class Gerencia(NombreMixin, models.Model):
    nombre = models.CharField(max_length=50)
    
class DatosPersonal(models.Model):
    ficha = models.CharField(max_length=5)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="datos_personal")
    tipo_personal = models.ForeignKey("TipoPersonal", on_delete=models.CASCADE, related_name="personal")
    cargo = models.ForeignKey("Cargo", on_delete=models.CASCADE, related_name="personal")
    activo = models.BooleanField(default=True)
    supervisor = models.ForeignKey("self", on_delete=models.CASCADE, related_name="supervisados", null=True, blank=True)
    gerencia = models.ForeignKey("Gerencia", on_delete=models.CASCADE, related_name="personal_gerencia")
    fecha_ingreso = models.DateField()
    escalafon = models.ForeignKey("evaluacion.NivelEscalafon", on_delete=models.CASCADE, default=1)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    def evaluacion_actual(self):
        return self.evaluaciones.filter(periodo__activo=True).first()
    
    def antiguedad(self):
        today = datetime.date.today()
        time_in_charge_months = (today.year - self.fecha_ingreso.year) * 12 + today.month - self.fecha_ingreso.month - ((today.month, today.day) < (self.fecha_ingreso.month, self.fecha_ingreso.day))
        return time_in_charge_months
    
    class Meta:
        ordering = (
            'ficha',
        )
    
class PeriodoGerencial(models.Model):
    gerente = models.ForeignKey(DatosPersonal, on_delete=models.CASCADE, related_name="personal_gerente")
    activo = models.BooleanField(default=True)
    gerencia = models.ForeignKey(Gerencia, on_delete=models.CASCADE, related_name="gerencias")
