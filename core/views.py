from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.contrib import messages
from django.views import View
from django.shortcuts import render, redirect
from core.models import *

# Create your views here.

class PeriodoContextMixin():
    def get_context_data(self, **kwargs):
        context = {}
        if hasattr(super(), 'get_context_data'):
            context = super().get_context_data(**kwargs)

        context['periodo'] = Periodo.objects.get(activo=True)
        return context

class Login(PeriodoContextMixin, View):
    template_name = 'core/login.html'
    redirect_authenticated_user = True
    success_url = '/'

    def post(self, request, *args, **kwargs):
        username_or_ficha = request.POST.get('username').strip().lower()
        password = request.POST.get('password').strip()
            
        with transaction.atomic():
            user = authenticate(request, username=username_or_ficha, password=password)

            if not user:
                try:
                    datos_personal = DatosPersonal.objects.get(ficha=username_or_ficha)
                    print(f"FICHA: {username_or_ficha} - {datos_personal.user.username}")
                    user = authenticate(request, username=datos_personal.user.username, password=password)
                    print(user)
                except DatosPersonal.DoesNotExist:
                    user = None

            if user is not None:
                login(request, user)
            else:
                messages.error(request, 'Credenciales incorrectas.')
            
            return redirect(self.success_url)
    
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, context=self.get_context_data())

class Dashboard(LoginRequiredMixin, View, PeriodoContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['datos_personal'] = DatosPersonal.objects.get(activo = True)
        from datetime import date

        datos_personal = context['datos_personal']
        today = date.today()
        time_in_charge = today.year - datos_personal.fecha_ingreso.year - (
            (today.month, today.day) < (datos_personal.fecha_ingreso.month, datos_personal.fecha_ingreso.day)
        )
        time_in_charge_months = (today.year - datos_personal.fecha_ingreso.year) * 12 + today.month - datos_personal.fecha_ingreso.month - ((today.month, today.day) < (datos_personal.fecha_ingreso.month, datos_personal.fecha_ingreso.day))
        context['antiguedad'] = time_in_charge_months

        return context

    def get(self, request):
        return render(request, 'core/dashboard.html', context=self.get_context_data())