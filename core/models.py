from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.

class Periodo(models.Model):
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"PERIODO {self.fecha_inicio} - {self.fecha_fin}"

class TipoPersonal(models.Model):
    nombre = models.CharField(max_length=50)

class Cargo(models.Model):
    nombre = models.CharField(max_length=50)
    nivel = models.SmallIntegerField()

class Gerencia(models.Model):
    nombre = models.CharField(max_length=50)
    
class DatosPersonal(models.Model):
    ficha = models.CharField(max_length=5)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="datos_personal")
    tipo_personal = models.ForeignKey("TipoPersonal", on_delete=models.CASCADE, related_name="personal")
    cargo = models.ForeignKey("Cargo", on_delete=models.CASCADE, related_name="personal")
    activo = models.BooleanField(default=True)
    supervisor = models.ForeignKey("self", on_delete=models.CASCADE, related_name="supervisados")
    gerencia = models.ForeignKey("Gerencia", on_delete=models.CASCADE, related_name="personal_gerencia")

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
class PeriodoGerencial(models.Model):
    gerente = models.ForeignKey(DatosPersonal, on_delete=models.CASCADE, related_name="personal_gerente")
    activo = models.BooleanField(default=True)
    gerencia = models.ForeignKey(Gerencia, on_delete=models.CASCADE, related_name="gerencias")