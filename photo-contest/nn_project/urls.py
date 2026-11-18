from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from app import views
from app.views import auth_refresh

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/csrf/', views.get_xcsrf, name='csrf'),
    path('api/users/', views.users, name='users'),
    path('api/email_confirm/', views.email_confirm, name='email_confirm'),
    path('api/auth/', views.login, name='auth'),
    path('api/logout/', views.logout, name='logout'),
    path('api/test/', views.test, name='test'),
    path('api/', views.main, name='main'),
    path('api/contests/', views.contests, name='contests'),
    path('api/refresh/', auth_refresh, name='auth_refresh'),
    path('api/works/', views.works, name='works'),
    path('api/contests/analytics/', views.contests_analytics_csv, name='contests_analytics'),
    path('api/ws-ticket/', views.ws_ticket, name='ws_ticket'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)