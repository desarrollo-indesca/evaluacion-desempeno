from django.views import View
from .models import *
from django.shortcuts import render, redirect

# Create your views here.

class ComenzarEvaluacion(View):
    def post(self, request, pk):
        evaluacion = Evaluacion.objects.get(pk=pk)
        evaluacion.estado = 'E'
        evaluacion.save()
        return redirect('dashboard')