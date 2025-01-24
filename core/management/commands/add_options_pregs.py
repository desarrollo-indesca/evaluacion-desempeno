from django.core.management.base import BaseCommand
from evaluacion.models import Pregunta, Opciones, Instrumento
from django.db import transaction

class Command(BaseCommand):
        def handle(self, *args, **options):
            opciones = [
                (0, 'Nunca demuestra esta habilidad'),
                (1, 'Rara vez demuestra esta habilidad'),
                (2, 'A veces demuestra esta habilidad'),
                (3, 'Normalmente demuestra esta habilidad'),
                (4, 'Siempre demuestra esta habilidad'),
            ]

            with transaction.atomic():
                for seccion in Instrumento.objects.get(pk=6).secciones.all():
                    for pregunta in seccion.preguntas.all():
                        pregunta.opciones.add(
                            *[Opciones.objects.get_or_create(opcion=opcion, valor=valor)[0].pk for valor, opcion in opciones]
                        )