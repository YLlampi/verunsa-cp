from django import forms
from .models import Curso, Inscripcion


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nombre', 'descripcion', 'creditos', 'whatsapp_link', 'syllabus']
        widgets = {
            'nombre': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': ''}),
            'descripcion': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': ''}),
            'creditos': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 11}),
            'whatsapp_link': forms.URLInput(
                attrs={'class': 'form-control', 'placeholder': 'https://chat.whatsapp.com/...'}),
            'syllabus': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
        }
        labels = {
            'syllabus': 'Sílabo (PDF)',
            'whatsapp_link': 'Link del Grupo de WhatsApp',
            'nombre': 'Nombre del Curso',
            'creditos': 'Número de Créditos'
        }

    def clean_syllabus(self):
        archivo = self.cleaned_data.get('syllabus')

        if archivo:
            max_size = 3 * 1024 * 1024  # 3 MB
            if archivo.size > max_size:
                raise forms.ValidationError("El archivo debe ser menor a 3 MB.")

        return archivo


class InscripcionDocForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = ['documento']
