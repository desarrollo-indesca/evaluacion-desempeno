from django.views import View
from django.http import HttpResponseForbidden
from django.forms import modelformset_factory
from .models import *
from django.shortcuts import render, redirect
from core.views import PeriodoContextMixin, EvaluacionEstadoMixin
from django.db import transaction, models 
from .forms import *
from django.contrib import messages

# Create your views here.

class ComenzarEvaluacion(View):
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)

        if(evaluacion.estado == 'P'):
            evaluacion.estado = 'E'
            evaluacion.save()
            return redirect('dashboard')
        
        return HttpResponseForbidden("Una vez empezada la evaluación no puede modificar su estado.")
    
class FormularioInstrumentoEmpleado(PeriodoContextMixin, EvaluacionEstadoMixin, View):
    template_name = 'evaluacion/formulario_generico.html'
    estado = "E"

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

        if(True):
            with transaction.atomic():
                evaluacion = Evaluacion.objects.get(evaluado=request.user.datos_personal.get(activo=True), periodo=self.get_periodo(), fecha_fin__isnull=True)
                resultado_instrumento = ResultadoInstrumento.objects.get_or_create(
                    evaluacion=evaluacion, 
                    instrumento=instrumento
                )[0]

                total_instrumento = 0 
                max_instrumento = 0 if instrumento.calculo == 'S' else 1e9 if instrumento.calculo == 'M' else instrumento.secciones.count()     
                for seccion in instrumento.secciones.all():
                    max_seccion = 0
                    total = 0
                    for pregunta in seccion.preguntas.all():
                        form = FormularioRespuestasEmpleado(request.POST, 
                                                            instance=pregunta.respuestas.get(evaluacion=evaluacion) if pregunta.respuestas.filter(evaluacion=evaluacion).exists() else None, 
                                                            prefix=pregunta.pk)
                        if form.is_valid():
                            form.instance.evaluacion = evaluacion
                            form.save()

                            if(seccion.calculo == 'S' and form.instance.respuesta_empleado >= 0):
                                max_seccion += form.instance.pregunta.peso
                                total += form.instance.pregunta.peso * form.instance.respuesta_empleado / 2
                            elif(seccion.calculo == 'P'):
                                total += form.instance.respuesta_empleado
                                max_seccion += 1
                        else:
                            print(form.errors)
                            raise Exception(str(form.errors))

                    total = round(total, 2)

                    if(seccion.calculo == 'S'):
                        if(total > 0):
                            total = total*seccion.peso/max_seccion
                            total_instrumento += total
                            max_instrumento += seccion.peso
                        else:
                            total = None
                    elif(seccion.calculo == 'P'):
                        total = total / max_seccion
                        total_instrumento += total
                    elif(seccion.calculo == 'M'):
                        total_instrumento = min(total_instrumento, total)

                    ResultadoSeccion.objects.update_or_create(
                        seccion=seccion, 
                        resultado_instrumento=resultado_instrumento, 
                        defaults={
                            'resultado_empleado': total,
                        }
                    )

                if(instrumento.calculo == 'S'):
                    total_instrumento = total_instrumento*instrumento.peso/max_instrumento
                elif(instrumento.calculo == 'P'):
                    total_instrumento = total_instrumento / max_instrumento
               
                resultado_instrumento.resultado_empleado = total_instrumento
                resultado_instrumento.save()
        
        messages.success(request, 'Respuestas del Instrumento almacenadas correctamente.')
        return redirect('dashboard')

class FormacionEmpleado(PeriodoContextMixin, EvaluacionEstadoMixin, View):
    template_name = "evaluacion/formacion_empleado.html"
    estado = "E"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])

        context['formset'] = modelformset_factory(
            Formacion, form=FormularioFormacion, exclude = ('evaluacion', 'anadido_por', 'activo'),
        ) if not evaluacion.formaciones.exists() else modelformset_factory(
            Formacion, form=FormularioFormacion, exclude = ('evaluacion', 'anadido_por', 'activo'),
            extra = 0
        )(queryset = evaluacion.formaciones.all(), initial=[{'competencias_tecnicas': [c.pk for c in form.competencias.filter(tipo='T')]} for form in evaluacion.formaciones.all()])

        context['titulo'] = "Detección de Necesidades de Formación"

        return context
    
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)

        formset = modelformset_factory(
            Formacion, form=FormularioFormacion, exclude = ('evaluacion', 'anadido_por', 'activo', 'competencias'),
        )(request.POST)

        if formset.is_valid():
            with transaction.atomic():
                evaluacion.formaciones.all().delete()
                for form in formset:
                    form.instance.evaluacion = evaluacion
                    form.instance.anadido_por = "E"
                    form.save()

                    competencias_tecnicas = form.cleaned_data.get('competencias_tecnicas')
                    competencias_genericas = form.cleaned_data.get('competencias_genericas')

                    for competencia in competencias_tecnicas:
                        form.instance.competencias.add(competencia)

                    for competencia in competencias_genericas:
                        form.instance.competencias.add(competencia)

        else:
            print(formset.errors)
            raise Exception(str(formset.errors))

        messages.success(request, 'Respuestas de Formación almacenadas correctamente.')
        return redirect('dashboard')
    
class MetasEmpleado(PeriodoContextMixin, EvaluacionEstadoMixin, View):
    template_name = "evaluacion/metas_empleado.html"
    estado = "E"

    def get_formsets(self, add_prefixes = False, qs_actual = None, qs_proximo = None):
        formset_actual = modelformset_factory(
            LogrosYMetas, form=FormularioMetas, exclude = ('anadido_por', 'activo', 'periodo', 'evaluacion'),
            min_num=0, extra = 0 if qs_actual else 1
        )

        formset_proximo = modelformset_factory(
            LogrosYMetas, form=FormularioMetas, exclude = ('anadido_por', 'activo', 'periodo', 'evaluacion'),
            min_num=0, extra = 0 if qs_proximo else 1
        )

        if(add_prefixes and qs_actual and qs_proximo):
            formset_actual = formset_actual(queryset=qs_actual, prefix="form-actual")
            formset_proximo = formset_proximo(queryset=qs_proximo, prefix="form-proximo")
        elif(add_prefixes):
            formset_actual = formset_actual(prefix="form-actual")
            formset_proximo = formset_proximo(prefix="form-proximo")

        return formset_actual, formset_proximo

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])
        context['formset_actual'], context['formset_proximo'] = self.get_formsets(True, evaluacion.logros_y_metas.filter(periodo = "A"), evaluacion.logros_y_metas.filter(periodo = "P"))
        context['titulo'] = "Formulario de Logros y Metas"

        return context

    def post(self, request, pk, *args, **kwargs):
        evaluacion = Evaluacion.objects.get(pk=pk)

        formset_actual, formset_proximo = self.get_formsets()

        formset_actual = formset_actual(request.POST, prefix="form-actual")
        formset_proximo = formset_proximo(request.POST, prefix="form-proximo")

        with transaction.atomic():
            evaluacion.logros_y_metas.all().delete()

            formset_actual.is_valid()
            for form in formset_actual:
                if(form.is_valid()):
                    form.instance.evaluacion = evaluacion
                    form.instance.periodo = "A"
                    form.save()

            formset_proximo.is_valid()
            for form in formset_proximo:
                if(form.is_valid()):
                    form.instance.evaluacion = evaluacion
                    form.instance.periodo = "P"
                    form.save()
        
        return redirect('dashboard')