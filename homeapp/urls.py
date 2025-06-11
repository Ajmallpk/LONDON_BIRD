from .import views
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
# from django.contrib.auth.views import LogoutView,LoginView


urlpatterns = [
    path('',views.home,name='index'),
   
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
