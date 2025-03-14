from django.urls import path
from .views import *

urlpatterns = [
    path('comenzar/<int:pk>/', ComenzarEvaluacion.as_view(), name="comenzar_evaluacion"),
    path('instrumento/<int:pk>/', FormularioInstrumentoEmpleado.as_view(), name="instrumento"),
    path('instrumento/<int:pk>/<int:evaluacion>/', FormularioInstrumentoSupervisor.as_view(), name="revision_instrumento"),
    path('formacion/<int:pk>/', FormacionEmpleado.as_view(), name="formacion"),
    path('metas/<int:pk>/', MetasEmpleado.as_view(), name="metas"),

    path('finalizar/<int:pk>/', FinalizarEvaluacion.as_view(), name="finalizar_evaluacion"),
    path('seccion/', ResultadosPorInstrumentoYVersion.as_view(), name="ver_instrumento"),
    path('formacion/consulta/<int:pk>/', ConsultaFormacionesEvaluacion.as_view(), name="consulta_formacion"),
    path('metas/consulta/<int:pk>/', ConsultaLogrosMetas.as_view(), name="consulta_metas"),

    path('consulta/<int:pk>/', ConsultaEvaluaciones.as_view(), name="consultar_evaluaciones"),
    path('supervisados/', RevisionSupervisados.as_view(), name="consultar_supervisados"),
    path('supervisados/historico/<int:pk>/', HistoricoEvaluacionesSupervisado.as_view(), name="consultar_historico_supervisados"),
    path('supervisados/revisar/<int:pk>/', RevisionEvaluacion.as_view(), name="revisar_evaluacion"),
    path('supervisados/formacion/<int:pk>/', FormacionSupervisor.as_view(), name="formacion_supervisado"),
    path('supervisados/metas/<int:pk>/', LogrosYMetasSupervisor.as_view(), name="metas_supervisado"),
    path('supervisados/enviar/<int:pk>/', EnviarEvaluacionGerente.as_view(), name="enviar_gerente"),

    path('gerencia/', RevisionGerencia.as_view(), name="consultar_gerencia"),
    path('gerencia/revisar/', EnviarEvaluacionesGestionHumana.as_view(), name="enviar_gghh"),
    path('gerencia/devolver-evaluacion/<int:pk>/', DevolverEvaluacionSupervisor.as_view(), name="devolver_evaluacion_supervisor"),

    path('consulta-general/', ConsultaGeneralEvaluaciones.as_view(), name="consulta_general"),
    path('revision-general/', RevisionTodoPersonal.as_view(), name="revision_general"),
    path('evaluar-final/revisar/<int:pk>/', RevisionEvaluacionFinal.as_view(), name="revisar_evaluacion_final"),
    path('evaluar-final/revision/<int:pk>/<int:evaluacion>/', FormularioEvaluacionDefinitiva.as_view(), name="formulario_evaluacion_definitiva"),
    path('evaluar-final/metas/<int:pk>/', FormularioMetasDefinitivos.as_view(), name="metas_definitivas"),
    path('evaluar-final/formacion/<int:pk>/', FormacionDefinitiva.as_view(), name="formacion_definitiva"),
    path('evaluar-final/cerrar/<int:pk>/', CerrarEvaluacion.as_view(), name="cerrar_evaluacion_final"),

    # Promoción
    path('promocion/', FormularioPromocion.as_view(), name="revision_promocion"),

    path("modal/<int:pk>/", GenerarModal.as_view(), name="generar_modal")
]
