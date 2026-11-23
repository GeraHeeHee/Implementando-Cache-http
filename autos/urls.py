from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_autos, name='lista_autos'),
    path('agregar/', views.agregar_auto, name='agregar_auto'),
    path('api/autos/', views.api_autos, name='api_autos'),
    path('api/autos/crear/', views.api_crear_auto, name='api_crear_auto'),
]