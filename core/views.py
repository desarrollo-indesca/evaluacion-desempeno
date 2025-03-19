from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.contrib.sessions.models import Session
from core.email import send_mail_async
from .forms import PeriodoForm
from django.views.generic.list import ListView
from django.db.models import Q
from django.db import transaction
from django.contrib import messages
from django.views import View
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from datetime import date, timedelta
from core.models import *
from evaluacion.models import Evaluacion, Formulario
from core.reportes.generate_reports import create_dnf, fill_resumen_periodo, fill_resultado_apoyo, fill_resultado_operativo

# Create your views here.

class SuperuserMixin():
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
class ValidarMixin():
    def validar(self) -> bool:
        ...

    def dispatch(self, request, *args, **kwargs):
        if(self.validar()):
            return super().dispatch(request, *args, **kwargs)
        
        return redirect('dashboard')
    
class EvaluadoMatchMixin():
    def dispatch(self, request, *args, **kwargs):
        evaluacion = Evaluacion.objects.filter(pk=self.kwargs['pk']).first()
        if not evaluacion or evaluacion.evaluado.user != request.user:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
class GerenteMixin():
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

class PeriodoContextMixin():
    def get_periodo(self):
        return Periodo.objects.get(activo=True) if Periodo.objects.filter(activo=True).exists() else None

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
    success_url = '/'

    def post(self, request, *args, **kwargs):
        username_or_ficha = request.POST.get('username').strip().lower()
        password = request.POST.get('password').strip()
            
        with transaction.atomic():
            user = authenticate(request, username=username_or_ficha, password=password)

            if not user:
                try:
                    datos_personal = DatosPersonal.objects.get(ficha=username_or_ficha)
                    user = authenticate(request, username=datos_personal.user.username, password=password)
                except Exception as e:
                    print(str(e))
                    user = None

            if user is not None:
                login(request, user)
            else:
                messages.error(request, 'Credenciales incorrectas.')
            
            return redirect(self.success_url)
    
    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect(reverse_lazy('dashboard'))
        else:
            return render(request, self.template_name, context=self.get_context_data())

class Dashboard(LoginRequiredMixin, View, PeriodoContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['datos_personal'] = DatosPersonal.objects.get(activo = True, user = self.request.user)

        datos_personal = context['datos_personal']
        evaluacion = Evaluacion.objects.filter(evaluado=datos_personal, periodo = context['periodo']).first()
        context['antiguedad'] = datos_personal.antiguedad()
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

class PanelDeControl(SuperuserMixin, View, PeriodoContextMixin):
    template_name = 'core/panel_control.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if(context['periodo']):
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

            context['personal_evaluado'] = evaluaciones_periodo.exclude(estado__in=['A', 'R']).count()
            context['personal_finalizado'] = evaluaciones_periodo.filter(estado='A').count()        
        return context

    def get(self, request):
        if not request.user.is_superuser:
            return redirect('dashboard')
        
        return render(request, self.template_name, self.get_context_data())
    
class PeriodoListView(SuperuserMixin, ListView):
    model = Periodo
    template_name = 'core/periodo_list.html'
    context_object_name = 'periodos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['periodo'] = Periodo.objects.filter(activo=True).first() if Periodo.objects.filter(activo=True).exists() else None
        return context

class PeriodoCreateView(SuperuserMixin, FormView):
    template_name = 'core/periodo_form.html'
    form_class = PeriodoForm
    success_url = reverse_lazy('periodo_lista')

    def form_valid(self, form):
        form.save()

        six_months_from_inicio = form.instance.fecha_fin - timedelta(days=183)
        personal = DatosPersonal.objects.filter(
            fecha_ingreso__lte=six_months_from_inicio, 
            activo=True
        )

        correos = []

        for dp in personal:
            Evaluacion.objects.get_or_create(evaluado=dp, 
                periodo=form.instance, 
                formulario = Formulario.objects.get(
                    tipo_personal=dp.tipo_personal, 
                    activo=True
                ), 
            )

            if(dp.user.email):
                correos.append(dp.user.email)

        if(len(correos) > 0):
            send_mail_async(
                'Nuevo periodo de evaluación de Desempeño',
                f'Como Gerente de Gestión Humana, emito este mensaje para informar que el período de evaluación de desempeño {form.instance.__str__()} ha sido habilitado para que todo el personal realice su evaluación de desempeño. Por favor, ingresen a través del siguiente enlace: {self.request.headers.get("Referer")} para realizar su evaluación, haciendo uso de su número de ficha y clave de máquina.',
                correos,
                sender='kchirino@indesca.com',
            )

        return super().form_valid(form)
    
    def form_invalid(self, form):
        return super().form_invalid(form)

class CerrarPeriodoView(SuperuserMixin, View):
    def post(self, request, pk):
        periodo = Periodo.objects.get(pk=pk)
        if periodo.activo and request.user.is_superuser:
            periodo.activo = False
            periodo.save()

        return redirect('periodo_lista')

class GenerarReportesPeriodo(SuperuserMixin, View):
    def get(self, request):
        periodos = Periodo.objects.filter(activo=False).order_by('-fecha_inicio')
        return render(request, 'core/dnf.html', context={'periodos': periodos})
    
    def post(self, request):
        periodo = Periodo.objects.get(pk=request.POST.get('periodo'))
        tipo = request.POST.get('tipo')

        if(tipo == 'dnf'):
            return create_dnf(periodo)
        elif(tipo == 'resumen'):
            return fill_resumen_periodo(periodo)
    
class GenerarReporteFinal(ValidarMixin, View):
    def validar(self):
        evaluacion = Evaluacion.objects.get(pk=self.kwargs.get('pk'))

        return (self.request.user.is_superuser 
            or self.request.user.is_staff 
            or self.request.user.id == evaluacion.evaluado.supervisor.user.pk 
            or self.request.user.id == evaluacion.evaluado.user.pk
        )

    def get(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)

        return fill_resultado_apoyo(evaluacion) if evaluacion.evaluado.tipo_personal.nombre == "APOYO" else fill_resultado_operativo(evaluacion)