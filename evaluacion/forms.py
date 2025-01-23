from django import forms
from .models import Respuesta, Formacion, Competencias, LogrosYMetas

class FormularioRespuestasEmpleado(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        respuesta_empleado = cleaned_data.get("respuesta_empleado")
        comentario_empleado = cleaned_data.get("comentario_empleado")

        if respuesta_empleado == -1 and not comentario_empleado:
            msg = "Si no se ha seleccionado una respuesta, debe ingresar un comentario."
            self.add_error("comentario_empleado", msg)

    class Meta:
        model = Respuesta
        fields = ('respuesta_empleado', 'comentario_empleado', 'pregunta')
        widgets = {
            'pregunta': forms.HiddenInput(),
        }

class FormularioFormacion(forms.ModelForm):
    competencias_genericas = forms.ModelMultipleChoiceField(
        queryset=Competencias.objects.filter(tipo="G"),
        widget=forms.CheckboxSelectMultiple,
    )

    competencias_tecnicas = forms.ModelMultipleChoiceField(
        queryset=Competencias.objects.filter(tipo="T"),
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Formacion
        exclude = ('id', 'evaluacion', 'anadido_por', 'activo')

class FormularioMetas(forms.ModelForm):
    class Meta:
        model = LogrosYMetas
        exclude = ('id', 'anadido_por', 'activo', 'periodo', 'evaluacion')