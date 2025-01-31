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

class FormularioRespuestasSupervisor(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        respuesta_supervisor = cleaned_data.get("respuesta_supervisor")
        comentario_supervisor = cleaned_data.get("comentario_supervisor")

        if respuesta_supervisor == -1 and not comentario_supervisor:
            msg = "Si no se ha seleccionado una respuesta, debe ingresar un comentario."
            self.add_error("comentario_supervisor", msg)

    class Meta:
        model = Respuesta
        fields = ('respuesta_supervisor', 'comentario_supervisor', 'pregunta')
        widgets = {
            'pregunta': forms.HiddenInput(),
        }

class FormularioFormacion(forms.ModelForm):
    competencias_genericas = forms.ModelMultipleChoiceField(
        queryset=Competencias.objects.filter(tipo="G"),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    competencias_tecnicas = forms.ModelMultipleChoiceField(
        queryset=Competencias.objects.filter(tipo="T"),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if(kwargs.get('instance')):
            self.fields['competencias_genericas'].initial =kwargs['instance'].competencias.filter(tipo="G")
            self.fields['competencias_tecnicas'].initial = kwargs['instance'].competencias.filter(tipo="T")

    class Meta:
        model = Formacion
        exclude = ('id', 'evaluacion', 'anadido_por', 'activo', 'competencias')

class FormularioMetas(forms.ModelForm):
    class Meta:
        model = LogrosYMetas
        exclude = ('id', 'anadido_por', 'activo', 'periodo', 'evaluacion')