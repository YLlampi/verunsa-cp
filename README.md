# VerUNSA

**VerUNSA** es una plataforma integral diseñada para la gestión inteligente, propuesta y apertura de cursos universitarios en la **Universidad Nacional de San Agustín (UNSA)**.

El sistema empodera a los estudiantes permitiéndoles organizarse para alcanzar las metas de inscritos ("firmas") necesarias para abrir cursos de verano, aplazados o dirigidos, mientras automatiza la validación académica mediante **Inteligencia Artificial**.

## Motor de Inteligencia Artificial ("Cerebro")

VerUNSA no es solo un CRUD; integra un **motor de análisis semántico** que corre localmente para entender el contenido de los cursos.

### 1. Análisis Inteligente de Sílabos
*   **Extracción de Texto**: Utiliza `pypdf` para leer documentos PDF subidos por los estudiantes.
*   **Validación Estructural**: Algoritmo heurístico que verifica si el documento es realmente un sílabo oficial de la UNSA (busca palabras clave como "Competencias", "Bibliografía", "Escuela Profesional").
*   **Segmentación de Contenido**: Detecta y extrae automáticamente secciones críticas como "Contenido Temático" y el número de créditos, ignorando secciones administrativas irrelevantes.

### 2. Agrupación Automática (Equivalencias)
El sistema determina automáticamente si un curso propuesto es **equivalente** a otros ya existentes (incluso de otras escuelas), facilitando la convalidación.
*   **Embeddings Vectoriales**: Genera vectores densos usando el modelo `paraphrase-multilingual-MiniLM-L12-v2` (`sentence-transformers`), capaz de entender el significado semántico del texto en español.
*   **Similitud Híbrida**: Combina dos métricas para máxima precisión:
    *   **Similitud Coseno (Semántica)**: Compara el significado general del contenido.
    *   **Índice de Jaccard (Léxica)**: Compara la superposición de términos clave (tokens lemmatizados con `spacy`).
*   **Clustering Dinámico**: Si un curso nuevo tiene alta similitud (>82-92%) con el "centroide" de un grupo existente, se agrupa automáticamente. Si no, crea un nuevo grupo de equivalencia.

---

## Características Principales

*   **Autenticación Institucional Robustecida**:
    *   Login exclusivo con correos `@unsa.edu.pe` (Google OAuth2).
    *   Validación de identidad universitaria.
*   **Ciclo de Vida del Curso**:
    *   **Propuesta**: Creación de iniciativas por estudiantes.
    *   **Recolección de Firmas**: Sistema de adhesión digital.
    *   **Metas Dinámicas**: Tracking en tiempo real del progreso (ej. 15 alumnos).
    *   **Transiciones de Estado**: Flujo automático `Propuesto` → `Meta Alcanzada` → `En Trámite` → `Aprobado`.
*   **Gestión Documental**:
    *   Validación de tipo y peso de archivos (PDF, máx 3MB).
    *   Almacenamiento organizado de requisitos.

## Stack Tecnológico

### Backend & AI
*   **Core**: Python 3.10+, Django 4.x
*   **IA/NLP**:
    *   `sentence-transformers` (Embeddings)
    *   `spacy` (Procesamiento de Lenguaje Natural)
    *   `scikit-learn` (Cálculo de similitudes)
    *   `numpy` (Operaciones vectoriales)
*   **PDF Processing**: `pypdf`

### Infraestructura & Datos
*   **Base de Datos**: PostgreSQL (Producción) / SQLite (Dev)
*   **Contenedores**: Docker & Docker Compose
*   **Colas de Tareas** (Opcional/Futuro): Preparado para Celery (análisis asíncrono).

### Frontend
*   **Templates**: Django Templates (HTML5/CSS3)
*   **Estilos**: Custom CSS (Diseño responsive y limpio).

## Estructura del Proyecto

*   `apps/`
    *   `users`: Gestión de usuarios, roles (Estudiante, Delegado) y estructura universitaria (Escuelas, Facultades).
    *   `courses`: Lógica de negocio, modelos de IA (`services.py`), y gestión de estados.
    *   `frontend`: Vistas y controladores de la interfaz de usuario.
*   `verunsa/`: Configuración global del proyecto.
*   `media/`: Almacenamiento de sílabos y documentos (gestionado por `.gitignore`).

## Instalación y Despliegue

### Opción A: Docker (Recomendado)

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/YLlampi/verunsa-cp.git
    cd verunsa-cp
    ```

2.  **Variables de Entorno**:
    Crea un archivo `.env` basado en el ejemplo:
    ```env
    DEBUG=1
    SECRET_KEY=tu_clave_secreta
    ALLOWED_HOSTS=localhost,127.0.0.1
    # Base de datos
    DATABASE_URL=postgres://user:password@db:5432/verunsa
    ```

3.  **Iniciar Servicios**:
    La primera vez tomará unos minutos mientras descarga los modelos de IA (aprox. 500MB).
    ```bash
    docker-compose up --build
    ```

### Opción B: Entorno Virtual (Local)

1.  Crear entorno:
    ```bash
    python -m venv .venv
    # Windows: .venv\Scripts\activate
    # Linux/Mac: source .venv/bin/activate
    ```

2.  Instalar dependencias (incluye librerías de IA):
    ```bash
    pip install -r requirements.txt
    python -m spacy download es_core_news_sm
    ```

3.  Migraciones y Usuario:
    ```bash
    python manage.py migrate
    python manage.py createsuperuser
    ```

4.  Ejecutar:
    ```bash
    python manage.py runserver
    ```

5.  **Acceso**: [http://localhost:8000](http://localhost:8000)

## Contribución

¡Tu ayuda es bienvenida para mejorar la educación en la UNSA!

1.  Haz un Fork.
2.  Crea tu rama (`git checkout -b feature/AmazingFeature`).
3.  Commit (`git commit -m 'Add some AmazingFeature'`).
4.  Push (`git push origin feature/AmazingFeature`).
5.  Abre un Pull Request.

## 📄 Licencia

MIT - verUNSA
