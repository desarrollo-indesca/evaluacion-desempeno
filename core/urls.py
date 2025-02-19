from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import *

urlpatterns = [
    path('', Dashboard.as_view(), name="dashboard"),
    path('login/', Login.as_view(), name="login"),
    path('logout/', LogoutView.as_view(next_page="/"), name="logout"),
    path('panel-control/', PanelDeControl.as_view(), name="panel_de_control"),

    path('periodo/', PeriodoListView.as_view(), name="periodo_lista"),
    path('periodo/crear/', PeriodoCreateView.as_view(), name="periodo_crear"),
    path('periodo/cerrar/<int:pk>/', CerrarPeriodoView.as_view(), name="periodo_cerrar"),

    path('dnf/', GenerarDNF.as_view(), name="generar_dnf"),
]
