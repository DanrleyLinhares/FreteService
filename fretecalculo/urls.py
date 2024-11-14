from django.contrib import admin
from django.urls import path
from calculo.views import calculo  # Importa a view calculo

urlpatterns = [
    path('admin/', admin.site.urls),
    path('calculo/', calculo, name='calculo'),  # URL para a view de cálculo
    path('', calculo, name='home'),  # Redireciona a raiz para a view de cálculo
]
