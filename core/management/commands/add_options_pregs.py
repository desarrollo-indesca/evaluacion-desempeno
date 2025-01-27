from django.core.management.base import BaseCommand
from evaluacion.models import Seccion, Opciones, Pregunta, Instrumento
from django.db import transaction

class Command(BaseCommand):
        def handle(self, *args, **options):
            with transaction.atomic():
                instrumento_a_copiar = Instrumento.objects.get(pk=6)
                instrumento = Instrumento.objects.get(pk=9)

                for seccion in instrumento_a_copiar.secciones.all():
                     seccion_copia = seccion
                     seccion_copia.pk = None
                     seccion_copia.instrumento = instrumento
                     seccion_copia.save()

                     for pregunta in seccion.preguntas.all():
                          pregunta_copia = Pregunta.objects.create(
                               pregunta = pregunta.pregunta,
                               tip = pregunta.tip,
                               peso = pregunta.peso
                          )

                          pregunta_copia.opciones.add(pregunta.opciones.all().values_list())  

