from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
import csv
import datetime
from core.models import DatosPersonal, Gerencia, TipoPersonal, Cargo
from django.db import transaction

class Command(BaseCommand):
        def handle(self, *args, **options):
            with transaction.atomic():
                with open('./core/data/data_oriente.csv', 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, delimiter=",")
                    for row in reader:
                        usuario = get_user_model().objects.get_or_create(
                            username =  row["APELLIDOS Y NOMBRES"].split(" ")[2][0].lower() + row["APELLIDOS Y NOMBRES"].split(" ")[0].lower(),
                            defaults={
                                'password': make_password('indesca2025'),
                                'first_name': " ".join(row['APELLIDOS Y NOMBRES'].split(',')[::-1]).upper(),
                            }
                        )[0]
                        gerente = DatosPersonal.objects.get_or_create(
                            ficha = row['FICHA'],
                            user = usuario,
                            cargo = Cargo.objects.get_or_create(
                                nombre = row['CARGO']
                            )[0],
                            supervisor = DatosPersonal.objects.get(
                                ficha = row['SUPERVISOR']
                            ),
                            gerencia = Gerencia.objects.get(
                                nombre=row['GERENCIA'].upper()
                            ),
                            tipo_personal = TipoPersonal.objects.get(pk=2),
                            fecha_ingreso = datetime.datetime.strptime(row['FECHA DE INGRESO'], '%m/%d/%Y').strftime('%Y-%m-%d'),
                        )[0]