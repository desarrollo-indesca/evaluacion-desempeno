from django import forms

class FormularioRespuestas(forms.ModelForm):
    class Meta:
        model = ResultadoInstrumento
        fields = ('respuesta', 'comentario')