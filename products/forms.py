from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'image', 'image2', 'image3', 'image4', 'image5', 'description', 'price', 'stock', 'available']
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
        }

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.fields['category'].empty_label = "Selecione..."
