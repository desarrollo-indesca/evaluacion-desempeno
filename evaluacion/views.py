from django.views import View
from django.views.generic import ListView
from django.http import HttpResponseForbidden
from django.forms import modelformset_factory
from django.shortcuts import render, redirect
from django.db import transaction, models 
from django.contrib import messages
import datetime
from .models import *
from .forms import *
from .filters import *
from core.views import PeriodoContextMixin, EvaluacionEstadoMixin

# Create your views here.

class ComenzarEvaluacion(View):
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)

        if(evaluacion.estado == 'P'):
            evaluacion.estado = 'E'
            evaluacion.save()
            return redirect('dashboard')
        
        return HttpResponseForbidden("Una vez empezada la evaluación no puede modificar su estado.")

class FinalizarEvaluacion(View):
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)

        if(evaluacion.estado == 'E' and (
            evaluacion.resultados.count() == evaluacion.formulario.instrumentos.count() and
            evaluacion.formaciones.count() and evaluacion.logros_y_metas.count()
        )):
            evaluacion.estado = 'S'
            evaluacion.fecha_envio = datetime.datetime.now()
            evaluacion.comentario_evaluado = request.POST.get('comentarios')
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

        with transaction.atomic():
                evaluacion = Evaluacion.objects.get(evaluado=request.user.datos_personal.get(activo=True), periodo=self.get_periodo(), fecha_fin__isnull=True)
                resultado_instrumento = ResultadoInstrumento.objects.get_or_create(
                    evaluacion=evaluacion, 
                    instrumento=instrumento
                )[0]

                total_instrumento = 0 if instrumento.calculo != 'M' else 1e9
                max_instrumento = 0 if instrumento.calculo == 'S' else 1e9 if instrumento.calculo == 'M' else instrumento.secciones.count()     
                for seccion in instrumento.secciones.all():
                    max_seccion = 0
                    total = 0 if seccion.calculo != 'M' else 1e9
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
                            elif(seccion.calculo == 'M'):
                                total = min(total, form.instance.respuesta_empleado)
                        else:
                            context = {} 
                            context['instrumento'] = [{
                                    'preguntas': [{
                                        'form': FormularioRespuestasEmpleado(request.POST, prefix=pregunta.pk, initial={
                                            'pregunta': pregunta
                                        }),
                                        'pregunta': pregunta,
                                    } for pregunta in seccion.preguntas.all()],
                                    'seccion': seccion
                                } for seccion in instrumento.secciones.all()
                            ]

                            return render(
                                request, self.template_name,
                                context
                            )
                        
                        print(total)

                    total = round(total, 2)
                    print(total)

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
                        total_instrumento += total

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

    def get_queryset(self, evaluacion):
        return evaluacion.formaciones.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])

        context['formset'] = modelformset_factory(
            Formacion, form=FormularioFormacion, exclude = ('evaluacion', 'anadido_por', 'activo'),
        ) if not evaluacion.formaciones.exists() else modelformset_factory(
            Formacion, form=FormularioFormacion, exclude = ('evaluacion', 'anadido_por', 'activo'),
            extra = 0
        )(queryset = self.get_queryset(evaluacion), initial=[{'competencias_tecnicas': [c.pk for c in form.competencias.filter(tipo='T')]} for form in evaluacion.formaciones.all()])

        context['titulo'] = "Detección de Necesidades de Formación"
        context['evaluacion'] = evaluacion

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
    anadido_por = "E"

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

    def queryset_actual(self, evaluacion):
        return evaluacion.logros_y_metas.filter(periodo = "A")
    
    def queryset_proximo(self, evaluacion):
        return evaluacion.logros_y_metas.filter(periodo = "P")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])
        context['formset_actual'], context['formset_proximo'] = self.get_formsets(True, self.queryset_actual(evaluacion), self.queryset_proximo(evaluacion))
        context['titulo'] = "Formulario de Logros y Metas"

        return context

    def post(self, request, pk, *args, **kwargs):
        evaluacion = Evaluacion.objects.get(pk=pk)

        formset_actual, formset_proximo = self.get_formsets()

        formset_actual = formset_actual(request.POST, prefix="form-actual")
        formset_proximo = formset_proximo(request.POST, prefix="form-proximo")

        with transaction.atomic():
            evaluacion.logros_y_metas.filter(anadido_por=self.anadido_por).delete()

            formset_actual.is_valid()
            for form in formset_actual:
                if(form.is_valid()):
                    form.instance.evaluacion = evaluacion
                    form.instance.anadido_por = self.anadido_por
                    form.instance.periodo = "A"
                    form.save()

            formset_proximo.is_valid()
            for form in formset_proximo:
                if(form.is_valid()):
                    form.instance.evaluacion = evaluacion
                    form.instance.periodo = "P"
                    form.instance.anadido_por = self.anadido_por
                    form.save()
        
        return redirect('dashboard')
    
class ResultadosPorInstrumentoYVersion(View):
    template_name = 'evaluacion/resultados_por_inst_y_version.html'
    def get(self, request, **args):
            evaluacion = Evaluacion.objects.get(pk=request.GET['pk'])
            instrumento = ResultadoInstrumento.objects.get(pk=request.GET['instrumento'])
            valor = request.GET['version']

            secciones = []
            for seccion in instrumento.resultados_secciones.all(): 
                max_seccion = seccion.seccion.preguntas.aggregate(models.Sum('peso')).get('peso__sum')
                max_relativo = 0 
                valor_relativo = 0               
                for pregunta in seccion.seccion.preguntas.all():
                    respuesta = pregunta.respuestas.get(evaluacion=evaluacion).respuesta_empleado if valor == 'E' else pregunta.respuestas.get(evaluacion=evaluacion).respuesta_supervisor if valor == 'S' else pregunta.respuestas.get(evaluacion=evaluacion).respuesta_final
                    if(respuesta >= 0):
                        max_relativo += pregunta.peso
                        valor_relativo += respuesta*pregunta.peso/2
                
                secciones.append(
                    {
                        'nombre': seccion.seccion.titulo(),
                        'peso': seccion.seccion.peso,
                        'max_relativo': max_relativo,
                        'resultado': seccion.resultado_empleado if valor == 'E' else seccion.resultado_supervisor if valor == 'S' else seccion.resultado_final,
                        'calculo': seccion.seccion.calculo,
                        'seccion': seccion.seccion,
                        'valor_relativo': valor_relativo,
                        'valor_ponderado': (float(seccion.seccion.instrumento.peso) * float(max_seccion) / 100) * float(seccion.resultado_empleado / seccion.seccion.peso)  if seccion.seccion.calculo == 'S' else float(seccion.seccion.instrumento.peso) * float(seccion.resultado_empleado),
                        'preguntas': []
                    } 
                )               

                for pregunta in seccion.seccion.preguntas.all():
                    secciones[-1]['preguntas'].append(
                        {
                            'pregunta': pregunta.pregunta,
                            'peso': pregunta.peso,
                            'respuesta_ponderada': pregunta.respuestas.get(evaluacion=evaluacion).respuesta_empleado / 2 * float(pregunta.peso) if pregunta.respuestas.filter(evaluacion=evaluacion).exists() else None,
                            'respuesta': next((opcion for opcion in pregunta.opciones.all() if opcion.valor == (pregunta.respuestas.get(evaluacion=evaluacion).respuesta_empleado if valor == 'E' else pregunta.respuestas.get(evaluacion=evaluacion).respuesta_supervisor if valor == 'S' else pregunta.respuestas.get(evaluacion=evaluacion).respuesta_final)), None),
                            'comentario': {
                                'empleado': pregunta.respuestas.get(evaluacion=evaluacion).comentario_empleado if pregunta.respuestas.filter(evaluacion=evaluacion).exists() else None,
                                'supervisor': pregunta.respuestas.get(evaluacion=evaluacion).comentario_supervisor if pregunta.respuestas.filter(evaluacion=evaluacion).exists() else None,
                                'gghh': pregunta.respuestas.get(evaluacion=evaluacion).comentario_gghh if pregunta.respuestas.filter(evaluacion=evaluacion).exists() else None,   
                            },
                        }
                    )

            return render(
                request, 
                self.template_name,
                {
                    'secciones': secciones,
                    'instrumento': instrumento,
                    
                }
            )

class ConsultaFormacionesEvaluacion(View):
    template_name = "evaluacion/partials/consulta_formacion.html"

    def get(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)
        formaciones = evaluacion.formaciones.filter(anadido_por=request.GET.get('version'))
        for formacion in formaciones:
            formacion.competencias_genericas = formacion.competencias.filter(tipo='G')
            formacion.competencias_tecnicas = formacion.competencias.filter(tipo='T')

        return render(request, self.template_name, {'formaciones': formaciones, 'evaluacion': evaluacion})
    
class ConsultaLogrosMetas(View):
    template_name = "evaluacion/partials/consulta_logros_metas.html"

    def get(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)
        metas = evaluacion.logros_y_metas.filter(anadido_por=request.GET.get('version'), activo=True)

        metas_periodo_actual = metas.filter(periodo='A')
        metas_periodo_proximo = metas.filter(periodo='P')
        
        return render(request, self.template_name, {'metas_periodo_actual': metas_periodo_actual, 'metas_periodo_proximo': metas_periodo_proximo})

class ConsultaEvaluaciones(ListView):
    template_name = "evaluacion/partials/lista_evaluaciones.html"
    model = Evaluacion
    filter_class = EvaluacionFilter
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter_class(self.request.GET, queryset=self.get_queryset())
        context['datos_personal'] = self.request.user.datos_personal.get(activo=True)
        return context

    def get_queryset(self):
        return super().get_queryset().filter(
            evaluado=self.request.user.datos_personal.get(activo=True)
        )

class RevisionSupervisados(PeriodoContextMixin, ListView):
    template_name = "evaluacion/partials/lista_evaluaciones_supervisores.html"
    model = DatosPersonal
    template_name = "evaluacion/partials/revision_supervisados.html"
    filter_class = DatosPersonalFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter_class(self.request.GET, queryset=self.get_queryset())
        context['datos_personal'] = self.request.user.datos_personal.get(activo=True)
        return context

    def get_queryset(self):
        return super().get_queryset().filter(supervisor=self.request.user.datos_personal.get(activo=True), activo=True)

class HistoricoEvaluacionesSupervisado(PeriodoContextMixin, ListView):
    template_name = "evaluacion/partials/lista_evaluaciones.html"
    model = Evaluacion
    filter_class = EvaluacionFilter
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter_class(self.request.GET, queryset=self.get_queryset())
        context['datos_personal'] = DatosPersonal.objects.get(pk=self.kwargs['pk'])
        context['supervisado'] = True
        return context
    
    def get(self, request, *args, **kwargs):
        if(request.user.datos_personal.get(
                activo=True
            ).supervisados.filter(pk=self.kwargs['pk']).exists()):
            return super().get(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    def get_queryset(self):
        return super().get_queryset().filter(evaluado__pk=self.kwargs['pk'])

# VISTAS SUPERVISIÓN
class FormularioInstrumentoSupervisor(PeriodoContextMixin, EvaluacionEstadoMixin, View):
    estado = "S"
    template_name = "evaluacion/partials/formulario_supervisor.html"

    def get_context_data(self, post=False, **kwargs):
        context = super().get_context_data(**kwargs)
        evaluacion = Evaluacion.objects.get(
            pk=self.kwargs['evaluacion']
        )
        instrumento = Instrumento.objects.filter(id=self.kwargs['pk']).prefetch_related(
            models.Prefetch(
                'secciones',
                queryset=Seccion.objects.prefetch_related(models.Prefetch(
                    'preguntas', 
                    queryset=Pregunta.objects.prefetch_related('opciones', 'respuestas')
                )), 
            )
        ).first()
        
        context['instrumento'] = []
        for seccion in instrumento.secciones.all():
            preguntas_data = []
            for pregunta in seccion.preguntas.all():
                respuesta = pregunta.respuestas.get(evaluacion=evaluacion)
                initial_data = {
                    'pregunta': pregunta,
                    'respuesta_supervisor': respuesta.respuesta_empleado if not respuesta.respuesta_supervisor else respuesta.respuesta_supervisor,
                    'comentario_supervisor': respuesta.comentario_supervisor
                }
                form = FormularioRespuestasSupervisor(
                    instance=respuesta, 
                    prefix=pregunta.pk, 
                    initial=initial_data
                ) if not post else FormularioRespuestasSupervisor(
                    self.request.POST, 
                    prefix=pregunta.pk
                )
                
                preguntas_data.append({'form': form, 'pregunta': pregunta})
            
            context['instrumento'].append({'preguntas': preguntas_data, 'seccion': seccion})

        context['titulo'] = instrumento.nombre.title()
        context['pk'] = instrumento.pk
        context['evaluacion'] = evaluacion

        return context
    
    def post(self, request, pk, evaluacion):
        instrumento = Instrumento.objects.get(pk=pk)

        with transaction.atomic():
                evaluacion = Evaluacion.objects.get(
                    pk=evaluacion
                )
                resultado_instrumento = ResultadoInstrumento.objects.get(
                    evaluacion=evaluacion, 
                    instrumento=instrumento
                )

                total_instrumento = 0 if instrumento.calculo != 'M' else 1e9
                max_instrumento = 0 if instrumento.calculo == 'S' else 1e9 if instrumento.calculo == 'M' else instrumento.secciones.count()     
                for seccion in instrumento.secciones.all():
                    max_seccion = 0
                    total = 0 if seccion.calculo != 'M' else 1e9
                    for pregunta in seccion.preguntas.all():
                        form = FormularioRespuestasSupervisor(
                            request.POST, 
                            instance=pregunta.respuestas.get(evaluacion=evaluacion) if pregunta.respuestas.filter(evaluacion=evaluacion).exists() else None, 
                            prefix=pregunta.pk
                        )

                        if form.is_valid():
                            form.instance.evaluacion = evaluacion
                            form.save()

                            if(seccion.calculo == 'S' and form.instance.respuesta_supervisor >= 0):
                                max_seccion += form.instance.pregunta.peso
                                total += form.instance.pregunta.peso * form.instance.respuesta_supervisor / 2
                            elif(seccion.calculo == 'P'):
                                total += form.instance.respuesta_supervisor
                                max_seccion += 1
                            elif(seccion.calculo == 'M'):
                                total = min(total, form.instance.respuesta_supervisor)
                        else:
                            context = {} 
                            context['instrumento'] = [{
                                    'preguntas': [{
                                        'form': FormularioRespuestasSupervisor(request.POST, prefix=pregunta.pk, initial={
                                            'pregunta': pregunta
                                        }),
                                        'pregunta': pregunta,
                                    } for pregunta in seccion.preguntas.all()],
                                    'seccion': seccion
                                } for seccion in instrumento.secciones.all()
                            ]

                            context['titulo'] = instrumento.nombre.title()
                            context['pk'] = instrumento.pk
                            context['evaluacion'] = evaluacion

                            return render(
                                request, self.template_name,
                                context
                            )
                        
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
                        total_instrumento += total

                    resultado_seccion = ResultadoSeccion.objects.get(
                        seccion=seccion, 
                        resultado_instrumento=resultado_instrumento
                    )

                    resultado_seccion.resultado_supervisor = total
                    resultado_seccion.save()

                if(instrumento.calculo == 'S'):
                    total_instrumento = total_instrumento*instrumento.peso/max_instrumento
                elif(instrumento.calculo == 'P'):
                    total_instrumento = total_instrumento / max_instrumento
               
                resultado_instrumento.resultado_supervisor = total_instrumento
                resultado_instrumento.save()

                print(resultado_instrumento.resultado_supervisor)
        
        messages.success(request, 'Respuestas del Instrumento almacenadas correctamente.')
        return redirect('revisar_evaluacion', pk=evaluacion.pk)

class RevisionEvaluacion(PeriodoContextMixin, EvaluacionEstadoMixin, View):
    estado = "S"
    template_name = 'evaluacion/partials/revision_evaluacion.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])

        context['evaluacion'] = evaluacion

        context['puede_finalizar'] = evaluacion.resultados.filter(resultado_supervisor__isnull=False).count() == evaluacion.formulario.instrumentos.count() and (
            evaluacion.formaciones.filter(anadido_por="S").exists() 
            and 
            evaluacion.logros_y_metas.filter(anadido_por="S").exists() 
        ) if evaluacion else False

        context['instrumentos'] = [
            {
                'nombre': instrumento.nombre,
                'completado': instrumento.resultados.filter(evaluacion = evaluacion, resultado_supervisor__isnull=False).exists(),
                'resultado_empleado': instrumento.resultados.filter(evaluacion = evaluacion).first().resultado_empleado if instrumento.resultados.filter(evaluacion = evaluacion).exists() else None,
                'resultado_supervisor': instrumento.resultados.filter(evaluacion = evaluacion).first().resultado_supervisor if instrumento.resultados.filter(evaluacion = evaluacion).exists() else None,
                'peso': instrumento.peso,
                'pk': instrumento.pk
            } for instrumento in evaluacion.formulario.instrumentos.all()
        ] if evaluacion else None

        context['formaciones'] = evaluacion.formaciones.filter(anadido_por="S")
        context['logros_y_metas'] = evaluacion.logros_y_metas.filter(anadido_por="S")

        return context
    
class FormacionSupervisor(FormacionEmpleado):
    template_name = "evaluacion/formacion_empleado.html"
    estado = "S"
    anadido_por = "S"

    def get_queryset(self, evaluacion):
        qs = evaluacion.formaciones.filter(anadido_por = "S", activo = True)
        
        if(qs.exists()):
            return qs
        else:
            return evaluacion.formaciones.filter(activo = True)

class LogrosYMetasSupervisor(MetasEmpleado):
    estado = "S"
    anadido_por = "S"

    def queryset_actual(self, evaluacion):
        qs = evaluacion.logros_y_metas.filter(anadido_por="S", periodo = "A")
        
        if(qs.exists()):
            return qs
        else:
            return evaluacion.logros_y_metas.filter(periodo="A")
    
    def queryset_proximo(self, evaluacion):
        qs = evaluacion.logros_y_metas.filter(anadido_por="S", periodo = "P")
        
        if(qs.exists()):
            return qs
        else:
            return evaluacion.logros_y_metas.filter(periodo="P")