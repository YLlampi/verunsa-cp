from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Inscripcion


@receiver(post_save, sender=Inscripcion)
def notificar_nueva_inscripcion(sender, instance, created, **kwargs):
    if created:
        curso = instance.curso
        nuevo_alumno = instance.usuario
        delegado = curso.creador

        # Ver notificaciones (delegado)
        if nuevo_alumno != delegado:
            asunto = f"Nueva inscripción en {curso.nombre}"
            mensaje = f"Hola {delegado.first_name}, \n\n{nuevo_alumno.email} se acaba de unir a tu curso '{curso.nombre}'.\n\nTotal inscritos: {curso.total_inscritos}/{curso.minimo_alumnos}."

            send_mail(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [delegado.email],
                fail_silently=True
            )

        # Notificar a todos si se llega a la meta
        if curso.total_inscritos == curso.minimo_alumnos:
            asunto_meta = f"¡META ALCANZADA! {curso.nombre} está listo."
            mensaje_meta = f"¡Buenas noticias! El curso '{curso.nombre}' ha alcanzado los {curso.minimo_alumnos} inscritos necesarios.\n\nDelegado ({delegado.email}), por favor inicia el trámite en Dirección."

            emails_inscritos = list(curso.inscripciones.values_list('usuario__email', flat=True))

            send_mail(
                asunto_meta,
                mensaje_meta,
                settings.DEFAULT_FROM_EMAIL,
                emails_inscritos,
                fail_silently=True
            )
