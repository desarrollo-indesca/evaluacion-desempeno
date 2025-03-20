from django.contrib import admin

# Register your models here.

from .models import (Evaluacion, Formulario, Instrumento, Pregunta, Opciones, Respuesta, ResultadoInstrumento, ResultadoEscalafon, SolicitudPromocion, RespuestaSolicitudPromocion, AspectoPromocion, DetalleAspectoPromocion, NivelEscalafon, FormularioPromocion, Escalafon)

for model in [Evaluacion, Formulario, Instrumento, Pregunta, Opciones, Respuesta, ResultadoInstrumento, ResultadoEscalafon, SolicitudPromocion, RespuestaSolicitudPromocion, AspectoPromocion, DetalleAspectoPromocion, NivelEscalafon, Escalafon, FormularioPromocion]:
    admin.site.register(model)
