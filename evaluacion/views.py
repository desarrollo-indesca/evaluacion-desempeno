from django.views import View
from .models import *
from django.shortcuts import render, redirect
from core.views import PeriodoContextMixin
from django.db import transaction, models 

# Create your views here.

class ComenzarEvaluacion(View):
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)
        evaluacion.estado = 'E'
        evaluacion.save()
        return redirect('dashboard')
    
class FormularioInstrumentoEmpleado(PeriodoContextMixin, View):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['instrumento'] = Instrumento.objects.filter(id=self.kwargs['pk']).prefetch_related(
            models.Prefetch(
                'secciones',
                queryset=Seccion.objects.prefetch_related(models.Prefetch(
                    'preguntas', 
                    queryset=Pregunta.objects.prefetch_related('opciones')
                )), 
            )
        ).first()
        return context

    def get(self, request, pk):
        return render(request, 'evaluacion/formulario_generico.html', context=self.get_context_data())