from django.core.management.base import BaseCommand
from evaluacion.models import Pregunta, Opciones
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        opciones = [
            (1, '(1 - En Formación)'),
            (2, '(2 - Tiene los conocimientos básicos en su ámbito de trabajo)'),
            (3, '(3 - Tiene y demuestra conocimientos sólidos en su ámbito de trabajo)'),
            (4, '(4 - Tiene y demuestra conocimientos sólidos en su ámbito de trabajo y en otros afines a sus procesos (clientes y proveedores internos)'),
            (5, '(5 - Tiene y demuestra conocimientos sólidos en su ámbito de trabajo, en otros afines a sus procesos y más allá de la organización (clientes y proveedores internos y externos)'),
        ]

        with transaction.atomic():
            for pregunta in Pregunta.objects.filter(seccion__instrumento__pk=4).all():
                pregunta.opciones.add(
                    *[Opciones.objects.get_or_create(opcion=opcion, valor=valor)[0].pk for valor, opcion in opciones]
                )