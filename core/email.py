import threading
from django.core.mail import send_mail
from django.conf import settings

DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL

class EmailThread(threading.Thread):
    def __init__(self, subject, content, recipient_list, sender):
        self.subject = subject
        self.recipient_list = list(filter(None, (r.strip() for r in recipient_list if r)))
        self.content = content
        self.sender = sender
        threading.Thread.__init__(self)

    def run (self):
        send_mail(self.subject, '', self.sender, self.recipient_list, html_message=self.content)

def send_mail_async(subject, content, recipient_list, sender=DEFAULT_FROM_EMAIL):
    EmailThread(subject, content, recipient_list, sender).start()