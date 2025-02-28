from django import forms
from django.core.exceptions import ValidationError
from .models import Periodo

class PeriodoForm(forms.ModelForm):
    class Meta:
        model = Periodo
        fields = ['fecha_inicio', 'fecha_fin']

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        if fecha_inicio and fecha_fin and fecha_inicio >= fecha_fin:
            raise ValidationError('La fecha de inicio debe ser anterior a la fecha de fin.')

        if fecha_inicio:
            periodos_previos = Periodo.objects.filter(fecha_fin__gte=fecha_inicio)
            if periodos_previos.exists():
                raise ValidationError('La fecha de inicio debe ser posterior a la fecha de fin de los periodos previos.')

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise ValidationError('La fecha de fin debe ser mayor a la fecha de inicio.')
        
        return cleaned_data
    
    
