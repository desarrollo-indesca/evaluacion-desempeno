from django.core.management.base import BaseCommand
from evaluacion.models import Seccion, Opciones, Pregunta
from django.db import transaction

class Command(BaseCommand):
        def handle(self, *args, **options):
            preguntas = [
                {
                    'pregunta': 'Nivel de Educación',
                    'opciones': [
                        (1, '(1 - Nivel de formacion menor al punto 3)'),
                        (3, '(3 - Universitario)'), 
                        (4, '(4 - Especialización)'), 
                        (5, '(5 - Maestría)'), 
                        (7, '(7 -Doctorado (deseable))'),
                        (10, '(10 -Doctorado)')
                    ]
                },
                {
                    'pregunta': 'Idioma Inglés',
                    'opciones': [
                        (1, '(1 - Lectura)'),
                        (2, '(2 - Lectura, escritura, y conversación básica)'), 
                        (3, '(3 - Muy buena lectura y escritura, conversación básica. Más alla de la literatura técnica)'), 
                        (10, '(10 -Buen nivel completo)'),
                    ]
                },
                {
                    'pregunta': 'Amplitud de Conocimientos',
                    'opciones': [
                        (5, '(5 - Limitada a 1 área específica)'),
                        (6, '(6 - Conjuga más de 1 área integra, sintetiza)'), 
                        (10, '(10 - Conjuga mas de 2 áreas, integra, sintetiza. Considera competentemente el impacto org. y económico de sus propuestas y resultados)'),
                    ]
                },
                {
                    'pregunta': 'Línea de Investigación Propia',
                    'opciones': [
                        (1, '(2 -No tiene)'),
                        (3, '(3 - Esbozada, ya muestra una clara inclinación e intéres)'), 
                        (4, '(4 - Especialización)'), 
                        (5, '(5 - Claramente definida, explícita y declarada oficialmente)'), 
                        (6, '(6 -Al menos 2 líneas de investigación)'),
                        (10, '(10 -Al menos 2 líneas de investigación. Posee equipo de trabajo)')
                    ]
                },
            ]

            with transaction.atomic():
                seccion = Seccion.objects.get(pk=35)
                for pregunta in preguntas:
                    opciones = pregunta['opciones']
                    pregunta = Pregunta.objects.create(
                         pregunta = pregunta['pregunta'],
                         peso = 1,
                         seccion = seccion
                    )
                    pregunta.opciones.add(
                        *[Opciones.objects.get_or_create(opcion=opcion[1], valor=opcion[0])[0].pk for opcion in opciones]
                    )