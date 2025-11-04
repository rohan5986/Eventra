from django import forms


class EventTextInputForm(forms.Form):
    """Form for user to input unstructured text."""
    
    text_input = forms.CharField(
        label='Enter event details',
        widget=forms.Textarea(attrs={
            'rows': 5,
            'cols': 50,
            'placeholder': 'e.g., "Lunch with Dr. Rivera on October 17th at 1pm at Harvard Square"',
            'class': 'form-control'
        }),
        help_text='Describe your event in natural language. Include date, time, location, and description.'
    )


