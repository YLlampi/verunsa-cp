import re
import os
import io
import logging
import numpy as np
import spacy
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from django.db.models.fields.files import FieldFile
from .models import GrupoEquivalencia, Curso

logger = logging.getLogger(__name__)


MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'

_TRANSFORMER_MODEL = None
_NLP_MODEL = None


def get_transformer_model():
    global _TRANSFORMER_MODEL
    if _TRANSFORMER_MODEL is None:
        logger.info(f"Cargando modelo IA {MODEL_NAME} en memoria...")
        try:
            _TRANSFORMER_MODEL = SentenceTransformer(MODEL_NAME)
            logger.info("Modelo IA cargado correctamente.")
        except Exception as e:
            logger.error(f"Error cargando modelo IA: {e}")
            return None
    return _TRANSFORMER_MODEL


def get_nlp_model():
    global _NLP_MODEL
    if _NLP_MODEL is None:
        logger.info("Cargando modelo Spacy...")
        try:
            _NLP_MODEL = spacy.load("es_core_news_sm", disable=["parser", "ner"])
            logger.info("Modelo Spacy cargado.")
        except Exception as e:
            logger.error(f"Error cargando Spacy: {e}")
            return None
    return _NLP_MODEL


def leer_pdf_agnostico(archivo_o_ruta):
    texto = ""
    try:
        reader = None

        # archivo ya guardado en S3
        if isinstance(archivo_o_ruta, FieldFile):
            try:
                with archivo_o_ruta.open('rb') as f:
                    reader = PdfReader(f)
                    for page in reader.pages:
                        t = page.extract_text()
                        if t: texto += t + "\n"
            except Exception as e:
                logger.error(f"Error abriendo FieldFile: {e}")
                return ""
        else:
            stream_trabajo = None
            if hasattr(archivo_o_ruta, 'read'):

                if hasattr(archivo_o_ruta, 'seek'):
                    archivo_o_ruta.seek(0)
                content = archivo_o_ruta.read()
                if hasattr(archivo_o_ruta, 'seek'):
                    archivo_o_ruta.seek(0)

                stream_trabajo = io.BytesIO(content)

            elif isinstance(archivo_o_ruta, str):
                stream_trabajo = archivo_o_ruta

            if stream_trabajo:
                reader = PdfReader(stream_trabajo)
                for page in reader.pages:
                    t = page.extract_text()
                    if t: texto += t + "\n"

    except Exception as e:
        logger.error(f"Error general leyendo PDF: {e}")
        if hasattr(archivo_o_ruta, 'seek'):
            try:
                archivo_o_ruta.seek(0)
            except:
                pass
        return ""

    return texto


def limpiar_texto_para_tokens(texto):
    nlp = get_nlp_model()
    if not texto or not nlp: return set()

    texto = re.sub(r'[^a-záéíóúüñA-ZÁÉÍÓÚÜÑ\s]', '', texto.lower())

    if len(texto) > 500000: texto = texto[:500000]

    doc = nlp(texto)

    tokens = set()
    stopwords_extra = {'unidad', 'capitulo', 'tema', 'semana', 'clase', 'docente', 'alumno', 'hora', 'teoria',
                       'practica'}

    for token in doc:
        if not token.is_stop and not token.is_punct and len(token.text) > 2:
            lemma = token.lemma_.lower()
            if lemma not in stopwords_extra:
                tokens.add(lemma)

    return tokens


def extraer_solo_contenido_tematico(texto_raw):
    texto = texto_raw.replace('\r\n', '\n')

    starts = [r"(?:CONTENIDO)\s+TEM[ÁA]TICO", r"CONTENIDO"]
    ends = [
        r"6\.\s*PROGRAMACI[ÓO]N\s+DE\s+ACTIVIDADES\s+DE\s+INVESTIG\.\s+FORMATIVA\s+Y\s+RESPONSABILIDAD\s+SOCIAL",
        r"\d+\.\s*ESTRATEGIAS\s+DE\s+ENSEÑANZA",
        r"\d+\.\s*ESTRATEGIAS\s+DE\s+ENSEÑANZA\s+APRENDIZAJE"
    ]

    start_pattern = f"(?i)(?:{'|'.join(starts)})"
    end_pattern = f"(?i)(?:{'|'.join(ends)})"

    match_start = re.search(start_pattern, texto)
    if not match_start:
        return texto if len(texto) < 2000 else texto[:2000]

    idx_inicio = match_start.end()
    texto_desde_inicio = texto[idx_inicio:]

    match_end = re.search(end_pattern, texto_desde_inicio)

    if match_end:
        return texto_desde_inicio[:match_end.start()].strip()

    return texto_desde_inicio[:3000].strip()


def validar_es_silabo_unsa(texto):
    if not texto: return False
    texto_lower = texto.lower()

    keywords_alta_probabilidad = [
        "universidad nacional de san agustín", "información académica",
        "competencias", "contenido tematico", "contenido temático",
        "estrategias de evaluación", "bibliografía", "cronograma académico"
    ]
    keywords_contexto = [
        "silabo", "sílabo", "asignatura", "créditos", "creditos",
        "docente", "escuela profesional", "semestre", "prerrequisitos"
    ]

    score = 0
    for kw in keywords_alta_probabilidad:
        if kw in texto_lower: score += 2
    for kw in keywords_contexto:
        if kw in texto_lower: score += 1

    return score >= 6


def extraer_datos_inteligente(path_o_archivo):
    resultado = {
        'creditos': 0, 'contenido_raw': '',
        'valido': False, 'es_silabo': False, 'mensaje_error': ''
    }

    texto_raw = leer_pdf_agnostico(path_o_archivo)

    if len(texto_raw.strip()) < 100:
        if not texto_raw:
            resultado['mensaje_error'] = "El archivo está dañado o no es un PDF válido."
        else:
            resultado['mensaje_error'] = "Por favor sube el archivo digital original (texto ilegible)."
        return resultado

    if not validar_es_silabo_unsa(texto_raw):
        resultado['mensaje_error'] = "El documento NO parece ser un sílabo oficial de la universidad."
        resultado['valido'] = True
        return resultado

    resultado['valido'] = True
    resultado['es_silabo'] = True

    match_cred = re.search(r'(?i)crédito.*?\s*[:\.]?\s*(\d)', texto_raw)
    if match_cred:
        resultado['creditos'] = int(match_cred.group(1))

    resultado['contenido_raw'] = extraer_solo_contenido_tematico(texto_raw)

    return resultado


def generar_embedding(texto):
    model = get_transformer_model()
    if not model or not texto: return []

    t = re.sub(r'\s+', ' ', texto.lower().replace('\n', ' ')).strip()
    return model.encode(t[:2000]).tolist()


def calcular_centroide_grupo(grupo):
    cursos = grupo.instancias_curso.filter(embedding_vector__isnull=False)
    if not cursos.exists(): return None
    vectores = [np.array(c.embedding_vector) for c in cursos]
    return np.mean(vectores, axis=0)


def calcular_jaccard(tokens1, tokens2):
    if not tokens1 or not tokens2: return 0.0
    interseccion = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    return interseccion / union


def procesar_y_agrupar_curso(curso):
    logger.info(f"--- [CELERY] Iniciando análisis para curso: {curso.nombre} ---")

    texto_a_procesar = curso.contenido_cache

    if not texto_a_procesar:
        logger.info(f"Cache vacío para curso {curso.nombre}. Intentando leer fuente...")
        try:
            datos = extraer_datos_inteligente(curso.syllabus)

            if datos['es_silabo']:
                texto_a_procesar = datos['contenido_raw']
                if datos['creditos'] > 0:
                    curso.creditos = datos['creditos']
                curso.contenido_cache = texto_a_procesar
            else:
                logger.warning(f"Fallo al re-procesar PDF: {datos.get('mensaje_error')}")
                return False

        except Exception as e:
            logger.error(f"Error crítico leyendo PDF: {e}")
            return False

    if not curso.embedding_vector:
        curso.embedding_vector = generar_embedding(texto_a_procesar)

    tokens_curso_nuevo = limpiar_texto_para_tokens(curso.contenido_cache)
    curso.save()

    if not get_transformer_model():
        crear_grupo_nuevo(curso)
        return False

    posibles_grupos = GrupoEquivalencia.objects.filter(
        instancias_curso__creditos=curso.creditos
    ).distinct()

    mejor_grupo = None
    mejor_score_hibrido = 0.0

    vec_nuevo = np.array(curso.embedding_vector).reshape(1, -1)

    logger.info(f"Analizando curso: {curso.nombre} contra {posibles_grupos.count()} grupos.")

    for grupo in posibles_grupos:
        centroide = calcular_centroide_grupo(grupo)
        if centroide is None: continue

        vec_grupo = centroide.reshape(1, -1)
        score_ia = cosine_similarity(vec_nuevo, vec_grupo)[0][0]

        max_jaccard = 0.0
        cursos_grupo = grupo.instancias_curso.exclude(id=curso.id).only('contenido_cache')

        for c_existente in cursos_grupo:
            tokens_existente = limpiar_texto_para_tokens(c_existente.contenido_cache)
            j = calcular_jaccard(tokens_curso_nuevo, tokens_existente)
            if j > max_jaccard:
                max_jaccard = j

        es_compatible = False
        if score_ia > 0.82 and max_jaccard > 0.35:
            es_compatible = True
        elif score_ia > 0.92 and max_jaccard > 0.20:
            es_compatible = True

        if es_compatible:
            score_final = (score_ia * 0.70) + (max_jaccard * 0.30)
            if score_final > mejor_score_hibrido:
                mejor_score_hibrido = score_final
                mejor_grupo = grupo

    if mejor_grupo and mejor_score_hibrido > 0.65:
        logger.info(f"MATCH: Asignado a '{mejor_grupo.nombre}' (Score: {mejor_score_hibrido:.2f})")
        curso.grupo_equivalencia = mejor_grupo
        mejor_grupo.escuelas.add(curso.escuela)
        curso.save()
        return True
    else:
        logger.info(f"SIN MATCH SUFICIENTE. Creando nuevo grupo.")
        crear_grupo_nuevo(curso)
        return False


def crear_grupo_nuevo(curso):
    g = GrupoEquivalencia.objects.create(
        nombre=curso.nombre,
        descripcion=f"Grupo base generado por {curso.codigo_curso or 'sistema'}"
    )
    g.escuelas.add(curso.escuela)
    curso.grupo_equivalencia = g
    curso.save()
