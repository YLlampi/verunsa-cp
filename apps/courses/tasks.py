from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from .models import Curso
from .services import procesar_y_agrupar_curso


@shared_task(bind=True, max_retries=2)
def task_analizar_curso_ia(self, curso_id):
    """
    Tarea asíncrona para recuperar el curso y ejecuta lógica de IA.
    """
    try:
        print(f"[CELERY] Iniciando análisis para curso ID: {curso_id}")
        curso = Curso.objects.get(id=curso_id)

        # Ejecutamos lógica core
        match_encontrado = procesar_y_agrupar_curso(curso)

        if match_encontrado:
            return f"Curso {curso.nombre} AGRUPADO en {curso.grupo_equivalencia.nombre}"
        else:
            return f"Curso {curso.nombre} SIN MATCH (Grupo Nuevo Generado)"

    except ObjectDoesNotExist:
        return f"Error: El curso {curso_id} no existe."
    except Exception as e:
        print(f"[CELERY ERROR] {e}")

        raise self.retry(exc=e, countdown=10 * (self.request.retries + 1))
