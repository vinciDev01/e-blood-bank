"""
URL configuration for eBloodBank project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('frontend.urls')),
    path('bankDeSang/', include('bankDeSang.urls')),
    path('serviceMedicaux/', include('serviceMedicaux.urls')),
    path('donneur/', include('donneur.urls')),
    path('_auth/', include('_auth.urls')),
]

if settings.DEBUG: # Si le mode DEBUG est activé
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) # Pour servir les fichiers médias en mode développement
