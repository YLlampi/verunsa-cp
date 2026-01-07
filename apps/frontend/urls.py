from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.landing_view, name='landing'),

    path('bienvenido/', views.onboarding_view, name='onboarding'),
    path('muro/', views.dashboard_view, name='dashboard'),
    path('crear-curso/', views.create_course_view, name='create_course'),
    path('unirse/<uuid:curso_id>/', views.join_course_view, name='join_course'),
    path('salir/<uuid:curso_id>/', views.leave_course_view, name='leave_course'),

    path('curso/<uuid:curso_id>/', views.course_detail_view, name='course_detail'),

    path('delegar/<uuid:curso_id>/', views.nominate_delegado_view, name='nominate_delegado'),
    path('responder-delegacion/<uuid:curso_id>/<str:accion>/', views.respond_nomination_view,
         name='respond_nomination'),

    path('subir-doc/<int:inscripcion_id>/', views.upload_document_view, name='upload_doc'),
    path('borrar-doc/<int:inscripcion_id>/', views.delete_document_view, name='delete_doc'),
]
