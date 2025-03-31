from django.core.management.base import BaseCommand
from core.email import send_mail_async


class Command(BaseCommand):
    help = 'Envia un correo de prueba a dfaria@indesca.com'

    def handle(self, *args, **options):
        send_mail_async(
            'Asunto de prueba',
            'Este es un mensaje de prueba',
            ['dfaria@indesca.com']
        )
