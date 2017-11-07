from django import forms

from .models import Item


class ItemForm(forms.ModelForm):
    description = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Why are you making this change?'}),
        label='Activity description')

    class Meta:
        model = Item
        fields = ['title', 'number', 'effective_date', 'description']
        widgets = {
            'effective_date': forms.DateInput(attrs={'type': 'date'}),
        }
