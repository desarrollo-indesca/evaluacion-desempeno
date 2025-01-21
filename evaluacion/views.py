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
        evaluacion = Evaluacion.objects.get(evaluado=self.request.user.datos_personal.get(activo=True), periodo=self.get_periodo())
        instrumento = Instrumento.objects.filter(id=self.kwargs['pk']).prefetch_related(
            models.Prefetch(
                'secciones',
                queryset=Seccion.objects.prefetch_related(models.Prefetch(
                    'preguntas', 
                    queryset=Pregunta.objects.prefetch_related('opciones', 'respuestas')
                )), 
            )
        ).first()
        
        if(instrumento.resultados.filter(evaluacion = evaluacion).exists()):
            context['instrumento'] = [{
                    'preguntas': [{
                        'form': FormularioRespuestasEmpleado(instance=pregunta.respuestas.get(evaluacion=evaluacion), prefix=pregunta.pk) if not post else FormularioRespuestasEmpleado(self.request.POST, prefix=pregunta.pk),
                        'pregunta': pregunta,
                    } for pregunta in seccion.preguntas.all()],
                    'seccion': seccion
                } for seccion in instrumento.secciones.all()
            ]
        else:
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
                resultado_instrumento = ResultadoInstrumento.objects.get_or_create(
                    evaluacion=evaluacion, 
                    instrumento=instrumento
                )[0]
                
                for seccion in instrumento.secciones.all():
                    total = 0
                    for pregunta in seccion.preguntas.all():
                        form = FormularioRespuestasEmpleado(request.POST, 
                                                            instance=pregunta.respuestas.get(evaluacion=evaluacion) if pregunta.respuestas.filter(evaluacion=evaluacion).exists() else None, 
                                                            prefix=pregunta.pk)
                        if form.is_valid():
                            form.instance.evaluacion = evaluacion
                            form.save()

                            total += form.instance.respuesta_empleado
                        else:
                            print(form.errors)
                            raise Exception(str(form.errors))

                    # TODO : chequear el archivo para ver el cálculo de los instrumentos
                    if instrumento.calculo == 'P':
                        total = total / seccion.preguntas.count()
                    elif instrumento.calculo == 'S':
                        total = total / seccion.preguntas.count()

                    ResultadoSeccion.objects.update_or_create(
                        seccion=seccion, 
                        resultado_instrumento=resultado_instrumento, 
                        defaults={
                            'resultado_empleado': total,
                        }
                    )
                    
                resultado_instrumento.resultado_empleado = resultado_instrumento.resultados_secciones.aggregate(models.Sum('resultado_empleado'))['resultado_empleado__sum']
                resultado_instrumento.save()
                    
        except Exception as e:
            print(str(e))
            context = self.get_context_data(True)
            return render(request, 'evaluacion/formulario_generico.html', context)
        
        messages.success(request, 'Respuestas del Instrumento almacenadas correctamente.')
        return redirect('dashboard')

    def get(self, request, pk):
        return render(request, 'evaluacion/formulario_generico.html', context=self.get_context_data())