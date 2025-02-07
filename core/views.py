from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.contrib import messages
from django.views import View
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from datetime import date
from core.models import *
from evaluacion.models import Evaluacion

# Create your views here.

class PeriodoContextMixin():
    def get_periodo(self):
        return Periodo.objects.get(activo=True)

    def get_context_data(self, **kwargs):
        context = {}
        if hasattr(super(), 'get_context_data'):
            context = super().get_context_data(**kwargs)

        context['periodo'] = self.get_periodo()
        return context
    
class EvaluacionEstadoMixin():
    estado = ""

    def get(self, request, **kwargs):
        print(kwargs)
        if kwargs.get('evaluacion'):
            evaluacion = Evaluacion.objects.get(pk=kwargs.get('evaluacion'))
        elif kwargs.get('pk'):
            evaluacion = Evaluacion.objects.filter(pk=kwargs.get('pk')) 
            if(evaluacion.exists()):
                evaluacion = evaluacion.first()
            else:
                evaluacion = None
        
        if(not evaluacion):
            evaluacion = Evaluacion.objects.get(evaluado=self.request.user.datos_personal.get(activo=True), periodo=self.get_periodo())

        if(evaluacion.estado == self.estado):
            return render(request, self.template_name, context=self.get_context_data())
        else:
            return HttpResponseForbidden()

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
        context['datos_personal'] = DatosPersonal.objects.get(activo = True, user = self.request.user)

        datos_personal = context['datos_personal']
        evaluacion = Evaluacion.objects.filter(evaluado=datos_personal, periodo = context['periodo']).first()
        today = date.today()
        time_in_charge_months = (today.year - datos_personal.fecha_ingreso.year) * 12 + today.month - datos_personal.fecha_ingreso.month - ((today.month, today.day) < (datos_personal.fecha_ingreso.month, datos_personal.fecha_ingreso.day))
        context['antiguedad'] = time_in_charge_months
        context['evaluacion'] = evaluacion
        context['puede_finalizar'] = evaluacion.resultados.count() == evaluacion.formulario.instrumentos.count() and (
            evaluacion.formaciones.exists() and evaluacion.logros_y_metas.exists()
        ) if evaluacion else False
        context['instrumentos'] = [
            {
                'nombre': instrumento.nombre,
                'completado': instrumento.resultados.filter(evaluacion = evaluacion).exists(),
                'resultado': instrumento.resultados.filter(evaluacion = evaluacion).first().resultado_empleado if instrumento.resultados.filter(evaluacion = evaluacion).exists() else None,
                'peso': instrumento.peso,
                'pk': instrumento.pk
            } for instrumento in evaluacion.formulario.instrumentos.all()
        ] if evaluacion else None
        return context

    def get(self, request):
        return render(request, 'core/dashboard.html', context=self.get_context_data())

class PanelDeControl(LoginRequiredMixin, View, PeriodoContextMixin):
    template_name = 'core/panel_control.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evaluaciones_periodo = Evaluacion.objects.filter(periodo=context['periodo'])
        evaluaciones = {
            'evaluaciones_pendientes': {'count': evaluaciones_periodo.filter(estado='P').count(), 'porcentaje': (evaluaciones_periodo.filter(estado='P').count() / evaluaciones_periodo.count()) * 100},
            'evaluaciones_iniciadas': {'count': evaluaciones_periodo.filter(estado='E').count(), 'porcentaje': (evaluaciones_periodo.filter(estado='E').count() / evaluaciones_periodo.count()) * 100},
            'evaluaciones_enviadas_supervisor': {'count': evaluaciones_periodo.filter(estado='S').count(), 'porcentaje': (evaluaciones_periodo.filter(estado='S').count() / evaluaciones_periodo.count()) * 100},
            'evaluaciones_revisadas': {'count': evaluaciones_periodo.filter(estado='G').count(), 'porcentaje': (evaluaciones_periodo.filter(estado='G').count() / evaluaciones_periodo.count()) * 100},
            'evaluaciones_enviadas_gghh': {'count': evaluaciones_periodo.filter(estado='H').count(), 'porcentaje': (evaluaciones_periodo.filter(estado='H').count() / evaluaciones_periodo.count()) * 100},
            'evaluaciones_aprobadas': {'count': evaluaciones_periodo.filter(estado='A').count(), 'porcentaje': (evaluaciones_periodo.filter(estado='A').count() / evaluaciones_periodo.count()) * 100},
            'evaluaciones_rechazadas': {'count': evaluaciones_periodo.filter(estado='R').count(), 'porcentaje': (evaluaciones_periodo.filter(estado='R').count() / evaluaciones_periodo.count()) * 100},
        }
        context['evaluaciones'] = evaluaciones

        context['personal_evaluado'] = DatosPersonal.objects.filter(activo=True, evaluaciones__periodo=context['periodo']).count()
        context['personal_finalizado'] = DatosPersonal.objects.filter(activo=True, evaluaciones__periodo=context['periodo'], evaluaciones__estado='A').count()
        context['porcentaje_finalizado'] = (context['personal_finalizado'] / context['personal_evaluado']) * 100
        return context

    def get(self, request):
        if not request.user.is_superuser:
            return redirect('dashboard')
        
        return render(request, self.template_name, self.get_context_data())