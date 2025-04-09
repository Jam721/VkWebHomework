from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings
urlpatterns = [
    path('', views.index, name='index'),
    path('ask/', views.ask, name='ask'),
    path('login/', views.login_view, name='login'),
    path('settings/', views.settings, name='settings'),
    path('tag/<str:tag_name>/', views.tag, name='tag'),
    path('signup/', views.signup, name='signup'),
    path('question/<int:question_id>/', views.question, name='question'),
    path('answer/<int:question_id>/', views.answer, name='answer'),
    path('logout/', views.logout_view, name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
