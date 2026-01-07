from django.db import models
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.conf import settings
import uuid
import os


class GrupoEquivalencia(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    # grupo de escuelas
    escuelas = models.ManyToManyField(
        'users.Escuela',
        related_name='grupos_equivalencia',
        help_text="Escuelas que pueden llevar estos cursos como equivalentes"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre


def syllabus_upload_path(instance, filename):
    extension = os.path.splitext(filename)[1]

    nombre_curso = slugify(instance.nombre)
    nombre_escuela = slugify(instance.escuela.nombre)
    uid = str(instance.id)[:6]

    return f"syllabus/{nombre_curso}-{nombre_escuela}-{uid}{extension}"


class Curso(models.Model):
    ESTADOS = [
        ('PROPUESTO', 'Propuesto (Recogiendo firmas)'),
        ('META_ALCANZADA', 'Meta Alcanzada (Presentar Papeles)'),
        ('EN_TRAMITE', 'En Trámite (Esperando Escuela)'),
        ('APROBADO', 'Aprobado (Oficialmente abierto)'),
        ('CERRADO', 'Cerrado/Rechazado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nombre = models.CharField(max_length=200)
    descripcion = models.CharField(max_length=255, blank=True, null=True,
                                   help_text="Algún detalle del curso que tal vez sea importante mencionar")
    creditos = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(11)])
    codigo_curso = models.CharField(max_length=20, blank=True, help_text="Código oficial en el syllabus")
    escuela = models.ForeignKey('users.Escuela', on_delete=models.CASCADE, related_name='cursos_solicitados')
    grupo_equivalencia = models.ForeignKey(GrupoEquivalencia, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='instancias_curso')
    creador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cursos_creados')

    syllabus = models.FileField(
        upload_to=syllabus_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        max_length=255,
        help_text="El sílabo es obligatorio para validar el curso (max 3MB)"
    )
    whatsapp_link = models.URLField(help_text="Enlace al grupo de coordinación", blank=True, null=True)

    minimo_alumnos = models.PositiveIntegerField(default=15, help_text="Meta para abrir el curso")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PROPUESTO')

    delegado_pendiente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='nominaciones_delegado',
        help_text="Usuario nominado para ser el nuevo delegado"
    )

    contenido_cache = models.TextField(blank=True, null=True, editable=False)
    embedding_vector = models.JSONField(blank=True, null=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nombre} - {self.escuela.nombre}"

    @property
    def total_inscritos(self):
        return self.inscripciones.count()

    @property
    def progreso_porcentaje(self):
        if self.minimo_alumnos == 0: return 100
        return min(int((self.total_inscritos / self.minimo_alumnos) * 100), 100)

    def clean(self):
        super().clean()
        max_size = 3 * 1024 * 1024  # 3 MB

        if self.syllabus and self.syllabus.size > max_size:
            raise ValidationError({
                'syllabus': 'El archivo excede el tamaño máximo permitido de 3 MB.'
            })


class Inscripcion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inscripciones')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='inscripciones')

    documento = models.FileField(
        upload_to='docs_estudiantes/%Y/%m/',
        null=True,
        blank=True,
        help_text="Constancia o documento de requisito"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('usuario', 'curso')
        verbose_name = "Inscripción"
        verbose_name_plural = "Inscripciones"

    def __str__(self):
        return f"{self.usuario.email} -> {self.curso.nombre}"
