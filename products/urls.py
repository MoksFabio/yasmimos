from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('manage/', views.manage_products, name='manage_products'),
    path('manage/add/', views.add_product, name='add_product'),
    path('manage/edit/<int:id>/', views.edit_product, name='edit_product'),
    path('manage/delete/<int:id>/', views.delete_product, name='delete_product'),
    path('manage/category/delete/<int:id>/', views.delete_category, name='delete_category'),
    path('api/categories/add/', views.api_add_category, name='api_add_category'),
    path('api/categories/delete/<int:id>/', views.api_delete_category, name='api_delete_category'),
    path('api/categories/list/', views.api_list_categories, name='api_list_categories'),
    path('api/orders/date/', views.api_orders_by_date, name='api_orders_by_date'),
    path('api/rows/', views.product_list_rows_api, name='product_list_rows_api'),
    path('api/grid/', views.product_grid_api, name='product_grid_api'),
    path('', views.product_list, name='product_list'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
]
