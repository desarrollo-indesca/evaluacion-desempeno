import django_filters
from core.models import DatosPersonal
from evaluacion.models import Evaluacion

class EvaluacionFilter(django_filters.FilterSet):
    
    class Meta:
        model = Evaluacion
        fields = ['periodo', 'estado']

class DatosPersonalFilter(django_filters.FilterSet):
    ficha = django_filters.CharFilter(lookup_expr='icontains', field_name='ficha')
    user__first_name = django_filters.CharFilter(label="El nombre del usuario contiene", lookup_expr='icontains', field_name='user__first_name')
    
    class Meta:
        model = DatosPersonal
        fields = ['user__first_name', 'cargo', 'tipo_personal', 'supervisor__ficha', 
                  'supervisor__nombre', 'gerencia', 'ficha', 'fecha_ingreso']