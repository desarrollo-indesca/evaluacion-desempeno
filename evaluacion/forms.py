from django import forms
from .models import Respuesta

class FormularioRespuestasEmpleado(forms.ModelForm):
    class Meta:
        model = Respuesta
        fields = ('respuesta_empleado', 'comentario_empleado', 'pregunta')
        widgets = {
            'pregunta': forms.HiddenInput(),
        }