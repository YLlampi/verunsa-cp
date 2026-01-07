from django.db.models import Sum, Q, Exists, OuterRef
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from apps.courses.forms import CursoForm, InscripcionDocForm
from apps.courses.models import Curso, Inscripcion
from apps.courses.services import extraer_datos_inteligente
from apps.users.models import Escuela, Facultad, User
from django.contrib import messages
from apps.courses.tasks import task_analizar_curso_ia


def landing_view(request):
    return render(request, 'landing.html')


@login_required
def onboarding_view(request):
    if request.user.escuela and request.user.codigo_alumno and request.user.celular:
        return redirect('frontend:dashboard')

    if request.method == 'POST':
        escuela_id = request.POST.get('escuela_id')
        codigo_alumno = request.POST.get('codigo_alumno')
        celular = request.POST.get('celular')

        if escuela_id and codigo_alumno and celular:
            try:
                escuela = Escuela.objects.get(id=escuela_id)

                if User.objects.filter(codigo_alumno=codigo_alumno).exclude(id=request.user.id).exists():
                    messages.error(request, "El código de alumno (CUI) ya está registrado. Usa otro.")
                    return redirect('frontend:onboarding')

                if User.objects.filter(celular=celular).exclude(id=request.user.id).exists():
                    messages.error(request, "El celular ya está registrado. Usa otro.")
                    return redirect('frontend:onboarding')

                request.user.escuela = escuela
                request.user.codigo_alumno = codigo_alumno
                request.user.celular = celular
                request.user.save()

                messages.success(request, f"¡Perfil completado! Bienvenido a la comunidad de {escuela.nombre}.")
                return redirect('frontend:dashboard')
            except Escuela.DoesNotExist:
                messages.error(request, "La escuela seleccionada no es válida.")
        else:
            messages.error(request, "Por favor completa todos los campos obligatorios.")

    facultades = Facultad.objects.prefetch_related('escuelas').all()

    return render(request, 'auth/onboarding.html', {'facultades': facultades})


@login_required
def dashboard_view(request):
    user = request.user
    if not user.escuela or not user.celular or not user.codigo_alumno:
        return redirect('frontend:onboarding')

    filtro_mi_escuela = Q(escuela=user.escuela)

    filtro_equivalentes = Q(grupo_equivalencia__escuelas=user.escuela)

    inscrito_subquery = Inscripcion.objects.filter(
        usuario=user,
        curso=OuterRef('pk')
    )

    cursos = (
        Curso.objects
        .filter(filtro_mi_escuela | filtro_equivalentes)
        .annotate(is_inscrito_db=Exists(inscrito_subquery))  # 1 si inscrito, 0 si no
        .select_related('escuela', 'creador')
        .distinct()
        .order_by('-is_inscrito_db', '-created_at')
    )

    mis_inscripciones_ids = Inscripcion.objects.filter(usuario=user).values_list('curso_id', flat=True)

    for curso in cursos:
        curso.is_inscrito = curso.id in mis_inscripciones_ids

        curso.is_equivalente = (curso.escuela != user.escuela)

    context = {
        'cursos': cursos
    }
    return render(request, 'muro/dashboard.html', context)


@login_required
def create_course_view(request):
    """
    Permite al estudiante proponer un nuevo curso y agenda el análisis IA en background.
    """
    if request.method == 'POST':
        form = CursoForm(request.POST, request.FILES)
        if form.is_valid():
            syllabus_file = request.FILES.get('syllabus')

            datos_pdf = extraer_datos_inteligente(syllabus_file)

            if not datos_pdf['valido']:
                messages.error(request, f"Error de archivo: {datos_pdf['mensaje_error']}")
                return render(request, 'courses/create.html', {'form': form})

            if not datos_pdf['es_silabo']:
                messages.warning(request,
                                 f"Documento rechazado: {datos_pdf['mensaje_error']}")
                return render(request, 'courses/create.html', {'form': form})

            contenido_limpio = datos_pdf['contenido_raw']

            if contenido_limpio:
                duplicado = Curso.objects.filter(
                    creador=request.user,
                    contenido_cache=contenido_limpio
                ).exists()

                if duplicado:
                    messages.error(request,
                                   "Ya has creado un curso con este mismo sílabo anteriormente. Revisa tu Muro.")
                    return redirect('frontend:dashboard')

            curso = form.save(commit=False)
            inscripcion = Inscripcion.objects.filter(usuario=request.user)
            creditos_actuales = inscripcion.aggregate(Sum('curso__creditos'))['curso__creditos__sum'] or 0

            if datos_pdf['creditos'] > 0:
                curso.creditos = datos_pdf['creditos']

            if creditos_actuales + curso.creditos > 11:
                messages.error(request,
                               f"No puedes inscribirte. Excederías el límite de 11 créditos (Tienes {creditos_actuales} créditos).")
                return redirect('frontend:dashboard')

            cursos_actuales = inscripcion.count()
            if cursos_actuales >= 2:
                messages.error(request,
                               f"No puedes inscribirte. Excederías el límite de 2 cursos (Estas en {cursos_actuales} cursos).")
                return redirect('frontend:dashboard')

            curso.creador = request.user
            curso.escuela = request.user.escuela
            curso.contenido_cache = datos_pdf['contenido_raw']
            curso.save()

            # Inscripción del delegado
            Inscripcion.objects.create(usuario=request.user, curso=curso)

            # Tarea Asíncrona
            task_analizar_curso_ia.delay(curso.id)

            messages.success(request,
                             "¡Curso creado exitosamente! Nuestra IA está analizando el sílabo en segundo plano para encontrar equivalencias. Se mostrará en el muro si se agrupa automáticamente.")

            return redirect('frontend:dashboard')

    else:
        form = CursoForm()

    return render(request, 'courses/create.html', {'form': form})


@login_required
def join_course_view(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    user = request.user

    # Validar si ya está inscrito en este curso específico
    if Inscripcion.objects.filter(usuario=user, curso=curso).exists():
        messages.warning(request, "Ya estás inscrito en este curso.")
        return redirect('frontend:dashboard')

    if curso.grupo_equivalencia:
        ya_tiene_equivalente = Inscripcion.objects.filter(
            usuario=user,
            curso__grupo_equivalencia=curso.grupo_equivalencia
        ).exists()

        if ya_tiene_equivalente:
            messages.error(
                request,
                f"No puedes inscribirte. Ya estás registrado en un curso similar del grupo '{curso.grupo_equivalencia.nombre}'."
            )
            return redirect('frontend:dashboard')

    # Validar límite de créditos, maximo 11
    inscripcion = Inscripcion.objects.filter(usuario=user)
    creditos_actuales = inscripcion.aggregate(Sum('curso__creditos'))[
                            'curso__creditos__sum'] or 0

    if creditos_actuales + curso.creditos > 11:
        messages.error(request,
                       f"No puedes inscribirte. Excederías el límite de 11 créditos (Tienes {creditos_actuales} créditos).")
        return redirect('frontend:dashboard')

    cursos_actuales = inscripcion.count()
    if cursos_actuales >= 2:
        messages.error(request,
                       f"No puedes inscribirte. Excederías el límite de 2 cursos (Estas en {cursos_actuales} cursos).")
        return redirect('frontend:dashboard')

    Inscripcion.objects.create(usuario=user, curso=curso)
    messages.success(request, f"Te has unido a {curso.nombre}. ¡Avisa a tus amigos!")
    return redirect('frontend:course_detail', curso.id)


@login_required
def leave_course_view(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)

    inscripcion = Inscripcion.objects.filter(usuario=request.user, curso=curso).first()
    if inscripcion:
        inscripcion.delete()
        messages.info(request, f"Te has retirado de {curso.nombre}.")
    else:
        messages.warning(request, "No estabas inscrito en ese curso.")

    return redirect('frontend:dashboard')


@login_required
def course_detail_view(request, curso_id):
    user = request.user

    if not user.escuela:
        return redirect('frontend:onboarding')

    curso = get_object_or_404(Curso, id=curso_id)

    filtro_mi_escuela = Q(escuela=user.escuela)
    filtro_equivalentes = Q(grupo_equivalencia__escuelas=user.escuela)

    tiene_permiso = Curso.objects.filter(
        (filtro_mi_escuela | filtro_equivalentes),
        id=curso.id
    ).exists()

    if not tiene_permiso:
        messages.error(request, "No tienes permisos para ver ese curso (Pertenece a otra escuela).")
        return redirect('frontend:dashboard')

    inscripciones = curso.inscripciones.select_related('usuario__escuela').order_by('created_at')

    es_delegado_actual = (user == curso.creador)

    lista_alumnos = []
    for insc in inscripciones:
        u = insc.usuario

        # 1. Enmascarar apellido
        apellido_safe = f"{u.last_name[0]}****" if u.last_name else "****"

        # 2. Enmascarar CUI
        cui_safe = "****"
        if u.codigo_alumno and len(u.codigo_alumno) >= 4:
            cui_safe = "****" + u.codigo_alumno[-4:]

        wa_link = None
        if u.celular:
            clean_number = ''.join(filter(str.isdigit, u.celular))
            wa_link = f"https://wa.me/51{clean_number}"

        lista_alumnos.append({
            'inscripcion_id': insc.id,
            'usuario_id': u.id,
            'nombre': u.first_name,
            'apellido': apellido_safe,
            'cui': cui_safe,
            'escuela_nombre': u.escuela.nombre if u.escuela else "Sin Escuela",
            'fecha': insc.created_at,
            'es_delegado_rol': (u == curso.creador),
            'documento': insc.documento,
            'wa_link': wa_link,
            'es_mi_fila': (u == request.user)
        })

    is_inscrito = Inscripcion.objects.filter(usuario=request.user, curso=curso).exists()

    context = {
        'curso': curso,
        'alumnos': lista_alumnos,
        'is_inscrito': is_inscrito,
        'es_delegado': es_delegado_actual,
        'doc_form': InscripcionDocForm()
    }
    return render(request, 'courses/detail.html', context)


@login_required
def leave_course_view(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    user = request.user

    if curso.creador == user:
        if curso.inscripciones.count() == 1:
            curso.delete()
            messages.info(request, f"El curso '{curso.nombre}' ha sido eliminado porque eras el único integrante.")
            return redirect('frontend:dashboard')

        else:
            messages.error(request,
                           "No puedes salirte porque eres el Delegado. Debes asignar tu cargo a otro compañero y esperar a que acepte.")
            return redirect('frontend:course_detail', curso_id=curso.id)

    if curso.delegado_pendiente == user:
        curso.delegado_pendiente = None
        curso.save()

    inscripcion = Inscripcion.objects.filter(usuario=user, curso=curso).first()
    if inscripcion:
        inscripcion.delete()
        messages.info(request, f"Te has retirado de {curso.nombre}.")

    return redirect('frontend:dashboard')


@login_required
def nominate_delegado_view(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)

    if curso.creador != request.user:
        return redirect('frontend:dashboard')

    if request.method == 'POST':
        nuevo_id = request.POST.get('sucesor_id')
        sucesor = get_object_or_404(User, id=nuevo_id)

        if not Inscripcion.objects.filter(curso=curso, usuario=sucesor).exists():
            messages.error(request, "El usuario seleccionado no está inscrito.")
        else:
            curso.delegado_pendiente = sucesor
            curso.save()
            messages.success(request, f"Solicitud enviada a {sucesor.first_name}. Debes esperar a que acepte.")
            return redirect('frontend:course_detail', curso_id=curso.id)

    candidatos = curso.inscripciones.exclude(usuario=request.user).select_related('usuario')

    return render(request, 'courses/nominate.html', {'curso': curso, 'candidatos': candidatos})


@login_required
def respond_nomination_view(request, curso_id, accion):
    curso = get_object_or_404(Curso, id=curso_id)

    if curso.delegado_pendiente != request.user:
        messages.error(request, "No tienes una solicitud pendiente para este curso.")
        return redirect('frontend:dashboard')

    if accion == 'aceptar':
        curso.creador = request.user
        curso.delegado_pendiente = None
        curso.save()
        messages.success(request,
                         f"¡Aceptado! Ahora eres el Delegado de {curso.nombre}. El anterior delegado ya puede retirarse.")

    elif accion == 'rechazar':
        curso.delegado_pendiente = None
        curso.save()
        messages.info(request, "Has rechazado el cargo de Delegado.")

    return redirect('frontend:dashboard')


@login_required
def upload_document_view(request, inscripcion_id):
    inscripcion = get_object_or_404(Inscripcion, id=inscripcion_id)

    if inscripcion.usuario != request.user:
        messages.error(request, "No puedes subir documentos de otros.")
        return redirect('frontend:course_detail', curso_id=inscripcion.curso.id)

    if request.method == 'POST':
        form = InscripcionDocForm(request.POST, request.FILES, instance=inscripcion)
        if form.is_valid():
            form.save()
            messages.success(request, "Documento subido correctamente.")

    return redirect('frontend:course_detail', curso_id=inscripcion.curso.id)


@login_required
def delete_document_view(request, inscripcion_id):
    inscripcion = get_object_or_404(Inscripcion, id=inscripcion_id)

    if inscripcion.usuario != request.user:
        messages.error(request, "No tienes permiso.")
        return redirect('frontend:course_detail', curso_id=inscripcion.curso.id)

    if inscripcion.documento:
        inscripcion.documento.delete()
        inscripcion.save()
        messages.info(request, "Documento eliminado.")

    return redirect('frontend:course_detail', curso_id=inscripcion.curso.id)
