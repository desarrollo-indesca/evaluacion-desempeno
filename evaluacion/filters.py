import django_filters
from core.models import DatosPersonal
from evaluacion.models import Evaluacion

class EvaluacionFilter(django_filters.FilterSet):
    
    class Meta:
        model = Evaluacion
        fields = ['periodo', 'estado']

class DatosPersonalFilter(django_filters.FilterSet):
    ficha = django_filters.CharFilter(lookup_expr='icontains', field_name='ficha')
    supervisor__ficha = django_filters.CharFilter(lookup_expr='icontains', field_name='supervisor__ficha')
    supervisor__nombre = django_filters.CharFilter(lookup_expr='icontains', field_name='supervisor__ficha')
    user__nombre = django_filters.CharFilter(lookup_expr='icontains', field_name='user__nombre')
    fecha_ingreso__gte = django_filters.DateFilter(field_name='fecha_ingreso', lookup_expr='gte')
    fecha_ingreso__lte = django_filters.DateFilter(field_name='fecha_ingreso', lookup_expr='lte')

    class Meta:
        model = DatosPersonal
        fields = ['user__nombre', 'cargo', 'tipo_personal', 'supervisor__ficha', 
                  'supervisor__nombre', 'gerencia', 'ficha', 'fecha_ingreso']