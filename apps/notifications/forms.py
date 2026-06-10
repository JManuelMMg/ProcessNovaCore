from django import forms

INPUT = 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'


class ComposeEmailForm(forms.Form):
    to = forms.EmailField(widget=forms.EmailInput(attrs={'class': INPUT, 'placeholder': 'destinatario@ejemplo.com'}))
    subject = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': INPUT, 'placeholder': 'Asunto'}))
    body = forms.CharField(widget=forms.Textarea(attrs={'class': INPUT, 'rows': 10, 'placeholder': 'Escribe tu mensaje...'}))
