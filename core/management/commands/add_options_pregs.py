from django.core.management.base import BaseCommand
from evaluacion.models import Seccion, Opciones, Pregunta, Instrumento
from django.db import transaction

class Command(BaseCommand):
        def handle(self, *args, **options):
            with transaction.atomic():
                instrumento_a_copiar = Instrumento.objects.get(pk=6)
                instrumento = Instrumento.objects.get(pk=9)

                for seccion in instrumento_a_copiar.secciones.all():
                     seccion_copia = Seccion.objects.create(
                          peso = seccion.peso,
                          calculo = seccion.calculo,
                          instrumento = instrumento
                     )

                     for pregunta in seccion.preguntas.all():
                          pregunta_copia = Pregunta.objects.create(
                               pregunta = pregunta.pregunta,
                               tip = pregunta.tip,
                               peso = pregunta.peso,
                               seccion = seccion_copia
                          )

                          pregunta_copia.opciones.set(pregunta.opciones.all())

