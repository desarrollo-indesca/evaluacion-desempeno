from django.views import View
from .models import *
from django.shortcuts import render, redirect
from core.views import PeriodoContextMixin
from django.db import transaction, models 
from .forms import FormularioRespuestasEmpleado
from django.contrib import messages

# Create your views here.

class ComenzarEvaluacion(View):
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)
        evaluacion.estado = 'E'
        evaluacion.save()
        return redirect('dashboard')
    
class FormularioInstrumentoEmpleado(PeriodoContextMixin, View):
    def get_context_data(self, post=False, **kwargs):
        context = super().get_context_data(**kwargs)
        instrumento = Instrumento.objects.filter(id=self.kwargs['pk']).prefetch_related(
            models.Prefetch(
                'secciones',
                queryset=Seccion.objects.prefetch_related(models.Prefetch(
                    'preguntas', 
                    queryset=Pregunta.objects.prefetch_related('opciones')
                )), 
            )
        ).first()

        context['instrumento'] = [{
                'preguntas': [{
                    'form': FormularioRespuestasEmpleado(prefix=pregunta.pk, initial={
                        'pregunta': pregunta
                    }) if not post else FormularioRespuestasEmpleado(self.request.POST, prefix=pregunta.pk),
                    'pregunta': pregunta,
                } for pregunta in seccion.preguntas.all()],
                'seccion': seccion
            } for seccion in instrumento.secciones.all()
        ]

        context['titulo'] = instrumento.nombre.title()

        return context
    
    def post(self, request, pk):
        instrumento = Instrumento.objects.get(pk=pk)

        try:
            with transaction.atomic():
                evaluacion = Evaluacion.objects.get(evaluado=request.user.datos_personal.get(activo=True), periodo=self.get_periodo(), fecha_fin__isnull=True)
                for seccion in instrumento.secciones.all():
                    for pregunta in seccion.preguntas.all():
                        form = FormularioRespuestasEmpleado(request.POST, prefix=pregunta.pk)
                        if form.is_valid():
                            form.instance.evaluacion = evaluacion
                            form.save()
                        else:
                            print(form.errors)
                            raise Exception(str(form.errors))
                        
                if evaluacion.resultados.filter(instrumento=instrumento).exists():
                    resultado = evaluacion.resultados.get(instrumento=instrumento)
                else:
                    resultado = ResultadoInstrumento(evaluacion=evaluacion, instrumento=instrumento)
                    resultado.save()
                    
        except Exception as e:
            print(str(e))
            context = self.get_context_data(True)
            return render(request, 'evaluacion/formulario_generico.html', context)
        
        messages.success(request, 'Respuestas del Instrumento almacenadas correctamente.')
        return redirect('dashboard')

    def get(self, request, pk):
        return render(request, 'evaluacion/formulario_generico.html', context=self.get_context_data())