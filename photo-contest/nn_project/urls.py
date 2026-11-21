from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from app import views
from app.views import auth_refresh, index, login_page, contest_page

urlpatterns = [
    path('', index, name='index'),
    path('admin/', admin.site.urls),
    path('api/csrf/', views.get_xcsrf, name='csrf'),
    path('api/contests/<int:contest_id>/status/', views.change_contest_status, name='change_contest_status'),
    path('api/users/', views.users, name='users'),
    path('api/email_confirm/', views.email_confirm, name='email_confirm'),
    path('api/auth/', views.login, name='auth'),
    path('api/logout/', views.logout, name='logout'),
    path('api/test/', views.test, name='test'),
    path('api/contests/<int:contest_id>/winners/', views.get_contest_winners, name='get_contest_winners'),
    path('api/logout/refresh/', views.logout_refresh, name='logout_refresh'),
    path('api/', views.main, name='main'),
    path('profile/', views.profile_page, name='profile_page'),
    path('login/', login_page, name='login_page'),
    path('contest/', contest_page, name='contest_page'),
    path('api/works/moderate/', views.moderate_work, name='moderate_work'),
    path('api/profile/', views.profile, name='profile'),
    path('api/change-password/', views.change_password, name='change_password'),
    path('api/admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('api/votes/', views.votes, name='votes'),
    path('api/users/<int:user_id>/block/', views.block_user, name='block_user'),
    path('api/contests/', views.contests, name='contests'),
    path('api/refresh/', auth_refresh, name='auth_refresh'),
    path('api/works/', views.works, name='works'),
    path('api/works/<int:work_id>/view/', views.increment_work_views, name='increment_work_views'), # <-- ДОБАВЛЕНО
    path('api/contests/analytics/', views.contests_analytics_csv, name='contests_analytics'),
    path('api/ws-ticket/', views.ws_ticket, name='ws_ticket'),
    path('api/comments/', views.comments, name='comments'), # <-- ДОБАВЛЕНО
    path('api/comments/<int:comment_id>/', views.delete_comment, name='delete_comment'), # <-- ДОБАВЛЕНО
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)