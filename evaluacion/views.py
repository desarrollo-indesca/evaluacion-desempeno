from django.views import View
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden, HttpResponse
from django.forms import modelformset_factory
from django.shortcuts import render, redirect
from django.db import transaction, models
from django.db.models import Q, Exists, OuterRef, Prefetch
from django.contrib import messages
from core.email import send_mail_async
import datetime
from .models import *
from .forms import *
from .filters import *
from core.models import PeriodoGerencial
from core.views import PeriodoContextMixin, ValidarMixin, EvaluacionEstadoMixin, SuperuserMixin, GerenteMixin, EvaluadoMatchMixin

# Create your views here.

class ValidarEvaluadoMixin(ValidarMixin):
    def validar(self):
        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])
        return evaluacion.evaluado.user.pk == self.request.user.pk
    
class ValidarSupervisorMixin(ValidarMixin):
    def validar(self):
        try:
            evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])
        except:
            evaluacion = Evaluacion.objects.get(pk=self.kwargs['evaluacion'])

        return evaluacion.evaluado.pk in self.request.user.datos_personal.get(activo=True).supervisados.values_list('pk', flat=True)

class ValidarSuperusuario(ValidarMixin):
    def validar(self):
        return self.request.user.is_superuser

class EscalafonMixin():
    def calcular_escalafon(self, resultado_instrumento: ResultadoInstrumento):
        niveles_escalafon = resultado_instrumento.instrumento.escalafon.niveles_escalafon.all()
        calculo = resultado_instrumento.instrumento.calculo_escalafon

        if(calculo == 'M'):
            if(self.estado == "E"):
                nivel_alcanzado = min(seccion.resultado_empleado for seccion in resultado_instrumento.resultados_secciones.all())
            elif(self.estado == "S"):
                nivel_alcanzado = min(seccion.resultado_supervisor for seccion in resultado_instrumento.resultados_secciones.all())
            elif(self.estado == "H"):
                nivel_alcanzado = min(seccion.resultado_final for seccion in resultado_instrumento.resultados_secciones.all())
        elif(calculo == 'P'):
            if self.estado == "E":
                nivel_alcanzado = sum(seccion.resultado_empleado for seccion in resultado_instrumento.resultados_secciones.all()) / len(resultado_instrumento.resultados_secciones.all())
            elif self.estado == "S":
                nivel_alcanzado = sum(seccion.resultado_supervisor for seccion in resultado_instrumento.resultados_secciones.all()) / len(resultado_instrumento.resultados_secciones.all())
            elif self.estado == "H":
                nivel_alcanzado = sum(seccion.resultado_final for seccion in resultado_instrumento.resultados_secciones.all()) / len(resultado_instrumento.resultados_secciones.all())
        elif(calculo == 'S'):
            if self.estado == "E":
                nivel_alcanzado = sum(seccion.resultado_empleado * seccion.seccion.peso for seccion in resultado_instrumento.resultados_secciones.all()) / resultado_instrumento.instrumento.peso
            elif self.estado == "S":
                nivel_alcanzado = sum(seccion.resultado_supervisor * seccion.seccion.peso for seccion in resultado_instrumento.resultados_secciones.all()) / resultado_instrumento.instrumento.peso
            elif self.estado == "H":
                nivel_alcanzado = sum(seccion.resultado_final * seccion.seccion.peso for seccion in resultado_instrumento.resultados_secciones.all()) / resultado_instrumento.instrumento.peso

        highest_nivel = None
        for nivel in niveles_escalafon:
            if highest_nivel is None or nivel_alcanzado > highest_nivel.valor_requerido:
                highest_nivel = nivel

        if highest_nivel:
            ResultadoEscalafon.objects.filter(
                evaluacion=resultado_instrumento.evaluacion,
                asignado_por=self.estado
            ).delete()

            ResultadoEscalafon.objects.create(
                evaluacion=resultado_instrumento.evaluacion,
                asignado_por=self.estado,
                escalafon=highest_nivel
            )

class ComenzarEvaluacion(EvaluadoMatchMixin, View):
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)

        if(evaluacion.estado == 'P'):
            evaluacion.estado = 'E'
            evaluacion.fecha_inicio = datetime.datetime.now()
            evaluacion.save()

            return redirect('dashboard')
        
        return HttpResponseForbidden("Una vez empezada la evaluación no puede modificar su estado.")

class FinalizarEvaluacion(EvaluadoMatchMixin, View):
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)

        with transaction.atomic():
            if(evaluacion.estado == 'E' and (
                evaluacion.resultados.count() == evaluacion.formulario.instrumentos.count() and
                evaluacion.formaciones.count() and evaluacion.logros_y_metas.count()
            )):
                if evaluacion.evaluado.supervisor and not evaluacion.evaluado.supervisor.user.is_superuser:
                    evaluacion.estado = 'S'
                else:
                    evaluacion.fecha_entrega = datetime.datetime.now()
                    evaluacion.estado = 'H'

                evaluacion.fecha_envio = datetime.datetime.now()
                evaluacion.comentario_evaluado = request.POST.get('comentarios')
                evaluacion.save()
                
                if evaluacion.estado == 'S':
                    messages.success(request, 'La evaluación fue enviada a su supervisor.')
                    body = 'La evaluación de desempeño de ' + evaluacion.evaluado.user.get_full_name().upper() + ' ha sido enviada a usted para su revisión en reunión con el empleado; podrá encontrarla en la pestaña "Revisar" del sistema.\n\n'
                    to = [evaluacion.evaluado.supervisor.user.email]
                elif evaluacion.estado == 'H':
                    messages.success(request, 'La evaluación fue enviada a la Gerencia de Gestión Humana.')
                    body = 'La evaluación de desempeño de ' + evaluacion.evaluado.user.get_full_name().upper() + ' ha sido enviada a la Gerencia de Gestión Humana para su revisión final.\n\n'
                    to = [evaluacion.evaluado.supervisor.user.email if evaluacion.evaluado.supervisor else None, DatosPersonal.objects.get(user__is_superuser=True).user.email]

                send_mail_async(
                    'Actualización de Estatus - Evaluación de Desempeño de ' + evaluacion.evaluado.user.get_full_name().upper(),
                    body,
                    to,
                )
                
                return redirect('dashboard')
            
        return HttpResponseForbidden("Una vez empezada la evaluación no puede modificar su estado.")

class FormularioInstrumentoEmpleado(ValidarMixin, PeriodoContextMixin, EscalafonMixin, EvaluacionEstadoMixin, View):
    template_name = 'evaluacion/formulario_generico.html'
    estado = "E"
    success_message = 'Respuestas del Instrumento almacenadas correctamente.'
    form_class = FormularioRespuestasEmpleado

    def validar(self):
        instrumento = Instrumento.objects.filter(id=self.kwargs['pk']).first()
        if not instrumento or instrumento.formulario.tipo_personal != self.request.user.datos_personal.get(activo=True).tipo_personal:
            return False
        return True

    def get_context_data(self, post=False):
        context = super().get_context_data(post=post)        
        evaluacion = Evaluacion.objects.get(
            evaluado=self.request.user.datos_personal.get(activo=True), 
            periodo=self.get_periodo()
        ) if not self.request.GET.get('evaluacion') else Evaluacion.objects.get(
            pk=self.request.GET.get('evaluacion')
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
        
        if(instrumento.resultados.filter(evaluacion = evaluacion).exists()):
            context['instrumento'] = []
            for seccion in instrumento.secciones.all():
                seccion_questions = []
                for pregunta in seccion.preguntas.all():
                    respuestas = pregunta.respuestas.filter(evaluacion=evaluacion)
                    if respuestas.count() > 1:
                        for respuesta in respuestas[:respuestas.count() - 1]:
                            respuesta.delete()
                    seccion_questions.append({
                        'form': self.form_class(instance=pregunta.respuestas.get(evaluacion=evaluacion), prefix=pregunta.pk) if not post else self.form_class(self.request.POST, prefix=pregunta.pk),
                        'pregunta': pregunta,
                    })
                context['instrumento'].append({
                    'preguntas': seccion_questions,
                    'seccion': seccion
                })
        else:
            context['instrumento'] = [{
                    'preguntas': [{
                        'form': self.form_class(prefix=pregunta.pk, initial={
                            'pregunta': pregunta
                        }) if not post else self.form_class(self.request.POST, prefix=pregunta.pk),
                        'pregunta': pregunta,
                    } for pregunta in seccion.preguntas.all()],
                    'seccion': seccion
                } for seccion in instrumento.secciones.all()
            ]

        context['titulo'] = instrumento.nombre.title()
        context['periodo'] = self.get_periodo()

        return context
    
    def post(self, request, pk, evaluacion = None):
        instrumento = Instrumento.objects.get(pk=pk)

        try:
            with transaction.atomic():
                        if(not evaluacion):
                            evaluacion = Evaluacion.objects.get(evaluado=request.user.datos_personal.get(activo=True), periodo=self.get_periodo(), fecha_fin__isnull=True)
                        else:
                            evaluacion = Evaluacion.objects.get(
                                pk=evaluacion
                            )
                        
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
                                form = self.form_class(request.POST, 
                                                                    instance=pregunta.respuestas.get(evaluacion=evaluacion) if pregunta.respuestas.filter(evaluacion=evaluacion).exists() else None, 
                                                                    prefix=pregunta.pk)
                                if form.is_valid():
                                    form.instance.evaluacion = evaluacion
                                    form.save()

                                    if(self.estado == 'E'):
                                        campo = 'resultado_empleado'
                                    elif(self.estado == 'S'):
                                        campo = 'resultado_supervisor'
                                    elif(self.estado == 'H'):
                                        campo = 'resultado_final'

                                    respuesta = None
                                    if self.estado == 'E':
                                        respuesta = form.instance.respuesta_empleado
                                    elif self.estado == 'S':
                                        respuesta = form.instance.respuesta_supervisor
                                    elif self.estado == 'H':
                                        respuesta = form.instance.respuesta_definitiva

                                    if respuesta is not None:
                                        if seccion.calculo == 'S' and respuesta >= 0:
                                            max_seccion += form.instance.pregunta.peso
                                            total += form.instance.pregunta.peso * respuesta / 2
                                        elif seccion.calculo == 'P':
                                            total += respuesta
                                            max_seccion += 1
                                        elif seccion.calculo == 'M' and respuesta != 0:
                                            total = min(total, respuesta)
                                else:
                                    raise Exception("No validó")
                                
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

                            ResultadoSeccion.objects.update_or_create(
                                seccion=seccion, 
                                resultado_instrumento=resultado_instrumento, 
                                defaults={
                                    campo: total,
                                }
                            )

                        if(instrumento.calculo == 'S'):
                            total_instrumento = total_instrumento*instrumento.peso/max_instrumento
                        elif(instrumento.calculo == 'P'):
                            total_instrumento = total_instrumento / max_instrumento
                    
                        if(self.estado == 'E'):
                            campo = 'resultado_empleado'
                        elif(self.estado == 'S'):
                            campo = 'resultado_supervisor'
                        elif(self.estado == 'H'):
                            campo = 'resultado_final'

                        setattr(resultado_instrumento, campo, total_instrumento)
                        resultado_instrumento.save()

                        if(instrumento.escalafon):
                            self.calcular_escalafon(resultado_instrumento)
        except:
            context = {} 
            context['instrumento'] = [{
                    'preguntas': [{
                        'form': self.form_class(request.POST, prefix=pregunta.pk, initial={
                            'pregunta': pregunta
                        }),
                        'pregunta': pregunta,
                    } for pregunta in seccion.preguntas.all()],
                    'seccion': seccion
                } for seccion in instrumento.secciones.all()
            ]
            context['error'] = 'Verifique la información ingresada, ya que hay errores en el formulario.'
            context['evaluacion'] = evaluacion
            context['pk'] = instrumento.pk

            return render(
                request, self.template_name,
                context
            )

        messages.success(request, self.success_message)

        if(self.estado == "E"):
            return redirect('dashboard')
        elif(self.estado == "S"):
            return redirect('revisar_evaluacion', pk=evaluacion.pk)
        elif(self.estado == "H"):
            return redirect('revisar_evaluacion_final', pk=evaluacion.pk)

class FormacionEmpleado(ValidarEvaluadoMixin, PeriodoContextMixin, EvaluacionEstadoMixin, View):
    template_name = "evaluacion/formacion_empleado.html"
    estado = "E"
    anadido_por = 'E'
    
    def get_success_url(self):
        return redirect('dashboard')

    def get_queryset(self, evaluacion):
        return evaluacion.formaciones.all()    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])
        qs = self.get_queryset(evaluacion)

        context['formset'] = modelformset_factory(
            Formacion, form=FormularioFormacion, exclude = ('evaluacion', 'anadido_por', 'activo'),
        )(queryset=qs) if not qs.exists() else modelformset_factory(
            Formacion, form=FormularioFormacion, exclude = ('evaluacion', 'anadido_por', 'activo'),
            extra = 0
        )(queryset = qs, initial=[{'competencias_tecnicas': [c.pk for c in form.competencias.filter(tipo='T')]} for form in evaluacion.formaciones.all()])

        context['titulo'] = "Detección de Necesidades de Formación"
        context['evaluacion'] = evaluacion
        context['anadido_por'] = self.anadido_por
        context['url_previo'] = ''

        return context
    
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)
        formset = modelformset_factory(
            Formacion, form=FormularioFormacion, exclude = ('evaluacion', 'anadido_por', 'activo', 'competencias'),
        )(request.POST)

        if formset.is_valid():
            with transaction.atomic():
                evaluacion.formaciones.filter(anadido_por=self.anadido_por).delete()
                for form in formset:
                    form.instance.evaluacion = evaluacion
                    form.instance.anadido_por = self.anadido_por
                    form.save()

                    competencias_tecnicas = form.cleaned_data.get('competencias_tecnicas')
                    competencias_genericas = form.cleaned_data.get('competencias_genericas')

                    for competencia in competencias_tecnicas:
                        form.instance.competencias.add(competencia)

                    for competencia in competencias_genericas:
                        form.instance.competencias.add(competencia)
        else:
            context = self.get_context_data()
            context['formset'] = formset
            return render(request, self.template_name, context)

        messages.success(request, 'Respuestas de Formación almacenadas correctamente.')
        return self.get_success_url()
    
class MetasEmpleado(ValidarEvaluadoMixin, PeriodoContextMixin, EvaluacionEstadoMixin, View):
    template_name = "evaluacion/metas_empleado.html"
    estado = "E"
    anadido_por = "E"
    anadido_previo = "E"

    def get_formsets(self, add_prefixes = False, qs_actual = None, qs_proximo = None):
        formset_actual = modelformset_factory(
            LogrosYMetas, form=FormularioMetas, exclude = ('anadido_por', 'activo', 'periodo', 'evaluacion'),
            min_num=0, extra = 0 if qs_actual else 1,
        )

        formset_proximo = modelformset_factory(
            LogrosYMetas, form=FormularioMetas, exclude = ('anadido_por', 'activo', 'periodo', 'evaluacion'),
            min_num=0, extra = 0 if qs_proximo else 1
        )

        if(add_prefixes):
            formset_actual = formset_actual(queryset=qs_actual, prefix="form-actual")
            formset_proximo = formset_proximo(queryset=qs_proximo, prefix="form-proximo")

        return formset_actual, formset_proximo

    def queryset_actual(self, evaluacion):
        qs = evaluacion.logros_y_metas.filter(anadido_por=self.anadido_por, periodo = "A")
        
        if(qs.exists()):
            return qs
        else:
            if(self.anadido_previo):
                qs = evaluacion.logros_y_metas.filter(periodo="A", anadido_por=self.anadido_previo)
                return qs if qs.exists() else evaluacion.logros_y_metas.filter(periodo="A")
            else:
                return evaluacion.logros_y_metas.filter(periodo="A")
    
    def queryset_proximo(self, evaluacion):
        qs = evaluacion.logros_y_metas.filter(anadido_por=self.anadido_por, periodo = "P")
        
        if(qs.exists()):
            return qs
        else:
            if(self.anadido_previo):
                qs = evaluacion.logros_y_metas.filter(periodo="P", anadido_por=self.anadido_previo)
                return qs if qs.exists() else evaluacion.logros_y_metas.filter(periodo="P")
            else:
                return evaluacion.logros_y_metas.filter(periodo="P")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])
        context['formset_actual'], context['formset_proximo'] = self.get_formsets(True, self.queryset_actual(evaluacion), self.queryset_proximo(evaluacion))
        context['titulo'] = "Formulario de Logros y Metas"
        context['anadido_por'] = self.anadido_por
        context['evaluacion'] = evaluacion
        context['url_previo'] = ''

        return context

    def get_success_url(self):
        return redirect('dashboard')

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

        messages.add_message(request, messages.SUCCESS, "Se han almacenado las respuestas de Logros y Metas.")        
        return self.get_success_url()
    
class ResultadosPorInstrumentoYVersion(LoginRequiredMixin, View):
    template_name = 'evaluacion/resultados_por_inst_y_version.html'
    def get(self, request, **args):
            evaluacion = Evaluacion.objects.get(pk=request.GET['pk'])
            instrumento = ResultadoInstrumento.objects.get(pk=request.GET['instrumento'])
            valor = request.GET['version']

            secciones = []
            try:
                for seccion in instrumento.resultados_secciones.all(): 
                    max_seccion = seccion.seccion.preguntas.aggregate(models.Sum('peso')).get('peso__sum')
                    max_relativo = 0 
                    valor_relativo = 0               
                    for pregunta in seccion.seccion.preguntas.all():
                        respuesta = pregunta.respuestas.get(evaluacion=evaluacion).respuesta_empleado if valor == 'E' else pregunta.respuestas.get(evaluacion=evaluacion).respuesta_supervisor if valor == 'S' else pregunta.respuestas.get(evaluacion=evaluacion).respuesta_definitiva
                        if(respuesta != None and respuesta >= 0):
                            max_relativo += pregunta.peso
                            valor_relativo += respuesta*pregunta.peso/2

                    resultado = seccion.resultado_empleado if valor == 'E' else seccion.resultado_supervisor if valor == 'S' else seccion.resultado_final
                    
                    secciones.append(
                        {
                            'nombre': seccion.seccion.titulo(),
                            'peso': seccion.seccion.peso,
                            'max_relativo': max_relativo,
                            'resultado': resultado,
                            'calculo': seccion.seccion.calculo,
                            'seccion': seccion.seccion,
                            'valor_relativo': valor_relativo,
                            'valor_ponderado': ((float(seccion.seccion.instrumento.peso) * float(max_seccion) / 100) * float(resultado / seccion.seccion.peso)  if seccion.seccion.calculo == 'S' else float(seccion.seccion.instrumento.peso) * float(resultado)) if resultado else '-',
                            'preguntas': []
                        } 
                    )               

                    for pregunta in seccion.seccion.preguntas.all():
                        secciones[-1]['preguntas'].append(
                            {
                                'pregunta': pregunta.pregunta,
                                'peso': pregunta.peso,
                                'respuesta_ponderada': pregunta.respuestas.get(evaluacion=evaluacion).respuesta_empleado / 2 * float(pregunta.peso) if pregunta.respuestas.filter(evaluacion=evaluacion).exists() else None,
                                'respuesta': next((opcion for opcion in pregunta.opciones.all() if opcion.valor == (pregunta.respuestas.get(evaluacion=evaluacion).respuesta_empleado if valor == 'E' else pregunta.respuestas.get(evaluacion=evaluacion).respuesta_supervisor if valor == 'S' else pregunta.respuestas.get(evaluacion=evaluacion).respuesta_definitiva)), None),
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
                        'version': valor,
                        'escalafon_obtenido': ResultadoEscalafon.objects.get(evaluacion=evaluacion, asignado_por = valor) if instrumento.instrumento.escalafon else None                 
                    }
                )
            except Exception as e:
                print(str(e))
                return HttpResponse("No se han cargado resultados en esta versión.")

class ConsultaFormacionesEvaluacion(LoginRequiredMixin, View):
    template_name = "evaluacion/partials/consulta_formacion.html"

    def get(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)
        formaciones = evaluacion.formaciones.filter(anadido_por=request.GET.get('version'))
        for formacion in formaciones:
            formacion.competencias_genericas = formacion.competencias.filter(tipo='G')
            formacion.competencias_tecnicas = formacion.competencias.filter(tipo='T')

        return render(request, self.template_name, {'formaciones': formaciones, 'evaluacion': evaluacion})
    
class ConsultaLogrosMetas(LoginRequiredMixin, View):
    template_name = "evaluacion/partials/consulta_logros_metas.html"

    def get(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)
        metas = evaluacion.logros_y_metas.filter(anadido_por=request.GET.get('version'), activo=True)

        metas_periodo_actual = metas.filter(periodo='A')
        metas_periodo_proximo = metas.filter(periodo='P')
        
        return render(request, self.template_name, {'metas_periodo_actual': metas_periodo_actual, 'metas_periodo_proximo': metas_periodo_proximo})

class ConsultaEvaluaciones(LoginRequiredMixin, ListView):
    template_name = "evaluacion/partials/lista_evaluaciones.html"
    model = Evaluacion
    filter_class = EvaluacionFilter
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter_class(self.request.GET, queryset=self.get_queryset())
        context['datos_personal'] = self.request.user.datos_personal.get(activo=True)
        context['url_previo'] = self.request.session.get('url_previo')
        context['extra_suffix'] = 'propias'
        return context

    def get_queryset(self):
        return super().get_queryset().filter(
            evaluado=self.request.user.datos_personal.get(activo=True)
        )

# VISTAS SUPERVISIÓN
class RevisionSupervisados(LoginRequiredMixin, PeriodoContextMixin, ListView):
    model = DatosPersonal
    template_name = "evaluacion/partials/revision_supervisados.html"
    filter_class = DatosPersonalFilter
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['datos_personal'] = self.request.user.datos_personal.get(activo=True)
        context['filter'] = self.filter_class()
        context['total'] = self.get_queryset().count()
        self.request.session['url_previo'] = 'evaluacion/supervisados/'

        return context

    def get_queryset(self):
        queryset = self.model.objects.filter(
            supervisor=self.request.user.datos_personal.get(activo=True),
            activo=True
        )

        queryset = self.filter_class(self.request.GET, queryset=queryset)
        return queryset.qs

class HistoricoEvaluacionesSupervisado(PeriodoContextMixin, ListView):
    template_name = "evaluacion/partials/lista_evaluaciones.html"
    model = Evaluacion
    filter_class = EvaluacionFilter
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        datos_personal = request.user.datos_personal.get(activo=True)
        evaluado = DatosPersonal.objects.get(pk=self.kwargs['pk'])
        
        if datos_personal != evaluado.supervisor and not request.user.is_superuser and not request.user.is_staff:
            return redirect('dashboard')
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter_class(self.request.GET, queryset=self.get_queryset())
        context['datos_personal'] = DatosPersonal.objects.get(pk=self.kwargs['pk'])
        context['supervisado'] = True
        context['url_previo'] = self.request.session.get('url_previo')
        context['extra_suffix'] = f'{context["datos_personal"].pk}extra'
        return context
    
    def get(self, request, *args, **kwargs):
        """
        Verificar si el usuario puede ver esta evaluación
        """
        datos_personal = request.user.datos_personal.get(activo=True)
        evaluado = DatosPersonal.objects.get(pk=self.kwargs['pk'])

        if (datos_personal.supervisados.filter(pk=evaluado.pk).exists()
                or request.user.is_superuser
                or (request.user.is_staff)):
            return super().get(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    def get_queryset(self):
        return super().get_queryset().filter(evaluado__pk=self.kwargs['pk'])

class FormularioInstrumentoSupervisor(ValidarSupervisorMixin, FormularioInstrumentoEmpleado):
    estado = "S"
    template_name = "evaluacion/partials/formulario_supervisor.html"
    form_class = FormularioRespuestasSupervisor

    def define_initial_data(self, pregunta, respuesta):
        return {
            'pregunta': pregunta,
            'respuesta_supervisor': respuesta.respuesta_empleado if respuesta.respuesta_supervisor == None else respuesta.respuesta_supervisor,
            'comentario_supervisor': respuesta.comentario_supervisor
        }

    def get_context_data(self, post=False, **kwargs):
        context = {}
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
                initial_data = self.define_initial_data(pregunta, respuesta)
                form = self.form_class(
                    instance=respuesta, 
                    prefix=pregunta.pk, 
                    initial=initial_data
                ) if not post else self.form_class(
                    self.request.POST, 
                    prefix=pregunta.pk
                )
                
                preguntas_data.append({'form': form, 'pregunta': pregunta})
            
            context['instrumento'].append({'preguntas': preguntas_data, 'seccion': seccion})

        context['titulo'] = instrumento.nombre.title()
        context['pk'] = instrumento.pk
        context['evaluacion'] = evaluacion

        return context
    
class RevisionEvaluacion(ValidarSupervisorMixin, PeriodoContextMixin, EvaluacionEstadoMixin, View):
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
    
class FormacionSupervisor(ValidarSupervisorMixin, FormacionEmpleado):
    template_name = "evaluacion/formacion_empleado.html"
    estado = "S"
    anadido_por = "S"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_previo'] = f'/evaluacion/supervisados/revisar/{context["evaluacion"].pk}/'

        return context        

    def get_success_url(self):
        return redirect('revisar_evaluacion', pk=self.kwargs['pk'])

    def get_queryset(self, evaluacion):
        qs = evaluacion.formaciones.filter(anadido_por = "S", activo = True)
        
        if(qs.exists()):
            return qs
        else:
            return evaluacion.formaciones.filter(activo = True)

class LogrosYMetasSupervisor(ValidarSupervisorMixin, MetasEmpleado):
    estado = "S"
    anadido_por = "S"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_previo'] = f"evaluacion/supervisados/revisar/{context['evaluacion'].pk}/"
        return context 

    def get_success_url(self):
        return redirect('revisar_evaluacion', pk=self.kwargs['pk'])

class EnviarEvaluacionGerente(ValidarSupervisorMixin, View):
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)

        with transaction.atomic():
            if(evaluacion.estado == 'S' and (
                evaluacion.resultados.filter(resultado_supervisor__isnull=False).count() == evaluacion.formulario.instrumentos.count() and
                evaluacion.formaciones.filter(anadido_por = "S").count() and evaluacion.logros_y_metas.filter(anadido_por = "S").count()
            )):
                if evaluacion.evaluado.supervisor and not evaluacion.evaluado.user.is_superuser:
                    evaluacion.estado = 'G'
                elif evaluacion.evaluado.supervisor and evaluacion.evaluado.supervisor.user.is_superuser:
                    evaluacion.estado = 'H'
                elif evaluacion.evaluado.user.is_superuser:
                    evaluacion.estado = 'A'
                    evaluacion.fecha_entrega = datetime.datetime.now()
                    evaluacion.fecha_fin = datetime.datetime.now()

                    #copiamos los resultados del supervisor como definitivos
                    for resultado in evaluacion.resultados.all():
                        resultado.resultado_final = resultado.resultado_supervisor
                        resultado.save()
                        for seccion in resultado.resultados_secciones.all():
                            seccion.resultado_final = seccion.resultado_supervisor
                            seccion.save()

                    for respuesta in evaluacion.respuestas.all():
                        respuesta.respuesta_definitiva = respuesta.respuesta_supervisor
                        respuesta.save()

                    for formacion in evaluacion.formaciones.filter(anadido_por = 'S'):
                        competencias = formacion.competencias.all()
                        formacion.pk = None
                        formacion.anadido_por = 'H'
                        formacion.save()

                        for competencia in competencias:
                            formacion.competencias.add(competencia)

                    for logro in evaluacion.logros_y_metas.filter(anadido_por = 'S'):
                        logro.pk = None
                        logro.anadido_por = 'H'
                        logro.save()

                #copiamos el resultado escalafon del supervisor como definitivo
                resultado_escalafon = evaluacion.escalafones.get(asignado_por='S')
                nuevo_resultado_escalafon = resultado_escalafon
                nuevo_resultado_escalafon.pk = None
                nuevo_resultado_escalafon.asignado_por = 'H'
                nuevo_resultado_escalafon.save()

                evaluacion.fecha_revision = datetime.datetime.now()
                evaluacion.comentario_supervisor = request.POST.get('comentarios')
                evaluacion.save()

                if evaluacion.estado == 'G':
                    messages.success(request, f"Ha sido enviada la evaluación de {evaluacion.evaluado.user.get_full_name().upper()} a la Gerencia correspondiente.")
                    body = 'La evaluación de desempeño de ' + evaluacion.evaluado.user.get_full_name().upper() + ' ha sido enviada a usted para su revisión antes de ser enviada a la Gerencia de Gestión Humana; podrá encontrarla en la pestaña "GERENCIA" del sistema, y podrá enviarse mediante el botón "Enviar a Gestión Humana" de la misma pantalla.\n\n'
                    to = [evaluacion.evaluado.user.email, PeriodoGerencial.objects.get(activo=True, gerencia=evaluacion.evaluado.gerencia).gerente.user.email]
                elif evaluacion.estado == 'A': # Caso Gestión Humana
                    messages.success(request, f"Ha sido aprobada la evaluación de {evaluacion.evaluado.user.get_full_name().upper()} por la Gerencia General.")
                    body = 'La evaluación de desempeño de ' + evaluacion.evaluado.user.get_full_name().upper() + ' ha sido aprobada por la Gerencia General; siendo cerrada para el periodo activo.\n\n'
                    to = [evaluacion.evaluado.user.email, evaluacion.evaluado.gerencia.gerencias.get(activo=True).gerente.user.email]

            send_mail_async(
                'Actualización de Estatus - Evaluación de Desempeño de ' + evaluacion.evaluado.user.get_full_name().upper(),
                body,
                to,
            )
            
            return redirect('consultar_supervisados')
        
        return HttpResponseForbidden("Una vez empezada la evaluación no puede modificar su estado.")

# VISTAS DE GERENCIA
class RevisionGerencia(ValidarMixin, PeriodoContextMixin, ListView):
    model = DatosPersonal
    template_name = "evaluacion/partials/revision_supervisados.html"
    filter_class = DatosPersonalFilter
    paginate_by = 5

    def validar(self):
        return self.request.user.datos_personal.filter(activo=True, user__is_staff=True).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter_class(prefix='gerencia')
        context['datos_personal'] = self.request.user.datos_personal.get(activo=True)
        self.request.session['url_previo'] = f'evaluacion/gerencia/'
        context['puede_enviarse_gghh'] = self.request.user.is_staff and (Evaluacion.objects.filter(periodo=self.get_periodo(), estado='G', evaluado__gerencia__in=self.request.user.datos_personal.get(activo=True).personal_gerente.filter(activo=True).values_list('gerencia', flat=True)).count())
        context['gerencia'] = self.request.user.datos_personal.get(activo=True).gerencia
        context['total'] = self.get_queryset().count()
        return context

    def get_queryset(self):
        qs = super().get_queryset().filter(
            gerencia__in=self.request.user.datos_personal.get(activo=True).personal_gerente.filter(activo=True).values_list('gerencia', flat=True),
            activo=True
        )
        self.filter = self.filter_class(self.request.GET, queryset=qs, prefix='gerencia')
        return self.filter.qs

class EnviarEvaluacionesGestionHumana(GerenteMixin, View):
    def post(self, request):
        periodo_actual = Periodo.objects.get(activo=True)
        evaluaciones = Evaluacion.objects.filter(periodo=periodo_actual, estado='G', evaluado__gerencia__in=request.user.datos_personal.get(activo=True).personal_gerente.filter(activo=True).values_list('gerencia', flat=True))
        nombres = list(evaluaciones.values_list('evaluado__user__first_name', flat=True))

        if evaluaciones.count():
            evaluaciones.update(estado='H', fecha_entrega=datetime.datetime.now())
            messages.success(request, f"Ha sido enviada la evaluación de los empleados con el estatus 'Enviado a la Gerencia' a la Gerencia de Gestión Humana.")
            body = 'Las evaluaciones de desempeño de los empleados han sido enviadas a la Gerencia de Gestión Humana.\n\n'
            body += "Los empleados enviados son: \n\n"

            for nombre in nombres:
                body += f"- {nombre.upper()}\n"

            body += "\nPodrá revisarlas en el Panel de Control del Gerente de Gestión Humana, en la sección de revisión de evaluaciones.\n\n"

            print(body)
            
            send_mail_async(
                f"Envío de Evaluaciones a la Gerencia de Gestión Humana",
                body,
                [DatosPersonal.objects.get(user__is_superuser=True).user.email],
            )
            
            return redirect('consultar_gerencia')
        
class DevolverEvaluacionSupervisor(GerenteMixin, View):
    def post(self, request, pk):
        if(request.user.is_staff):
            evaluacion = Evaluacion.objects.get(pk=pk, estado='G')
            evaluacion.estado = 'S'
            evaluacion.fecha_revision = None
            evaluacion.save()
            messages.success(request, "La evaluación ha sido devuelta al estado 'Revisión por Supervisor'. Por favor comunique al supervisor las rrazones para la devolución.")
            return redirect('consultar_gerencia')
        else:
            return HttpResponseForbidden("No se puede devolver la evaluación al estado 'S'.")

# VISTAS DE GESTIÓN HUMANA / SUPERUSUARIO
class ConsultaGeneralEvaluaciones(ValidarSuperusuario, RevisionGerencia):
    model = DatosPersonal
    template_name = "evaluacion/partials/revision_supervisados.html"
    filter_class = DatosPersonalFilter
    paginate_by = 5

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['general'] = True
        return context

    def get_queryset(self):
        return self.filter_class(self.request.GET, queryset=DatosPersonal.objects.filter(activo=True)).qs

class RevisionTodoPersonal(ValidarSuperusuario, PeriodoContextMixin, ListView):
    model = DatosPersonal
    template_name = "evaluacion/partials/revision_gghh.html"
    filter_class = DatosPersonalFilter
    paginate_by = 5

    def get(self, request, *args, **kwargs):
        if(request.user.is_superuser): # Gerente de Gestión Humana
            if request.GET:
                request.session['previous_req'] = request.GET
            return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter_class(self.request.session.get('previous_req'))
        context['total'] = self.get_queryset().count()
        context['datos_personal'] = self.request.user.datos_personal.get(activo=True)
        self.request.session['url_previo'] = f'evaluacion/revision-general/'
        return context

    def get_queryset(self):
        qs = self.model.objects.filter(
            activo=True
        )
        return self.filter_class(self.request.session.get('previous_req'), qs).qs

class RevisionEvaluacionFinal(ValidarSuperusuario, PeriodoContextMixin, EvaluacionEstadoMixin, View):
    estado = "H"
    template_name = 'evaluacion/partials/revision_evaluacion_final.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])

        context['evaluacion'] = evaluacion

        context['puede_finalizar'] = evaluacion.resultados.filter(resultado_final__isnull=False).count() == evaluacion.formulario.instrumentos.count() and (
            evaluacion.formaciones.filter(anadido_por="H").exists() 
            and 
            evaluacion.logros_y_metas.filter(anadido_por="H").exists() 
        ) if evaluacion else False

        context['instrumentos'] = [
            {
                'nombre': instrumento.nombre,
                'completado': instrumento.resultados.filter(evaluacion = evaluacion, resultado_final__isnull=False).exists(),
                'resultado_empleado': instrumento.resultados.filter(evaluacion = evaluacion).first().resultado_empleado if instrumento.resultados.filter(evaluacion = evaluacion).exists() else None,
                'resultado_supervisor': instrumento.resultados.filter(evaluacion = evaluacion).first().resultado_supervisor if instrumento.resultados.filter(evaluacion = evaluacion).exists() else None,
                'resultado_final': instrumento.resultados.filter(evaluacion = evaluacion).first().resultado_final if instrumento.resultados.filter(evaluacion = evaluacion).exists() else None,
                'peso': instrumento.peso,
                'pk': instrumento.pk
            } for instrumento in evaluacion.formulario.instrumentos.all()
        ] if evaluacion else None

        context['formaciones'] = evaluacion.formaciones.filter(anadido_por="H")
        context['logros_y_metas'] = evaluacion.logros_y_metas.filter(anadido_por="H")

        return context

class FormularioEvaluacionDefinitiva(ValidarSuperusuario, FormularioInstrumentoSupervisor):
    estado = "H"
    template_name = "evaluacion/partials/formulario_definitiva.html"
    form_class = FormularioRespuestasFinales

    def define_initial_data(self, pregunta, respuesta):
        return {
            'pregunta': pregunta,
            'respuesta_definitiva': respuesta.respuesta_empleado if respuesta.respuesta_supervisor == None else respuesta.respuesta_supervisor if respuesta.respuesta_definitiva == None else respuesta.respuesta_definitiva,
            'comentario_gghh': respuesta.comentario_gghh
        }
    
class FormularioMetasDefinitivos(ValidarSuperusuario, MetasEmpleado):
    anadido_por = "H"
    estado = "H"
    anadido_previo = "S"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["definitiva"] = True
        context['url_previo'] = f"evaluacion/evaluar-final/revisar/{context['evaluacion'].pk}/"
        return context 

    def get_success_url(self):
        return redirect('revisar_evaluacion_final', pk=self.kwargs['pk'])

class FormacionDefinitiva(ValidarSuperusuario, FormacionEmpleado):
    template_name = "evaluacion/formacion_empleado.html"
    estado = "H"
    anadido_por = "H"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["definitiva"] = True
        context['url_previo'] = f"evaluacion/evaluar-final/revisar/{context['evaluacion'].pk}/"
        return context

    def get_success_url(self):
        return redirect('revisar_evaluacion_final', pk=self.kwargs['pk'])

    def get_queryset(self, evaluacion):
        qs = evaluacion.formaciones.filter(anadido_por = "H", activo = True)
        
        if(qs.exists()):
            return qs
        else:
            qs = evaluacion.formaciones.filter(anadido_por = "S")
            if qs.exists():
                return qs
            else:
                return evaluacion.formaciones.filter(anadido_por = "E")

class CerrarEvaluacion(ValidarSuperusuario, View):
    def post(self, request, pk, *args, **kwargs):
        evaluacion = Evaluacion.objects.get(pk=pk)

        with transaction.atomic():        
            evaluacion.estado = request.POST.get('tipo_evaluacion')
            evaluacion.comentario_gghh = request.POST.get('comentarios')

            if not evaluacion.fecha_revision:
                evaluacion.fecha_revision = datetime.datetime.now()

            evaluacion.fecha_fin = datetime.datetime.now()
            evaluacion.save()

            if(evaluacion.estado == 'R'):
                evaluacion_previa = Evaluacion.objects.get(pk=pk)
                resultados_instrumentos = evaluacion_previa.resultados.all()
                resultados_escalafon = evaluacion.escalafones.get(asignado_por='E')

                evaluacion.pk = None
                evaluacion.estado = 'S'
                evaluacion.fecha_fin = None
                evaluacion.fecha_revision = None
                evaluacion.fecha_entrega = None
                evaluacion.fecha_inicio = datetime.datetime.now()
                evaluacion.fecha_envio = datetime.datetime.now()
                evaluacion.save()
                
                resultados_escalafon.evaluacion = evaluacion
                resultados_escalafon.pk = None
                resultados_escalafon.save()

                for resultado_previo in resultados_instrumentos:
                    nuevo_resultado_instrumento = resultado_previo
                    resultado_previo = ResultadoInstrumento.objects.get(pk=resultado_previo.pk)
                    nuevo_resultado_instrumento.evaluacion = evaluacion
                    nuevo_resultado_instrumento.resultado_final = None
                    nuevo_resultado_instrumento.resultado_supervisor = None
                    nuevo_resultado_instrumento.pk = None
                    nuevo_resultado_instrumento.save()

                    for resultado_seccion_previo in resultado_previo.resultados_secciones.all():
                        nuevo_resultado_seccion = resultado_seccion_previo
                        resultado_seccion_previo = ResultadoSeccion.objects.get(pk=resultado_seccion_previo.pk)
                        nuevo_resultado_seccion.pk = None
                        nuevo_resultado_seccion.resultado_final = None
                        nuevo_resultado_seccion.resultado_instrumento = nuevo_resultado_instrumento
                        nuevo_resultado_seccion.resultado_supervisor = None
                        nuevo_resultado_seccion.resultado_final = None
                        nuevo_resultado_seccion.save()
                        
                        for respuesta_previo in resultado_seccion_previo.seccion.preguntas.all():
                            nueva_respuesta_previo = respuesta_previo.respuestas.get(evaluacion=evaluacion_previa)
                            nueva_respuesta = nueva_respuesta_previo
                            nueva_respuesta.pk = None
                            nueva_respuesta.respuesta_definitiva = None
                            nueva_respuesta.respuesta_supervisor = None
                            nueva_respuesta.evaluacion = evaluacion
                            nueva_respuesta.save()

                formaciones_empleado = evaluacion_previa.formaciones.filter(anadido_por='E')
                for formacion_empleado in formaciones_empleado:
                    nueva_formacion = formacion_empleado
                    formacion_empleado = Formacion.objects.get(pk=formacion_empleado.pk)
                    nueva_formacion.evaluacion = evaluacion
                    nueva_formacion.pk = None
                    nueva_formacion.save()

                    for competencia in formacion_empleado.competencias.all():
                        nueva_formacion.competencias.add(competencia)                     

                logros_empleado = evaluacion_previa.logros_y_metas.filter(anadido_por='E')
                for logro_empleado in logros_empleado:
                    nuevo_logro = logro_empleado
                    nuevo_logro.evaluacion = evaluacion
                    nuevo_logro.pk = None
                    nuevo_logro.save()

                send_mail_async(
                    'Rechazada - Evaluación de desempeño de ' + evaluacion.evaluado.user.get_full_name().upper(),
                    "La gerencia de gestión humana encontró irregularidades en la última evaluación enviada por lo cual se ha rechazado y ha sido remitida al supervisor. Para más detalles, reunirse con el gerente de gestión humana.\n\n",
                    [evaluacion.evaluado.user.email, evaluacion.evaluado.supervisor.user.email if evaluacion.evaluado.supervisor else None, PeriodoGerencial.objects.get(gerencia=evaluacion.evaluado.gerencia, activo=True).gerente.user.email],
                )
            else:
                send_mail_async(
                    'Aprobada - Evaluación de desempeño de ' + evaluacion.evaluado.user.get_full_name().upper(),
                    "La gerencia de gestión humana ha revisado la evaluación y ha sido aprobada; cerrando definitivamente el proceso de evaluación para usted en el periodo evaluado.\n\n",
                    [evaluacion.evaluado.user.email, evaluacion.evaluado.supervisor.user.email if evaluacion.evaluado.supervisor else None, PeriodoGerencial.objects.get(gerencia=evaluacion.evaluado.gerencia, activo=True).gerente.user.email],
                )

        messages.success(request, 'Evaluación cerrada correctamente.')
        return redirect('revision_general')

# PROMOCIONES
class FormularioPostulacionPromocion(ValidarMixin, View):    
    def validar(self):
        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])
        return not evaluacion.solicitudes_promocion.count() and evaluacion.evaluado.supervisor.user.pk == self.request.user.pk

    def get(self, request, pk, *args, **kwargs):
        evaluacion = Evaluacion.objects.get(pk=pk)
        if evaluacion.fecha_fin and (datetime.datetime.now() - evaluacion.fecha_fin).days > 30:
            messages.error(request, 'No se pueden realizar promociones para evaluaciones aprobadas hace más de 30 días.')
            return redirect('revision_general')
        else:
            return render(request, 'evaluacion/formulario_promocion.html', context=self.get_context_data())
        
    def get_context_data(self):
        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])
        niveles = NivelEscalafon.objects.filter(
            pk__gt = evaluacion.evaluado.escalafon.pk, 
            escalafon__tipo_personal=evaluacion.evaluado.tipo_personal
        ).exclude(
            ~Exists(FormularioPromocion.objects.filter(nivel=OuterRef('pk')))
        )
        nivel_competencias = evaluacion.escalafones.get(asignado_por='H').escalafon
        nivel_previo = evaluacion.evaluado.escalafon
        nivel_deseado = NivelEscalafon.objects.get(
            pk = self.request.GET.get('nivel')
        ) if self.request.GET.get('nivel') else nivel_competencias if nivel_competencias.pk > nivel_previo.pk else niveles[0]

        formularios = {}
        detalles = DetalleAspectoPromocion.objects.filter(
            formulario_promocion__nivel=nivel_deseado
        )
        for detalle in detalles:
            respuesta_eval = Respuesta.objects.get(evaluacion=evaluacion, pregunta=detalle.pregunta_asociada).respuesta_definitiva if Respuesta.objects.filter(evaluacion=evaluacion, pregunta=detalle.pregunta_asociada).exists() else None
            respuesta_eval = detalle.pregunta_asociada.opciones.get(valor=respuesta_eval) if respuesta_eval else None
            formularios[detalle] = {
                'formulario': RespuestaSolicitudPromocionSupervisorForm(initial={
                    'detalle_aspecto': detalle,
                    'cumple': evaluacion.evaluado.antiguedad() >= detalle.valor_asociado if detalle.aspecto.antiguedad else respuesta_eval.valor >= detalle.opcion_asociada.valor if detalle.opcion_asociada and respuesta_eval else None
                }, prefix=detalle.pk),
                'respuesta_eval': respuesta_eval
            }

        context = {
            'evaluacion': evaluacion,
            'niveles': niveles,
            'nivel_competencias': nivel_competencias,
            'nivel_previo': nivel_previo,
            'nivel_deseado': nivel_deseado,
            'formularios': formularios
        }

        return context

    def post(self, request, pk, *args, **kwargs):
        try:
            with transaction.atomic():
                nivel = request.POST.get('nivel')
                forms_promocion = [RespuestaSolicitudPromocionSupervisorForm(request.POST, prefix=detalle.pk) for detalle in DetalleAspectoPromocion.objects.filter(formulario_promocion__nivel=nivel)]
                evaluacion = Evaluacion.objects.get(pk=pk)

                solicitud_promocion = SolicitudPromocion.objects.create(
                    evaluacion = evaluacion,
                    fecha_envio = datetime.datetime.now(),
                    formulario_promocion = FormularioPromocion.objects.get(nivel__pk=nivel)
                )
                
                if all(form.is_valid() for form in forms_promocion):
                    for form in forms_promocion:
                        respuesta = form.save(commit=False)
                        respuesta.solicitud_promocion = solicitud_promocion
                        respuesta.save()

                    messages.success(request, 'Solicitud de promoción enviada correctamente a Gestión humana.')
                    
                    send_mail_async(
                        f'Solicitud de promoción para {evaluacion.evaluado.user.get_full_name().upper()}',
                        f"Se solicita considerar la promoción para el empleado {evaluacion.evaluado.user.get_full_name().upper()}; el formulario correspondiente ha sido enviado con sus justificaciones y consideraciones correspondientes.",
                        [
                            DatosPersonal.objects.get(user__is_superuser=True).user.email,
                            evaluacion.evaluado.supervisor.user.email if evaluacion.evaluado.supervisor else None,
                            PeriodoGerencial.objects.get(activo=True, gerencia=evaluacion.evaluado.gerencia).gerente.user.email
                        ],
                        sender=request.user.email if request.user.email else 'no-replay@indesca.com'
                    )

                    return redirect('consultar_supervisados')
                else:
                    raise Exception("Error en el formulario")
        except Exception as e:
            print(str(e))
            print(forms_promocion)
            for form in forms_promocion:
                if form.is_valid() and not form.cleaned_data.get('justificacion'):
                    form.add_error('justificacion', 'La justificación es obligatoria.')

            context = self.get_context_data()
            context.update({'formularios': {detalle: {'formulario': form} for detalle, form in zip(DetalleAspectoPromocion.objects.filter(formulario_promocion__nivel=nivel), forms_promocion)}})
            return render(request, 'evaluacion/formulario_promocion.html', context)

class ConsultaPromociones(SuperuserMixin, ListView):
    model = SolicitudPromocion
    template_name = "evaluacion/partials/lista_promociones.html"
    filter_class = SolicitudPromocionFilter

    def get_context_data(self, **kwargs):
        context = {}
        if 'promocion' in self.request.GET:
            context['filter'] = self.filter_class(self.request.GET, queryset=self.get_queryset())
        else:
            active_periodo = Periodo.objects.filter(activo=True).first()
            context['filter'] = self.filter_class(self.request.GET.copy(), queryset=self.get_queryset())
            if active_periodo:
                context['filter'].form.fields['evaluacion__periodo'].initial = active_periodo.pk

        context['object_list'] = context['filter'].qs

        return context

    def get_queryset(self):
        return self.model.objects.all().select_related(
            'evaluacion', 'evaluacion__evaluado',
            'evaluacion__evaluado__escalafon',
        ).prefetch_related(
            Prefetch(
                'respuestas_solicitud_promocion',
                RespuestaSolicitudPromocion.objects.select_related(
                    'detalle_aspecto', 'detalle_aspecto__pregunta_asociada',
                    'detalle_aspecto__opcion_asociada'
                )
            )
        )

class FormularioRevisionPostulacionPromocion(FormularioPostulacionPromocion):    
    def validar(self):
        return self.request.user.is_superuser

    def get(self, request, pk, *args, **kwargs):
        return render(request, 'evaluacion/formulario_promocion.html', context=self.get_context_data())
        
    def get_context_data(self):
        solicitud = SolicitudPromocion.objects.select_related(
            'evaluacion', 'evaluacion__evaluado', 'evaluacion__evaluado__user'
        ).get(pk=self.kwargs['pk'])
        evaluacion = solicitud.evaluacion

        niveles = [solicitud.formulario_promocion.nivel]
        nivel_competencias = evaluacion.escalafones.get(asignado_por='H').escalafon
        nivel_previo = evaluacion.evaluado.escalafon
        nivel_deseado = solicitud.formulario_promocion.nivel

        formularios = {}
        detalles = DetalleAspectoPromocion.objects.filter(
            formulario_promocion__nivel=nivel_deseado
        ).select_related(
            'aspecto',
            'pregunta_asociada',
            'opcion_asociada'
        ).prefetch_related(
            Prefetch(
                'respuestas_solicitud_promocion',
                RespuestaSolicitudPromocion.objects.select_related(
                    'detalle_aspecto', 'detalle_aspecto__pregunta_asociada',
                )
            ),
            Prefetch(
                'pregunta_asociada__respuestas'
            )
        )
        for detalle in detalles:
            respuesta_eval = detalle.pregunta_asociada.respuestas.get(evaluacion=evaluacion).respuesta_definitiva if detalle.pregunta_asociada and detalle.pregunta_asociada.respuestas.filter(evaluacion=evaluacion, pregunta=detalle.pregunta_asociada).exists() else None
            respuesta_eval = detalle.pregunta_asociada.opciones.get(valor=respuesta_eval) if respuesta_eval else None
            res_previa = detalle.respuestas_solicitud_promocion.get(
                solicitud_promocion = solicitud
            )
            formularios[detalle] = {
                'formulario': RespuestaSolicitudPromocionSupervisorForm(initial={
                    'detalle_aspecto': detalle,
                    'cumple': res_previa.cumple
                }, prefix=detalle.pk),
                'respuesta_eval': respuesta_eval,
                'res_previa': res_previa
            }

        context = {
            'evaluacion': evaluacion,
            'niveles': niveles,
            'nivel_competencias': nivel_competencias,
            'nivel_previo': nivel_previo,
            'nivel_deseado': nivel_deseado,
            'formularios': formularios,
            'gerencia': True
        }

        print("SALIO")
        return context

    def post(self, request, pk, *args, **kwargs):
        try:
            with transaction.atomic():
                nivel = request.POST.get('nivel')
                forms_promocion = [RespuestaSolicitudPromocionSupervisorForm(request.POST, prefix=detalle.pk) for detalle in DetalleAspectoPromocion.objects.filter(formulario_promocion__nivel=nivel)]
                evaluacion = Evaluacion.objects.get(pk=pk)

                solicitud_promocion = SolicitudPromocion.objects.get(
                    evaluacion = evaluacion
                )
                solicitud_promocion.fecha_aprobacion = datetime.datetime.now()
                solicitud_promocion.comentario_general_gghh = request.POST.get('comentario_general_gghh')
                
                if all(form.is_valid() for form in forms_promocion):
                    for form in forms_promocion:
                        respuesta = form.save(commit=False)
                        respuesta.solicitud_promocion = solicitud_promocion
                        respuesta.enviada_por = 'H'
                        respuesta.save()

                    if request.POST.get('submit') == 'Conceder':
                        messages.success(request, f'Promoción concedida a {evaluacion.evaluado.user.get_full_name().upper()}.')
                        solicitud_promocion.aprobado = True
                        solicitud_promocion.save()

                        contenido = f"""Saludos,

                        Le escribimos para informarle que su solicitud de promoción del empleado {evaluacion.evaluado.user.get_full_name().upper()} al nivel {solicitud_promocion.formulario_promocion.nivel} ha sido CONCEDIDA.

                        Se le invita a verificar el estado de la solicitud junto a los comentarios correspondientes en el sistema de evaluación de desempeño.

                        Agradecemos su comprensión y nos ponemos a su disposición para cualquier inquietud que tenga.

                        Atentamente,
                        La Gerencia de Gestión Humana
                        """
                    elif request.POST.get('submit') == 'Denegar':
                        messages.success(request, 'Solicitud de promoción rechazada.')
                        solicitud_promocion.aprobado = False
                        solicitud_promocion.save()

                        contenido = f"""Saludos,

                        Le escribimos para informarle que su solicitud de promoción del empleado {evaluacion.evaluado.user.get_full_name().upper()} al nivel {solicitud_promocion.formulario_promocion.nivel} ha sido DENEGADA.

                        Se le invita a verificar el estado de la solicitud junto a los comentarios correspondientes en el sistema de evaluación de desempeño.

                        Agradecemos su comprensión y nos ponemos a su disposición para cualquier inquietud que tenga.

                        Atentamente,
                        La Gerencia de Gestión Humana
                        """

                    send_mail_async(
                        f'Decisión sobre la Solicitud de Promoción para {evaluacion.evaluado.user.get_full_name().upper()}',
                        contenido,
                        [
                            evaluacion.evaluado.supervisor.user.email if evaluacion.evaluado.supervisor else None,
                            PeriodoGerencial.objects.get(activo=True, gerencia=evaluacion.evaluado.gerencia).gerente.user.email
                        ],
                        sender=request.user.email
                    )

                    return redirect('consulta_promociones')
                else:
                    raise Exception("Error en el formulario")
        except Exception as e:
            print(str(e))
            print(forms_promocion)
            for form in forms_promocion:
                if form.is_valid() and not form.cleaned_data.get('justificacion'):
                    form.add_error('justificacion', 'La justificación es obligatoria.')

            context = self.get_context_data()
            context.update({'formularios': {detalle: {'formulario': form} for detalle, form in zip(DetalleAspectoPromocion.objects.filter(formulario_promocion__nivel=nivel), forms_promocion)}})
            return render(request, 'evaluacion/formulario_promocion.html', context)

# OTROS
class GenerarModal(LoginRequiredMixin, View):
    def get_context_data(self, **kwargs):
        tipo = self.request.GET['version']
        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])

        context = {
            'tipo': tipo,
            'evaluacion': evaluacion,
            'id': self.kwargs['pk'],
            'include_others': True
        }

        return context

    def get(self, request, pk, *args, **kwargs):
        return render(
            request=request, 
            template_name='evaluacion/partials/modal-evaluacion-empleado.html',
            context=self.get_context_data()
        )
    
class GenerarModalPromocion(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return render(
            request=request, 
            template_name='evaluacion/partials/modal-promocion.html',
            context=self.get_context_data()
        )
    
    def get_context_data(self, **kwargs):
        evaluacion = Evaluacion.objects.get(pk=self.kwargs['pk'])
        return {
            'evaluacion': evaluacion,
            'id': self.kwargs['pk'],
            'solicitud': SolicitudPromocion.objects.get(evaluacion=evaluacion)
        }
