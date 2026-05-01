from django.urls import path
from . import views

app_name = 'produtos'

urlpatterns = [
    path('gerenciar/', views.manage_products, name='gerenciar'),
    path('gerenciar/categorias/', views.manage_categories, name='gerenciar_categorias'),
    path('gerenciar/adicionar/', views.add_product, name='adicionar'),
    path('gerenciar/editar/<int:id>/', views.edit_product, name='editar'),
    path('gerenciar/deletar/<int:id>/', views.delete_product, name='deletar'),
    path('gerenciar/esvaziar-estoque/', views.empty_stock, name='esvaziar_estoque'),
    path('gerenciar/categoria/deletar/<int:id>/', views.delete_category, name='deletar_categoria'),
    path('api/categorias/adicionar/', views.api_add_category, name='api_add_category'),
    path('api/categorias/deletar/<int:id>/', views.api_delete_category, name='api_delete_category'),
    path('api/categorias/lista/', views.api_list_categories, name='api_list_categories'),
    path('api/pedidos/data/', views.api_orders_by_date, name='api_orders_by_date'),
    path('api/insumos/adicionar/', views.api_add_supply, name='api_add_supply'),
    path('api/insumos/deletar/<int:id>/', views.api_delete_supply, name='api_delete_supply'),
    path('api/ficha/salvar/', views.api_save_batch_recipe, name='api_save_batch_recipe'),
    path('api/ficha/detalhes/<int:product_id>/', views.api_get_batch_details, name='api_get_batch_details'),
    path('api/lista-simples/', views.api_product_list_simple, name='api_product_list_simple'),
    path('api/linhas/', views.product_list_rows_api, name='product_list_rows_api'),
    path('api/grade/', views.product_grid_api, name='product_grid_api'),
    path('', views.product_list, name='lista'),
    path('<slug:category_slug>/', views.product_list, name='lista_por_categoria'),
    path('avaliacao/deletar/<int:review_id>/', views.delete_review, name='deletar_avaliacao'),
    path('<int:id>/<slug:slug>/', views.product_detail, name='detalhes'),
]
