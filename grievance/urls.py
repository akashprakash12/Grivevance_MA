"""
URL configuration for grievance project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
# 🔻 Add these two imports
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin_app/', include('admin_app.urls')),
    path('officer/', include('officer.urls')),       # ✅ Included once
    path('collector/', include('collector.urls')),
    path('', include('accounts.urls')),
    path('core/', include('core_app.urls')),
    path('public_user/', include('user.urls', namespace='public_user')),  # ✅ correct
    path('grievance/', include('grievance_app.urls')),


]
# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)