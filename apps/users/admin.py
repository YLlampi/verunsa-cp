from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Area, Facultad, Escuela


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'created_at')
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(Facultad)
class FacultadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'area', 'created_at')
    list_filter = ('area',)
    search_fields = ('nombre',)
    ordering = ('area', 'nombre')


@admin.register(Escuela)
class EscuelaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'facultad', 'created_at')
    list_filter = ('facultad__area', 'facultad')
    search_fields = ('nombre', 'facultad__nombre')
    ordering = ('facultad', 'nombre')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    ordering = ['email']

    list_display = ('email', 'first_name', 'last_name', 'escuela', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'escuela__facultad', 'groups')
    search_fields = ('email', 'first_name', 'last_name', 'codigo_alumno')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'celular')}),
        ('Datos Académicos', {'fields': ('escuela', 'codigo_alumno')}),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )

    readonly_fields = ('date_joined', 'last_login')