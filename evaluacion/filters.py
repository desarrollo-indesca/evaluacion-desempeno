import django_filters
from core.models import DatosPersonal
from evaluacion.models import Evaluacion, Periodo, SolicitudPromocion, ESTADOS

class EvaluacionFilter(django_filters.FilterSet):
    
    class Meta:
        model = Evaluacion
        fields = ['periodo', 'estado']

class DatosPersonalFilter(django_filters.FilterSet):
    ficha = django_filters.CharFilter(lookup_expr='icontains', field_name='ficha')
    user__first_name = django_filters.CharFilter(label="El nombre del usuario contiene", lookup_expr='icontains', field_name='user__first_name')

    evaluacion_estado = django_filters.ChoiceFilter(
        label="Estado de la Evaluación",
        choices=ESTADOS,
        method='filter_evaluacion_estado'
    )

    def filter_evaluacion_estado(self, queryset, name, value):
        qs = queryset
        try:
            qs = qs.filter(
                evaluaciones__periodo=Periodo.objects.get(activo = True),
                evaluaciones__estado=value
            )
        except Periodo.DoesNotExist:
            pass
        return qs
    
    class Meta:
        model = DatosPersonal
        fields = ['user__first_name', 'cargo', 'tipo_personal', 'gerencia', 'ficha', 'fecha_ingreso']

class SolicitudPromocionFilter(django_filters.FilterSet):
    evaluacion__evaluado__user__first_name__icontains = django_filters.CharFilter(label="El nombre del usuario contiene", lookup_expr='icontains', field_name='evaluacion__evaluado__user__first_name')
    
    class Meta:
        model = SolicitudPromocion
        fields = [
            'evaluacion__evaluado__user__first_name', 'evaluacion__periodo',
            'aprobado'
        ]
