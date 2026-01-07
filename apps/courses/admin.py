from django.contrib import admin
from .models import Curso, GrupoEquivalencia, Inscripcion


@admin.register(GrupoEquivalencia)
class GrupoEquivalenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'created_at')
    search_fields = ('nombre',)


class InscripcionInline(admin.TabularInline):
    model = Inscripcion
    extra = 0
    readonly_fields = ('usuario', 'created_at')
    can_delete = True


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'escuela', 'creador_email', 'estado', 'ver_inscritos', 'minimo_alumnos', 'created_at')
    list_filter = ('estado', 'escuela__facultad', 'created_at')
    search_fields = ('nombre', 'creador__email', 'escuela__nombre')

    actions = ['marcar_como_aprobado', 'marcar_como_cerrado']
    inlines = [InscripcionInline]

    def creador_email(self, obj):
        return obj.creador.email

    creador_email.short_description = 'Delegado'

    def ver_inscritos(self, obj):
        return f"{obj.total_inscritos} / {obj.minimo_alumnos}"

    ver_inscritos.short_description = 'Progreso'

    readonly_fields = ('contenido_cache', 'embedding_vector')

    @admin.action(description='Marcar cursos seleccionados como APROBADOS')
    def marcar_como_aprobado(self, request, queryset):
        queryset.update(estado='APROBADO')

    @admin.action(description='Marcar cursos seleccionados como CERRADOS')
    def marcar_como_cerrado(self, request, queryset):
        queryset.update(estado='CERRADO')


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'curso', 'created_at')
    list_filter = ('curso__escuela', 'created_at')
    search_fields = ('usuario__email', 'curso__nombre')
