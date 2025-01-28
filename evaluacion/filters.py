import django_filters
from core.models import DatosPersonal
from evaluacion.models import Evaluacion

#TODO
class EvaluacionFilter(django_filters.FilterSet):
    class Meta:
        model = Evaluacion
        fields = [...]

class DatosPersonalFilter(django_filters.FilterSet):
    class Meta:
        model = DatosPersonal
        fields = [...]