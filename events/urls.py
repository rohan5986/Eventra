from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('create/', views.create_event_from_text, name='create_event'),
    path('preview/', views.preview_event, name='preview_event'),
    path('', views.list_events, name='list_events'),
    path('home/', views.home, name='home'),
    path('<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('<int:event_id>/edit/', views.edit_event, name='edit_event'),
]

