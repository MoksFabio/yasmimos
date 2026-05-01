from django import forms
from .models import Product, Review

class ProductForm(forms.ModelForm):
    price = forms.CharField(
        label='Preço (R$)',
        widget=forms.TextInput(attrs={'type': 'text', 'inputmode': 'decimal', 'class': 'form-control'})
    )

    class Meta:
        model = Product
        fields = ['category', 'name', 'image', 'image2', 'image3', 'image4', 'image5', 'description', 'price', 'stock', 'available', 'is_customizable', 'customizable_slots', 'customization_category']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'image': forms.FileInput(),
            'image2': forms.FileInput(),
            'image3': forms.FileInput(),
            'image4': forms.FileInput(),
            'image5': forms.FileInput(),
        }
        labels = {
            'category': 'Categoria',
            'name': 'Nome do Produto',
            'image': 'Imagem Principal',
            'image2': 'Imagem 2 (Opcional)',
            'image3': 'Imagem 3 (Opcional)',
            'image4': 'Imagem 4 (Opcional)',
            'image5': 'Imagem 5 (Opcional)',
            'description': 'Descrição Detalhada',
            'price': 'Preço (R$)',
            'stock': 'Quantidade em Estoque',
            'available': 'Disponível para Venda?',
            'is_customizable': 'É personalizável?',
            'customizable_slots': 'Vagas de Personalização',
            'customization_category': 'Categoria de Personalização',
        }

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields['category'].empty_label = "Selecione..."

    def clean_price(self):
        price_str = self.cleaned_data.get('price')
        if not price_str:
            return None
            
        if isinstance(price_str, str):
            price_str = price_str.replace(',', '.')
            try:
                import decimal
                return decimal.Decimal(price_str)
            except (decimal.InvalidOperation, ValueError):
                raise forms.ValidationError("Digite um preço válido.")
        
        return price_str

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
           'rating': forms.RadioSelect(choices=[(i, str(i)) for i in range(1, 6)]),
           'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'O que você achou deste produto? Escreva sua avaliação...'}),
        }
        labels = {
            'rating': 'Nota',
            'comment': 'Comentário'
        }
