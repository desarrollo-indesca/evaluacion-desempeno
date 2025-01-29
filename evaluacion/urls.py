from django.urls import path
from .views import *

urlpatterns = [
    path('comenzar/<int:pk>/', ComenzarEvaluacion.as_view(), name="comenzar_evaluacion"),
    path('instrumento/<int:pk>/', FormularioInstrumentoEmpleado.as_view(), name="instrumento"),
    path('formacion/<int:pk>/', FormacionEmpleado.as_view(), name="formacion"),
    path('metas/<int:pk>/', MetasEmpleado.as_view(), name="metas"),

    path('finalizar/<int:pk>/', FinalizarEvaluacion.as_view(), name="finalizar_evaluacion"),
    path('seccion/', ResultadosPorInstrumentoYVersion.as_view(), name="ver_instrumento"),
    path('formacion/consulta/<int:pk>/', ConsultaFormacionesEvaluacion.as_view(), name="consulta_formacion"),
    path('metas/consulta/<int:pk>/', ConsultaLogrosMetas.as_view(), name="consulta_metas"),

    path('consulta/<int:pk>/', ConsultaEvaluaciones.as_view(), name="consultar_evaluaciones"),
    path('supervisados/<int:pk>/', RevisionSupervisados.as_view(), name="consultar_supervisados"),
]
