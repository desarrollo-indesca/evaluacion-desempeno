from django.urls import path
from .views import *

urlpatterns = [
    path('comenzar/<int:pk>/', ComenzarEvaluacion.as_view(), name="comenzar_evaluacion"),
    path('instrumento/<int:pk>/', FormularioInstrumentoEmpleado.as_view(), name="instrumento"),
]
