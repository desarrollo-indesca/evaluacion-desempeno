from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render
from core.models import Periodo

# Create your views here.

class PeriodoContextMixin():
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['periodo'] = Periodo.objects.get(activo=True)
        return context

class Login(PeriodoContextMixin, LoginView):
    template_name = 'core/login.html'
    
    def get(self, request, *args, **kwargs):
        print(self.get_context_data())
        return super().get(request, *args, **kwargs)

class Dashboard(PeriodoContextMixin, LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'core/dashboard.html')

class Logout(View):
    # TODO
    pass