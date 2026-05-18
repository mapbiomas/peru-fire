"""
Idioma da Interface do Usuario (UI)
MapBiomas Fire Monitor Pipeline

Todos os textos de UI devem vir da classe L abaixo.
Textos tecnicos (print/log/raise no backend) devem ser em ingles puro, SEM usar L.

Para adicionar um novo idioma no futuro:
    STRINGS_EN = { 'LOADING': 'Loading...', ... }
    L.load_locale(STRINGS_EN)
"""


class L:
    """Atributos de classe resolvidos em runtime — troque o valor e toda UI reflete."""

    # ── Gerais ──────────────────────────────────────────────
    LOADING = "Cargando..."
    PROCESSING = "Procesando..."
    DELETING = "Eliminando..."
    SAVING = "Guardando..."
    SYNCING = "Sincronizando..."
    SEARCHING = "Buscando..."
    DONE = "Hecho"
    ERROR = "Error"
    SUCCESS = "Exito"
    WARNING = "Atencion"
    INFO = "Informacion"
    ALL = "Todos"
    ALL_F = "Todas"
    NONE = "Ninguno"
    BACK = "Voltar"
    OK = "OK"
    CONFIRM = "Confirmar"
    CANCEL = "Cancelar"
    SAVE = "Guardar"
    DELETE = "Eliminar"
    SYNC = "Sincronizar"
    SEARCH = "Buscar"
    CLEAR = "Limpiar"
    REFRESH = "Actualizar"
    APPLY = "Aplicar"
    CLOSE = "Cerrar"
    MODEL = "Modelo"
    REGION = "Region"
    YEAR = "Anio"
    PERIOD = "Periodo"
    TASK = "Tarea"
    TASK_NAME = "Nombre Tarea"
    STATUS = "Estado"
    PROGRESS = "Progreso"
    DESCRIPTION = "Descripcion"
    NAME = "Nombre"
    DATE = "Fecha"
    ID = "ID"

    # ── Estados vazios ──────────────────────────────────────
    NO_DATA = "No hay datos disponibles."
    NO_RESULTS = "No se encontraron resultados."
    NO_TASKS = "No hay tareas pendientes."
    NO_TASKS_PUBLISH = "Ninguna tarea lista para publicar."
    NO_TASKS_DONE = "Ninguna tarea finalizada aun."
    NO_TILES_GCS = "Ningun tile en GCS."
    NO_MAP = "No se pudo generar el mapa. Verifique conexion GEE."
    NO_SELECTION = "Ninguna opcion seleccionada."
    NO_SAMPLES = "No se encontraron muestras con este filtro."
    NO_COGS = "No se encontraron COGs en el repositorio GCS."

    # ── Widgets / Botoes M5 ────────────────────────────────
    ADD_BATCH = "Agregar Lote a la Cola"
    REFRESH_VIEW = "Actualizar Vista"
    LOAD_TO_QUEUE = "Cargar a la Cola"
    CLEAR_TEMP_TASKS = "Limpiar Tareas Temporales"
    SAVE_TASK_GCS = "Guardar Tarea GCS"
    EXCLUDE_TASK_GCS = "Excluir Tarea GCS"
    DELETE_MODEL = "Eliminar Modelo"
    DELETE_REGION = "Eliminar Region"
    DELETE_SELECTED = "Eliminar Seleccionados"
    DELETE_ALL = "Eliminar Todos"
    DELETE_JOB = "Eliminar Todo"
    VIEW_TILES = "Ver Tiles"
    HIDE_TILES = "Ocultar"
    REFRESH_MAP = "Actualizar Mapa"
    TASK_NAME_PLACEHOLDER = "Ej: Clasificar Amazonia Baja 2025 (Lucas)"

    # ── Abas M5 ────────────────────────────────────────────
    TAB_GUIDE = "Guia"
    TAB_REGISTER = "Registrar"
    TAB_PENDING = "Pendientes"
    TAB_PUBLISH = "Para Publicar"
    TAB_MAP = "Mapa"
    TAB_DONE = "Finalizadas"

    # ── Mapa / Grid ─────────────────────────────────────────
    LIVE_PROCESSING = "Procesando en vivo"
    CURRENT_TILE = "Tile actual"
    COMPLETED = "Completados"
    GRID_REGION = "Region"
    GRID_CELLS = "Celdas cim-world"

    # ── Tiles / GCS ─────────────────────────────────────────
    TILES = "tiles"
    MOSAIC = "mosaico"
    STATS = "stats"
    SELECT_TILES_DELETE = "Seleccione tiles para eliminar."
    TILES_REMOVED = "tiles eliminados."

    # ── Status das tarefas ─────────────────────────────────
    STATUS_QUEUED = "En cola"
    STATUS_RUNNING = "Ejecutando"
    STATUS_COMPLETED = "Completado"
    STATUS_FINISHED = "Finalizado"
    STATUS_ERROR = "Error"
    STATUS_PUBLISHING = "Publicando"
    STATUS_PUBLISHED = "Publicado"
    STATUS_SKIPPED = "Omitido"

    # ── M4 - Treinamento ───────────────────────────────────
    MODEL_TRAINER = "Entrenador del Modelo"
    ITERATIONS = "Iteraciones"
    BATCH_SIZE = "Tamano de Lote"
    LEARNING_RATE = "Tasa de Aprendizaje"
    HIDDEN_LAYERS = "Capas Ocultas"
    ACTIVATION = "Activacion"
    DROPOUT = "Dropout"
    OPTIMIZER = "Optimizador"
    LOSS_FN = "Funcion de Perdida"
    METRICS = "Metricas"
    SAMPLE_SELECTION = "Seleccion de Muestras"
    EXTRACTION_MATRIX = "Matriz de Extraccion"
    MODEL_CONFIG = "Configuracion del Modelo"
    GCS_DEST = "Destino GCS"
    USAGE_GUIDE = "Guia de Uso"

    # ── M4 - Canvas ────────────────────────────────────────
    METADATA = "Metadatos"
    KPIS = "KPIs"
    CONFUSION = "Confusion"
    HISTORY = "Historial"
    PROB = "Prob"
    PR_CURVE = "PR-Curve"
    MANAGEMENT = "Gestion"
    RANKING = "Ranking / Repositorio"
    SELECTED_CANVAS = "Seleccionados en Canvas"
    SEARCH_REPO = "Buscar en repositorio..."
    SEARCH_SAMPLES = "Buscar muestras..."
    SYNC_CATALOG = "Sincronizar Catalogo (GCS)"
    APPLY_VISIBILITY = "Aplicar Visibilidad"

    # ── M1 / M2 - Exportacao / Mosaico ─────────────────────
    SYNC_DATA = "Sincronizar Datos"
    SELECT_PENDING = "Seleccionar Pendientes"
    CLEAR_SELECTION = "Limpiar Seleccion"
    EXPORT_START = "Iniciar Exportacion"
    MOSAIC_START = "Iniciar Montaje"

    # ── M6 - Pos-classificacao ─────────────────────────────
    POST_CLASSIFICATION = "Procesador Post-Clasificacion"
    USING_PRESET = "Usando Configuracion Preset"
    FILTER_START = "Iniciar Filtrado"
    EXPORT_TASK_STARTED = "Tarea exportacion iniciada"
    CONFIG_SUMMARY = "Resumen de Configuracion Usada"

    # ── M7 - Curador ───────────────────────────────────────
    CURATOR = "Curador"
    CURATOR_DESC = "Publicacion de Coleccion Pre-Oficial"
    USING_VOTES_PRESET = "Usando Votacion Preset"
    CURATION_START = "Iniciar Curaduria"
    EXPORT_ASSET_STARTED = "Exportacion GEE Asset iniciada"

    # ── Cache ──────────────────────────────────────────────
    CACHE_REMOVED = "Cache local removido"
    CACHE_NOT_FOUND = "Cache no encontrado"

    # ── Etc ────────────────────────────────────────────────
    LOADING_TILES = "Cargando tiles..."
    CONFIRM_DELETE = "Confirmar Eliminacion"
    CONFIRM_DELETE_ALL = "Confirmar Eliminacion Total"
    CANCELED = "Cancelado."
    GLOBAL_OPTS_SET = "Opciones globales configuradas"

    @classmethod
    def load_locale(cls, locale="es"):
        """Troca todos os atributos para o idioma indicado.
        
        No futuro, aceitar 'en' e carregar STRINGS_EN:
        strings = {'LOADING': 'Loading...', ...}
        for k, v in strings.items():
            setattr(cls, k, v)
        """
        if locale == "es":
            return  # ja eh o padrao
        raise ValueError(f"Idioma '{locale}' ainda nao implementado.")
