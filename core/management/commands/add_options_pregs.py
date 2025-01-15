from django.core.management.base import BaseCommand
from evaluacion.models import Pregunta, Opciones
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        opciones = [
            (0, 'N/A'),
            (1, 'Por Debajo'),
            (2, 'Promedio'),
            (3, 'Por Encima'),
        ]

        with transaction.atomic():
            for pregunta in Pregunta.objects.filter(seccion__instrumento__pk=4).all():
                pregunta.opciones.add(
                    *[Opciones.objects.get_or_create(opcion=opcion, valor=valor)[0].pk for valor, opcion in opciones]
                )