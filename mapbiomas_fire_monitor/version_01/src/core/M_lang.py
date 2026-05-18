"""
Interface Language (UI)
MapBiomas Fire Monitor Pipeline

All UI-facing strings must come from class L below.
Tech messages (print/log/raise) must be in plain English, WITHOUT using L.

To add a new language:
  1. Add a `STRINGS_XX` dict below
  2. Add the locale code to `SUPPORTED_LOCALES`
  3. Call `L.load_locale('xx')` at startup
"""


class L:
    """Class attributes resolved at runtime — change values and the whole UI reflects."""

    # Default language is English
    # ── General ───────────────────────────────────────────
    LOADING = "Loading..."
    PROCESSING = "Processing..."
    DELETING = "Deleting..."
    SAVING = "Saving..."
    SYNCING = "Syncing..."
    SEARCHING = "Searching..."
    DONE = "Done"
    ERROR = "Error"
    SUCCESS = "Success"
    WARNING = "Warning"
    INFO = "Info"
    ALL = "All"
    ALL_F = "All"
    NONE = "None"
    BACK = "Back"
    OK = "OK"
    CONFIRM = "Confirm"
    CANCEL = "Cancel"
    SAVE = "Save"
    DELETE = "Delete"
    SYNC = "Sync"
    SEARCH = "Search"
    CLEAR = "Clear"
    REFRESH = "Refresh"
    APPLY = "Apply"
    CLOSE = "Close"
    MODEL = "Model"
    REGION = "Region"
    YEAR = "Year"
    PERIOD = "Period"
    TASK = "Task"
    TASK_NAME = "Task Name"
    STATUS = "Status"
    PROGRESS = "Progress"
    DESCRIPTION = "Description"
    NAME = "Name"
    DATE = "Date"
    ID = "ID"

    # ── Empty states ─────────────────────────────────────
    NO_DATA = "No data available."
    NO_RESULTS = "No results found."
    NO_TASKS = "No pending tasks."
    NO_TASKS_PUBLISH = "No tasks ready to publish."
    NO_TASKS_DONE = "No finished tasks yet."
    NO_TILES_GCS = "No tiles in GCS."
    NO_MAP = "Could not generate map. Check GEE connection."
    NO_SELECTION = "No option selected."
    NO_SAMPLES = "No samples found with this filter."
    NO_COGS = "No COGs found in the GCS repository."

    # ── Widgets / Buttons M5 ─────────────────────────────
    ADD_BATCH = "Add Batch to Queue"
    REFRESH_VIEW = "Refresh View"
    LOAD_TO_QUEUE = "Load to Queue"
    CLEAR_TEMP_TASKS = "Clear Temporary Tasks"
    SAVE_TASK_GCS = "Save Task GCS"
    EXCLUDE_TASK_GCS = "Exclude Task GCS"
    DELETE_MODEL = "Delete Model"
    DELETE_REGION = "Delete Region"
    DELETE_SELECTED = "Delete Selected"
    DELETE_ALL = "Delete All"
    DELETE_JOB = "Delete All"
    VIEW_TILES = "View Tiles"
    HIDE_TILES = "Hide"
    REFRESH_MAP = "Refresh Map"
    TASK_NAME_PLACEHOLDER = "e.g.: Classify Low Amazon 2025 (Lucas)"

    # ── M5 Tabs ──────────────────────────────────────────
    TAB_GUIDE = "Guide"
    TAB_REGISTER = "Register"
    TAB_PENDING = "Pending"
    TAB_PUBLISH = "To Publish"
    TAB_MAP = "Map"
    TAB_DONE = "Finished"

    # ── Map / Grid ───────────────────────────────────────
    LIVE_PROCESSING = "Live Processing"
    CURRENT_TILE = "Current tile"
    COMPLETED = "Completed"
    GRID_REGION = "Region"
    GRID_CELLS = "cim-world cells"

    # ── Tiles / GCS ──────────────────────────────────────
    TILES = "tiles"
    MOSAIC = "mosaic"
    STATS = "stats"
    SELECT_TILES_DELETE = "Select tiles to delete."
    TILES_REMOVED = "tiles removed."

    # ── Task status ──────────────────────────────────────
    STATUS_QUEUED = "Queued"
    STATUS_RUNNING = "Running"
    STATUS_COMPLETED = "Completed"
    STATUS_FINISHED = "Finished"
    STATUS_ERROR = "Error"
    STATUS_PUBLISHING = "Publishing"
    STATUS_PUBLISHED = "Published"
    STATUS_SKIPPED = "Skipped"

    # ── M4 - Training ────────────────────────────────────
    MODEL_TRAINER = "Model Trainer"
    ITERATIONS = "Iterations"
    BATCH_SIZE = "Batch Size"
    LEARNING_RATE = "Learning Rate"
    HIDDEN_LAYERS = "Hidden Layers"
    ACTIVATION = "Activation"
    DROPOUT = "Dropout"
    OPTIMIZER = "Optimizer"
    LOSS_FN = "Loss Function"
    METRICS = "Metrics"
    SAMPLE_SELECTION = "Sample Selection"
    EXTRACTION_MATRIX = "Extraction Matrix"
    MODEL_CONFIG = "Model Configuration"
    GCS_DEST = "GCS Destination"
    USAGE_GUIDE = "Usage Guide"

    # ── M4 - Canvas ──────────────────────────────────────
    METADATA = "Metadata"
    KPIS = "KPIs"
    CONFUSION = "Confusion"
    HISTORY = "History"
    PROB = "Prob"
    PR_CURVE = "PR-Curve"
    MANAGEMENT = "Management"
    RANKING = "Ranking / Repository"
    SELECTED_CANVAS = "Selected in Canvas"
    SEARCH_REPO = "Search repository..."
    SEARCH_SAMPLES = "Search samples..."
    SYNC_CATALOG = "Sync Catalog (GCS)"
    APPLY_VISIBILITY = "Apply Visibility"

    # ── M1 / M2 - Export / Mosaic ────────────────────────
    SYNC_DATA = "Sync Data"
    SELECT_PENDING = "Select Pending"
    CLEAR_SELECTION = "Clear Selection"
    EXPORT_START = "Start Export"
    MOSAIC_START = "Start Assembly"

    # ── M6 - Post-classification ─────────────────────────
    POST_CLASSIFICATION = "Post-Classification Processor"
    USING_PRESET = "Using Preset Configuration"
    FILTER_START = "Start Filtering"
    EXPORT_TASK_STARTED = "Export task started"
    CONFIG_SUMMARY = "Configuration Summary"

    # ── M7 - Curator ─────────────────────────────────────
    CURATOR = "Curator"
    CURATOR_DESC = "Pre-Official Collection Publication"
    USING_VOTES_PRESET = "Using Preset Votes"
    CURATION_START = "Start Curation"
    EXPORT_ASSET_STARTED = "GEE Asset export started"

    # ── Cache ────────────────────────────────────────────
    CACHE_REMOVED = "Local cache removed"
    CACHE_NOT_FOUND = "Cache not found"

    # ── Misc ─────────────────────────────────────────────
    LOADING_TILES = "Loading tiles..."
    LOADING_INTERFACE = "Loading interface..."
    CLICK_TO_LOAD = "Click to load {sensor} {period} ({mosaic})..."
    LOADING_CACHE = "Loading cache..."
    SYNCING_TASKS = "Syncing GEE tasks..."
    FILTERING = "Filtering..."
    CONFIRM_DELETE = "Confirm Deletion"
    CONFIRM_DELETE_ALL = "Confirm Delete All"
    CANCELED = "Canceled."
    GLOBAL_OPTS_SET = "Global options set"

    # ── Dropdown labels ─────────────────────────────────
    DROP_MODEL = "Model:"
    DROP_REGION = "Region:"
    DROP_YEAR = "Year:"
    DROP_TASK = "Task:"
    DROP_TASK_NAME = "Task Name:"

    # ── M4 - Hyperparams ────────────────────────────────
    HP_EPOCHS = "Epochs"
    HP_PATIENCE = "Patience"
    HP_TEST_SPLIT = "Test Split"
    HP_BALANCE = "Balance"
    HP_AUGMENT = "Data Augmentation"
    HP_ACTIVATION = "Activation Function"
    HP_OPTIMIZER = "Optimizer"
    HP_LOSS = "Loss Function"

    # ── M4 - Extraction ─────────────────────────────────
    EXTRACTION_TITLE = "Extraction Matrix (Multisensor GCS)"
    SAMPLE_SELECT = "Sample Selection"
    AVAILABLE = "Available"
    SELECTED = "Selected"
    ADD = "Add"
    REMOVE = "Remove"
    CAMPAIGN = "Campaign"
    SENSOR = "Sensor"
    BANDS = "Bands"
    STATUS_OK = "OK"
    STATUS_RUN = "Run"
    STATUS_MISS = "Miss"

    # ── M4 - Training ───────────────────────────────────
    TRAINING_ID = "Training ID:"
    SHORTNAME = "Short Name:"
    COMMENTS = "Comments..."
    START_TRAINING = "Start Training"
    CANVAS_TITLE = "Training and Audit Center"
    CANVAS_EMPTY = "Empty canvas"
    CANVAS_HINT = "Browse and select models in the side panel to visualize them here."
    LOSS_ACC = "Loss / Accuracy"
    VIZ_METADATA = "Metadata"
    VIZ_KPIS = "KPIs"
    VIZ_CONFUSION = "Confusion"
    VIZ_HISTORY = "History"
    VIZ_PROB = "Prob"
    VIZ_PR_CURVE = "PR-Curve"
    VIZ_MANAGEMENT = "Management"

    # ── M4 - Repository ─────────────────────────────────
    REPO_TITLE = "Ranking / Repository"
    REPO_SEARCH = "Search repository..."
    REPO_SYNC = "Sync GCS"
    REPO_ALL = "All"
    REPO_CLEAR = "Clear"
    REPO_SYNC_CATALOG = "Sync Catalog (GCS)"
    REPO_SCANNING = "Scanning GCS... Please wait."
    REPO_SCAN_DONE = "Catalog synced!"

    # ── M4 - Tab titles ─────────────────────────────────
    SORT_BY = "Sort by:"
    NEW_TRAINING = "New Training"
    TRAININGS = "Trainings"

    # ── M1 - Export ─────────────────────────────────────
    EXPORT_TITLE = "Collection Export"
    EXPORT_SYNC = "Sync Data"
    EXPORT_SELECT = "Select Pending"
    EXPORT_CLEAR = "Clear Selection"
    EXPORT_START_BTN = "Start Export"
    EXPORT_SENT = "tasks sent."
    EXPORT_NONE_SEL = "No option selected for export."

    # ── M2 - Mosaic ─────────────────────────────────────
    MOSAIC_TITLE = "Mosaic Assembly"
    MOSAIC_SYNC = "Sync Data"
    MOSAIC_SELECT = "Select Pending"
    MOSAIC_CLEAR = "Clear Selection"
    MOSAIC_START_BTN = "Start Assembly"
    MOSAIC_DONE = "Assembly completed successfully"

    # ── M0 - Startup ────────────────────────────────────
    START_COUNTRY = "Country"
    START_BUCKET = "Bucket"
    START_VERSION = "Version"
    START_SENSOR = "Sensor"
    START_PERIODICITY = "Periodicity"
    START_CAMPAIGN = "Campaign"
    START_FOUND = "found"
    START_NOT_FOUND = "not found"
    START_GDAL_OK = "GDAL found and added to PATH"
    START_GDAL_MISSING = "Warning: GDAL utilities not found"
    START_COLAB_HINT = "On Google Colab, run: !apt-get install -y gdal-bin"
    START_WIN_HINT = "On Windows, ensure GDAL is in your PATH"

    # ── M6 - Post-classification ────────────────────────
    M6_TITLE = "Post-Classification Processor"
    M6_PRESET = "Using Preset Configuration"
    M6_DOWNLOAD = "Downloading fragments"
    M6_VRT = "Building VRT"
    M6_COG = "Converting to COG"
    M6_UPLOAD = "Uploaded"
    M6_START = "Starting Filtering"
    M6_EXPORT_OK = "Export task started"
    M6_SUMMARY = "Configuration Summary"

    # ── M7 - Curator ────────────────────────────────────
    M7_TITLE = "Curator"
    M7_DESC = "Pre-Official Collection Publication"
    M7_PRESET = "Using Preset Votes"
    M7_START = "Starting Curation"
    M7_EXPORT_OK = "GEE Asset export started for"
    M7_SUMMARY = "Configuration Summary"

    # ── M3 - Samples ────────────────────────────────────
    M3_TITLE = "M3 - Sample Collection (GEE Toolkit Gateway)"
    M3_SOURCE = "Source code (GitHub)"
    M3_EDITOR = "Direct access (GEE Editor)"
    M3_DOCS = "Documentation and usage guidelines"


# ── Locale dictionaries ────────────────────────────────────

STRINGS_ES = {
    # General
    "LOADING": "Cargando...",
    "PROCESSING": "Procesando...",
    "DELETING": "Eliminando...",
    "SAVING": "Guardando...",
    "SYNCING": "Sincronizando...",
    "SEARCHING": "Buscando...",
    "DONE": "Hecho",
    "ERROR": "Error",
    "SUCCESS": "Exito",
    "WARNING": "Atencion",
    "INFO": "Informacion",
    "ALL": "Todos",
    "ALL_F": "Todas",
    "NONE": "Ninguno",
    "BACK": "Voltar",
    "OK": "OK",
    "CONFIRM": "Confirmar",
    "CANCEL": "Cancelar",
    "SAVE": "Guardar",
    "DELETE": "Eliminar",
    "SYNC": "Sincronizar",
    "SEARCH": "Buscar",
    "CLEAR": "Limpiar",
    "REFRESH": "Actualizar",
    "APPLY": "Aplicar",
    "CLOSE": "Cerrar",
    "MODEL": "Modelo",
    "REGION": "Region",
    "YEAR": "Anio",
    "PERIOD": "Periodo",
    "TASK": "Tarea",
    "TASK_NAME": "Nombre Tarea",
    "STATUS": "Estado",
    "PROGRESS": "Progreso",
    "DESCRIPTION": "Descripcion",
    "NAME": "Nombre",
    "DATE": "Fecha",
    "ID": "ID",
    # Empty states
    "NO_DATA": "No hay datos disponibles.",
    "NO_RESULTS": "No se encontraron resultados.",
    "NO_TASKS": "No hay tareas pendientes.",
    "NO_TASKS_PUBLISH": "Ninguna tarea lista para publicar.",
    "NO_TASKS_DONE": "Ninguna tarea finalizada aun.",
    "NO_TILES_GCS": "Ningun tile en GCS.",
    "NO_MAP": "No se pudo generar el mapa. Verifique conexion GEE.",
    "NO_SELECTION": "Ninguna opcion seleccionada.",
    "NO_SAMPLES": "No se encontraron muestras con este filtro.",
    "NO_COGS": "No se encontraron COGs en el repositorio GCS.",
    # M5 Widgets
    "ADD_BATCH": "Agregar Lote a la Cola",
    "REFRESH_VIEW": "Actualizar Vista",
    "LOAD_TO_QUEUE": "Cargar a la Cola",
    "CLEAR_TEMP_TASKS": "Limpiar Tareas Temporales",
    "SAVE_TASK_GCS": "Guardar Tarea GCS",
    "EXCLUDE_TASK_GCS": "Excluir Tarea GCS",
    "DELETE_MODEL": "Eliminar Modelo",
    "DELETE_REGION": "Eliminar Region",
    "DELETE_SELECTED": "Eliminar Seleccionados",
    "DELETE_ALL": "Eliminar Todos",
    "DELETE_JOB": "Eliminar Todo",
    "VIEW_TILES": "Ver Tiles",
    "HIDE_TILES": "Ocultar",
    "REFRESH_MAP": "Actualizar Mapa",
    "TASK_NAME_PLACEHOLDER": "Ej: Clasificar Amazonia Baja 2025 (Lucas)",
    # M5 Tabs
    "TAB_GUIDE": "Guia",
    "TAB_REGISTER": "Registrar",
    "TAB_PENDING": "Pendientes",
    "TAB_PUBLISH": "Para Publicar",
    "TAB_MAP": "Mapa",
    "TAB_DONE": "Finalizadas",
    # Map / Grid
    "LIVE_PROCESSING": "Procesando en vivo",
    "CURRENT_TILE": "Tile actual",
    "COMPLETED": "Completados",
    "GRID_REGION": "Region",
    "GRID_CELLS": "Celdas cim-world",
    # Tiles / GCS
    "TILES": "tiles",
    "MOSAIC": "mosaico",
    "STATS": "stats",
    "SELECT_TILES_DELETE": "Seleccione tiles para eliminar.",
    "TILES_REMOVED": "tiles eliminados.",
    # Task status
    "STATUS_QUEUED": "En cola",
    "STATUS_RUNNING": "Ejecutando",
    "STATUS_COMPLETED": "Completado",
    "STATUS_FINISHED": "Finalizado",
    "STATUS_ERROR": "Error",
    "STATUS_PUBLISHING": "Publicando",
    "STATUS_PUBLISHED": "Publicado",
    "STATUS_SKIPPED": "Omitido",
    # M4 - Training
    "MODEL_TRAINER": "Entrenador del Modelo",
    "ITERATIONS": "Iteraciones",
    "BATCH_SIZE": "Tamano de Lote",
    "LEARNING_RATE": "Tasa de Aprendizaje",
    "HIDDEN_LAYERS": "Capas Ocultas",
    "ACTIVATION": "Activacion",
    "DROPOUT": "Dropout",
    "OPTIMIZER": "Optimizador",
    "LOSS_FN": "Funcion de Perdida",
    "METRICS": "Metricas",
    "SAMPLE_SELECTION": "Seleccion de Muestras",
    "EXTRACTION_MATRIX": "Matriz de Extraccion",
    "MODEL_CONFIG": "Configuracion del Modelo",
    "GCS_DEST": "Destino GCS",
    "USAGE_GUIDE": "Guia de Uso",
    # M4 - Canvas
    "METADATA": "Metadatos",
    "KPIS": "KPIs",
    "CONFUSION": "Confusion",
    "HISTORY": "Historial",
    "PROB": "Prob",
    "PR_CURVE": "PR-Curve",
    "MANAGEMENT": "Gestion",
    "RANKING": "Ranking / Repositorio",
    "SELECTED_CANVAS": "Seleccionados en Canvas",
    "SEARCH_REPO": "Buscar en repositorio...",
    "SEARCH_SAMPLES": "Buscar muestras...",
    "SYNC_CATALOG": "Sincronizar Catalogo (GCS)",
    "APPLY_VISIBILITY": "Aplicar Visibilidad",
    # M1 / M2
    "SYNC_DATA": "Sincronizar Datos",
    "SELECT_PENDING": "Seleccionar Pendientes",
    "CLEAR_SELECTION": "Limpiar Seleccion",
    "EXPORT_START": "Iniciar Exportacion",
    "MOSAIC_START": "Iniciar Montaje",
    # M6
    "POST_CLASSIFICATION": "Procesador Post-Clasificacion",
    "USING_PRESET": "Usando Configuracion Preset",
    "FILTER_START": "Iniciar Filtrado",
    "EXPORT_TASK_STARTED": "Tarea exportacion iniciada",
    "CONFIG_SUMMARY": "Resumen de Configuracion Usada",
    # M7
    "CURATOR": "Curador",
    "CURATOR_DESC": "Publicacion de Coleccion Pre-Oficial",
    "USING_VOTES_PRESET": "Usando Votacion Preset",
    "CURATION_START": "Iniciar Curaduria",
    "EXPORT_ASSET_STARTED": "Exportacion GEE Asset iniciada",
    # Cache
    "CACHE_REMOVED": "Cache local removido",
    "CACHE_NOT_FOUND": "Cache no encontrado",
    # Misc
    "LOADING_TILES": "Cargando tiles...",
    "CONFIRM_DELETE": "Confirmar Eliminacion",
    "CONFIRM_DELETE_ALL": "Confirmar Eliminacion Total",
    "CANCELED": "Cancelado.",
    "GLOBAL_OPTS_SET": "Opciones globales configuradas",
    # Dropdown labels
    "DROP_MODEL": "Modelo:",
    "DROP_REGION": "Region:",
    "DROP_YEAR": "Anio:",
    "DROP_TASK": "Tarea:",
    "DROP_TASK_NAME": "Nombre Tarea:",
    # Hyperparams
    "HP_EPOCHS": "Epocas",
    "HP_PATIENCE": "Paciencia",
    "HP_TEST_SPLIT": "Split de Test",
    "HP_BALANCE": "Balanceo",
    "HP_AUGMENT": "Aumento de Datos",
    "HP_ACTIVATION": "Funcion de Activacion",
    "HP_OPTIMIZER": "Optimizador",
    "HP_LOSS": "Funcion de Perdida",
    # Extraction
    "EXTRACTION_TITLE": "Matriz de Extraccion (Multisensor GCS)",
    "SAMPLE_SELECT": "Seleccion de Muestras",
    "AVAILABLE": "Disponibles",
    "SELECTED": "Seleccionados",
    "ADD": "Agregar",
    "REMOVE": "Remover",
    "CAMPAIGN": "Campana",
    "SENSOR": "Sensor",
    "BANDS": "Bandas",
    "STATUS_OK": "OK",
    "STATUS_RUN": "Ejec.",
    "STATUS_MISS": "Falt.",
    # Training
    "TRAINING_ID": "ID Training:",
    "SHORTNAME": "Nombre Rapido:",
    "COMMENTS": "Comentarios...",
    "START_TRAINING": "Iniciar Entrenamiento",
    "CANVAS_TITLE": "Centro de Treinamentos y Auditoria",
    "CANVAS_EMPTY": "Canvas vazio",
    "CANVAS_HINT": "Busque y seleccione modelos en el panel lateral para visualizarlos aqui.",
    "LOSS_ACC": "Loss / Accuracy",
    "VIZ_METADATA": "Metadatos",
    "VIZ_KPIS": "KPIs",
    "VIZ_CONFUSION": "Confusion",
    "VIZ_HISTORY": "Historial",
    "VIZ_PROB": "Prob",
    "VIZ_PR_CURVE": "PR-Curve",
    "VIZ_MANAGEMENT": "Gestion",
    # Repository
    "REPO_TITLE": "Ranking / Repositorio",
    "REPO_SEARCH": "Buscar en repositorio...",
    "REPO_SYNC": "Sincronizar GCS",
    "REPO_ALL": "Todos",
    "REPO_CLEAR": "Limpiar",
    "REPO_SYNC_CATALOG": "Sincronizar Catalogo (GCS)",
    "REPO_SCANNING": "Escaneando GCS... Aguarde.",
    "REPO_SCAN_DONE": "!Catalogo Sincronizado!",
    # Tab titles
    "SORT_BY": "Ordenar:",
    "NEW_TRAINING": "Novo Treinamento",
    "TRAININGS": "Treinamentos",
    # M1 - Export
    "EXPORT_TITLE": "Exportacion de Colecciones",
    "EXPORT_SYNC": "Sincronizar Datos",
    "EXPORT_SELECT": "Seleccionar Pendientes",
    "EXPORT_CLEAR": "Limpiar Seleccion",
    "EXPORT_START_BTN": "Iniciar Exportacion",
    "EXPORT_SENT": "tareas enviadas.",
    "EXPORT_NONE_SEL": "Ninguna opcion seleccionada para exportacion.",
    # M2 - Mosaic
    "MOSAIC_TITLE": "Montaje de Mosaicos",
    "MOSAIC_SYNC": "Sincronizar Datos",
    "MOSAIC_SELECT": "Seleccionar Pendientes",
    "MOSAIC_CLEAR": "Limpiar Seleccion",
    "MOSAIC_START_BTN": "Iniciar Montaje",
    "MOSAIC_DONE": "Montaje concluida con exito",
    # M0 - Startup
    "START_COUNTRY": "Pais",
    "START_BUCKET": "Bucket",
    "START_VERSION": "Version",
    "START_SENSOR": "Sensor",
    "START_PERIODICITY": "Periodicidad",
    "START_CAMPAIGN": "Campana",
    "START_FOUND": "encontrado",
    "START_NOT_FOUND": "no encontrado",
    "START_GDAL_OK": "GDAL encontrado y agregado al PATH",
    "START_GDAL_MISSING": "Aviso: Utilitarios GDAL no encontrados",
    "START_COLAB_HINT": "En Google Colab, ejecute: !apt-get install -y gdal-bin",
    "START_WIN_HINT": "En Windows, asegurese de que GDAL este en su PATH",
    # M6
    "M6_TITLE": "Procesador Post-Clasificacion",
    "M6_PRESET": "Usando Configuracion Preset",
    "M6_DOWNLOAD": "Descargando fragmentos",
    "M6_VRT": "Construyendo VRT",
    "M6_COG": "Convirtiendo a COG",
    "M6_UPLOAD": "Subido",
    "M6_START": "Iniciando Filtrado",
    "M6_EXPORT_OK": "Tarea exportacion iniciada",
    "M6_SUMMARY": "Resumen de Configuracion Usada",
    # M7
    "M7_TITLE": "Curador",
    "M7_DESC": "Publicacion de Coleccion Pre-Oficial",
    "M7_PRESET": "Usando Votacion Preset",
    "M7_START": "Iniciando Curaduria",
    "M7_EXPORT_OK": "Exportacion GEE Asset iniciada para",
    "M7_SUMMARY": "Resumen de Configuracion Usada",
    # M3
    "M3_TITLE": "M3 - Colecta de Muestras (GEE Toolkit Gateway)",
    "M3_SOURCE": "Acceso al codigo fuente (GitHub)",
    "M3_EDITOR": "Acceso directo (Editor GEE)",
    "M3_DOCS": "Documentacion y normas de uso",
}

STRINGS_PT = {
    # General
    "LOADING": "Carregando...",
    "PROCESSING": "Processando...",
    "DELETING": "Excluindo...",
    "SAVING": "Salvando...",
    "SYNCING": "Sincronizando...",
    "SEARCHING": "Buscando...",
    "DONE": "Feito",
    "ERROR": "Erro",
    "SUCCESS": "Sucesso",
    "WARNING": "Atencao",
    "INFO": "Informacao",
    "ALL": "Todos",
    "ALL_F": "Todas",
    "NONE": "Nenhum",
    "BACK": "Voltar",
    "OK": "OK",
    "CONFIRM": "Confirmar",
    "CANCEL": "Cancelar",
    "SAVE": "Salvar",
    "DELETE": "Excluir",
    "SYNC": "Sincronizar",
    "SEARCH": "Buscar",
    "CLEAR": "Limpar",
    "REFRESH": "Atualizar",
    "APPLY": "Aplicar",
    "CLOSE": "Fechar",
    "MODEL": "Modelo",
    "REGION": "Regiao",
    "YEAR": "Ano",
    "PERIOD": "Periodo",
    "TASK": "Tarefa",
    "TASK_NAME": "Nome Tarefa",
    "STATUS": "Estado",
    "PROGRESS": "Progresso",
    "DESCRIPTION": "Descricao",
    "NAME": "Nome",
    "DATE": "Data",
    "ID": "ID",
    # Empty states
    "NO_DATA": "Nenhum dado disponivel.",
    "NO_RESULTS": "Nenhum resultado encontrado.",
    "NO_TASKS": "Nenhuma tarefa pendente.",
    "NO_TASKS_PUBLISH": "Nenhuma tarefa pronta para publicar.",
    "NO_TASKS_DONE": "Nenhuma tarefa finalizada ainda.",
    "NO_TILES_GCS": "Nenhum tile no GCS.",
    "NO_MAP": "Nao foi possivel gerar o mapa. Verifique conexao GEE.",
    "NO_SELECTION": "Nenhuma opcao selecionada.",
    "NO_SAMPLES": "Nenhuma amostra encontrada com este filtro.",
    "NO_COGS": "Nenhum COG encontrado no repositorio GCS.",
    # M5 Widgets
    "ADD_BATCH": "Adicionar Lote a Fila",
    "REFRESH_VIEW": "Atualizar Vista",
    "LOAD_TO_QUEUE": "Carregar na Fila",
    "CLEAR_TEMP_TASKS": "Limpar Tarefas Temporarias",
    "SAVE_TASK_GCS": "Salvar Tarefa GCS",
    "EXCLUDE_TASK_GCS": "Excluir Tarefa GCS",
    "DELETE_MODEL": "Excluir Modelo",
    "DELETE_REGION": "Excluir Regiao",
    "DELETE_SELECTED": "Excluir Selecionados",
    "DELETE_ALL": "Excluir Todos",
    "DELETE_JOB": "Excluir Tudo",
    "VIEW_TILES": "Ver Tiles",
    "HIDE_TILES": "Ocultar",
    "REFRESH_MAP": "Atualizar Mapa",
    "TASK_NAME_PLACEHOLDER": "Ex: Classificar Amazonia Baixa 2025 (Lucas)",
    # M5 Tabs
    "TAB_GUIDE": "Guia",
    "TAB_REGISTER": "Registrar",
    "TAB_PENDING": "Pendentes",
    "TAB_PUBLISH": "Para Publicar",
    "TAB_MAP": "Mapa",
    "TAB_DONE": "Finalizadas",
    # Map / Grid
    "LIVE_PROCESSING": "Processando ao vivo",
    "CURRENT_TILE": "Tile atual",
    "COMPLETED": "Completados",
    "GRID_REGION": "Regiao",
    "GRID_CELLS": "Celulas cim-world",
    # Tiles / GCS
    "TILES": "tiles",
    "MOSAIC": "mosaico",
    "STATS": "stats",
    "SELECT_TILES_DELETE": "Selecione tiles para excluir.",
    "TILES_REMOVED": "tiles excluidos.",
    # Task status
    "STATUS_QUEUED": "Na fila",
    "STATUS_RUNNING": "Executando",
    "STATUS_COMPLETED": "Completado",
    "STATUS_FINISHED": "Finalizado",
    "STATUS_ERROR": "Erro",
    "STATUS_PUBLISHING": "Publicando",
    "STATUS_PUBLISHED": "Publicado",
    "STATUS_SKIPPED": "Omitido",
    # M4 - Training
    "MODEL_TRAINER": "Treinador de Modelo",
    "ITERATIONS": "Iteracoes",
    "BATCH_SIZE": "Tamanho do Lote",
    "LEARNING_RATE": "Taxa de Aprendizado",
    "HIDDEN_LAYERS": "Camadas Ocultas",
    "ACTIVATION": "Ativacao",
    "DROPOUT": "Dropout",
    "OPTIMIZER": "Otimizador",
    "LOSS_FN": "Funcao de Perda",
    "METRICS": "Metricas",
    "SAMPLE_SELECTION": "Selecao de Amostras",
    "EXTRACTION_MATRIX": "Matriz de Extracao",
    "MODEL_CONFIG": "Configuracao do Modelo",
    "GCS_DEST": "Destino GCS",
    "USAGE_GUIDE": "Guia de Uso",
    # M4 - Canvas
    "METADATA": "Metadados",
    "KPIS": "KPIs",
    "CONFUSION": "Confusao",
    "HISTORY": "Historico",
    "PROB": "Prob",
    "PR_CURVE": "PR-Curve",
    "MANAGEMENT": "Gestao",
    "RANKING": "Ranking / Repositorio",
    "SELECTED_CANVAS": "Selecionados no Canvas",
    "SEARCH_REPO": "Buscar no repositorio...",
    "SEARCH_SAMPLES": "Buscar amostras...",
    "SYNC_CATALOG": "Sincronizar Catalogo (GCS)",
    "APPLY_VISIBILITY": "Aplicar Visibilidade",
    # M1 / M2
    "SYNC_DATA": "Sincronizar Dados",
    "SELECT_PENDING": "Selecionar Pendentes",
    "CLEAR_SELECTION": "Limpar Selecao",
    "EXPORT_START": "Iniciar Exportacao",
    "MOSAIC_START": "Iniciar Montagem",
    # M6
    "POST_CLASSIFICATION": "Processador Pos-Classificacao",
    "USING_PRESET": "Usando Configuracao Predefinida",
    "FILTER_START": "Iniciar Filtragem",
    "EXPORT_TASK_STARTED": "Tarefa de exportacao iniciada",
    "CONFIG_SUMMARY": "Resumo da Configuracao",
    # M7
    "CURATOR": "Curador",
    "CURATOR_DESC": "Publicacao de Colecao Pre-Oficial",
    "USING_VOTES_PRESET": "Usando Votacao Predefinida",
    "CURATION_START": "Iniciar Curadoria",
    "EXPORT_ASSET_STARTED": "Exportacao GEE Asset iniciada",
    # Cache
    "CACHE_REMOVED": "Cache local removido",
    "CACHE_NOT_FOUND": "Cache nao encontrado",
    # Misc
    "LOADING_TILES": "Carregando tiles...",
    "CONFIRM_DELETE": "Confirmar Exclusao",
    "CONFIRM_DELETE_ALL": "Confirmar Exclusao Total",
    "CANCELED": "Cancelado.",
    "GLOBAL_OPTS_SET": "Opcoes globais configuradas",
    # Dropdown labels
    "DROP_MODEL": "Modelo:",
    "DROP_REGION": "Regiao:",
    "DROP_YEAR": "Ano:",
    "DROP_TASK": "Tarefa:",
    "DROP_TASK_NAME": "Nome Tarefa:",
    # Hyperparams
    "HP_EPOCHS": "Epocas",
    "HP_PATIENCE": "Paciencia",
    "HP_TEST_SPLIT": "Split de Teste",
    "HP_BALANCE": "Balanceamento",
    "HP_AUGMENT": "Aumento de Dados",
    "HP_ACTIVATION": "Funcao de Ativacao",
    "HP_OPTIMIZER": "Otimizador",
    "HP_LOSS": "Funcao de Perda",
    # Extraction
    "EXTRACTION_TITLE": "Matriz de Extracao (Multissensor GCS)",
    "SAMPLE_SELECT": "Selecao de Amostras",
    "AVAILABLE": "Disponiveis",
    "SELECTED": "Selecionados",
    "ADD": "Adicionar",
    "REMOVE": "Remover",
    "CAMPAIGN": "Campanha",
    "SENSOR": "Sensor",
    "BANDS": "Bandas",
    "STATUS_OK": "OK",
    "STATUS_RUN": "Exec.",
    "STATUS_MISS": "Falt.",
    # Training
    "TRAINING_ID": "ID Treinamento:",
    "SHORTNAME": "Nome Rapido:",
    "COMMENTS": "Comentarios...",
    "START_TRAINING": "Iniciar Treinamento",
    "CANVAS_TITLE": "Centro de Treinamentos e Auditoria",
    "CANVAS_EMPTY": "Canvas vazio",
    "CANVAS_HINT": "Navegue e selecione modelos no painel lateral para visualiza-los aqui.",
    "LOSS_ACC": "Loss / Accuracy",
    "VIZ_METADATA": "Metadados",
    "VIZ_KPIS": "KPIs",
    "VIZ_CONFUSION": "Confusao",
    "VIZ_HISTORY": "Historico",
    "VIZ_PROB": "Prob",
    "VIZ_PR_CURVE": "PR-Curve",
    "VIZ_MANAGEMENT": "Gestao",
    # Repository
    "REPO_TITLE": "Ranking / Repositorio",
    "REPO_SEARCH": "Buscar no repositorio...",
    "REPO_SYNC": "Sincronizar GCS",
    "REPO_ALL": "Todos",
    "REPO_CLEAR": "Limpar",
    "REPO_SYNC_CATALOG": "Sincronizar Catalogo (GCS)",
    "REPO_SCANNING": "Escaneando GCS... Aguarde.",
    "REPO_SCAN_DONE": "Catalogo Sincronizado!",
    # Tab titles
    "SORT_BY": "Ordenar por:",
    "NEW_TRAINING": "Novo Treinamento",
    "TRAININGS": "Treinamentos",
    # M1 - Export
    "EXPORT_TITLE": "Exportacao de Colecoes",
    "EXPORT_SYNC": "Sincronizar Dados",
    "EXPORT_SELECT": "Selecionar Pendentes",
    "EXPORT_CLEAR": "Limpar Selecao",
    "EXPORT_START_BTN": "Iniciar Exportacao",
    "EXPORT_SENT": "tarefas enviadas.",
    "EXPORT_NONE_SEL": "Nenhuma opcao selecionada para exportacao.",
    # M2 - Mosaic
    "MOSAIC_TITLE": "Montagem de Mosaicos",
    "MOSAIC_SYNC": "Sincronizar Dados",
    "MOSAIC_SELECT": "Selecionar Pendentes",
    "MOSAIC_CLEAR": "Limpar Selecao",
    "MOSAIC_START_BTN": "Iniciar Montagem",
    "MOSAIC_DONE": "Montagem concluida com sucesso",
    # M0 - Startup
    "START_COUNTRY": "Pais",
    "START_BUCKET": "Bucket",
    "START_VERSION": "Versao",
    "START_SENSOR": "Sensor",
    "START_PERIODICITY": "Periodicidade",
    "START_CAMPAIGN": "Campanha",
    "START_FOUND": "encontrado",
    "START_NOT_FOUND": "nao encontrado",
    "START_GDAL_OK": "GDAL encontrado e adicionado ao PATH",
    "START_GDAL_MISSING": "Aviso: Utilitarios GDAL nao encontrados",
    "START_COLAB_HINT": "No Google Colab, execute: !apt-get install -y gdal-bin",
    "START_WIN_HINT": "No Windows, certifique-se de que o GDAL esteja no seu PATH",
    # M6
    "M6_TITLE": "Processador Pos-Classificacao",
    "M6_PRESET": "Usando Configuracao Predefinida",
    "M6_DOWNLOAD": "Baixando fragmentos",
    "M6_VRT": "Construindo VRT",
    "M6_COG": "Convertendo para COG",
    "M6_UPLOAD": "Enviado",
    "M6_START": "Iniciando Filtragem",
    "M6_EXPORT_OK": "Tarefa de exportacao iniciada",
    "M6_SUMMARY": "Resumo da Configuracao",
    # M7
    "M7_TITLE": "Curador",
    "M7_DESC": "Publicacao de Colecao Pre-Oficial",
    "M7_PRESET": "Usando Votacao Predefinida",
    "M7_START": "Iniciando Curadoria",
    "M7_EXPORT_OK": "Exportacao GEE Asset iniciada para",
    "M7_SUMMARY": "Resumo da Configuracao",
    # M3
    "M3_TITLE": "M3 - Coleta de Amostras (GEE Toolkit Gateway)",
    "M3_SOURCE": "Acesso ao codigo fonte (GitHub)",
    "M3_EDITOR": "Acesso direto (Editor GEE)",
    "M3_DOCS": "Documentacao e normas de uso",
}

STRINGS_FR = {
    # General
    "LOADING": "Chargement...",
    "PROCESSING": "Traitement...",
    "DELETING": "Suppression...",
    "SAVING": "Enregistrement...",
    "SYNCING": "Synchronisation...",
    "SEARCHING": "Recherche...",
    "DONE": "Termine",
    "ERROR": "Erreur",
    "SUCCESS": "Succes",
    "WARNING": "Attention",
    "INFO": "Information",
    "ALL": "Tous",
    "ALL_F": "Toutes",
    "NONE": "Aucun",
    "BACK": "Retour",
    "OK": "OK",
    "CONFIRM": "Confirmer",
    "CANCEL": "Annuler",
    "SAVE": "Enregistrer",
    "DELETE": "Supprimer",
    "SYNC": "Synchroniser",
    "SEARCH": "Rechercher",
    "CLEAR": "Effacer",
    "REFRESH": "Actualiser",
    "APPLY": "Appliquer",
    "CLOSE": "Fermer",
    "MODEL": "Modele",
    "REGION": "Region",
    "YEAR": "Annee",
    "PERIOD": "Periode",
    "TASK": "Tache",
    "TASK_NAME": "Nom Tache",
    "STATUS": "Statut",
    "PROGRESS": "Progression",
    "DESCRIPTION": "Description",
    "NAME": "Nom",
    "DATE": "Date",
    "ID": "ID",
    # Empty states
    "NO_DATA": "Aucune donnee disponible.",
    "NO_RESULTS": "Aucun resultat trouve.",
    "NO_TASKS": "Aucune tache en attente.",
    "NO_TASKS_PUBLISH": "Aucune tache prete a publier.",
    "NO_TASKS_DONE": "Aucune tache terminee.",
    "NO_TILES_GCS": "Aucun tile dans GCS.",
    "NO_MAP": "Impossible de generer la carte. Verifier connexion GEE.",
    "NO_SELECTION": "Aucune option selectionnee.",
    "NO_SAMPLES": "Aucun echantillon trouve avec ce filtre.",
    "NO_COGS": "Aucun COG trouve dans le depot GCS.",
    # M5 Widgets
    "ADD_BATCH": "Ajouter un lot a la file",
    "REFRESH_VIEW": "Actualiser la vue",
    "LOAD_TO_QUEUE": "Charger dans la file",
    "CLEAR_TEMP_TASKS": "Effacer les taches temporaires",
    "SAVE_TASK_GCS": "Enregistrer tache GCS",
    "EXCLUDE_TASK_GCS": "Exclure tache GCS",
    "DELETE_MODEL": "Supprimer le modele",
    "DELETE_REGION": "Supprimer la region",
    "DELETE_SELECTED": "Supprimer selectionnes",
    "DELETE_ALL": "Tout supprimer",
    "DELETE_JOB": "Tout supprimer",
    "VIEW_TILES": "Voir les tiles",
    "HIDE_TILES": "Cacher",
    "REFRESH_MAP": "Actualiser la carte",
    "TASK_NAME_PLACEHOLDER": "Ex: Classifier Amazonie Basse 2025 (Lucas)",
    # M5 Tabs
    "TAB_GUIDE": "Guide",
    "TAB_REGISTER": "Enregistrer",
    "TAB_PENDING": "En attente",
    "TAB_PUBLISH": "A publier",
    "TAB_MAP": "Carte",
    "TAB_DONE": "Terminees",
    # Map / Grid
    "LIVE_PROCESSING": "Traitement en direct",
    "CURRENT_TILE": "Tile actuel",
    "COMPLETED": "Termines",
    "GRID_REGION": "Region",
    "GRID_CELLS": "Cellules cim-world",
    # Tiles / GCS
    "TILES": "tiles",
    "MOSAIC": "mosaique",
    "STATS": "stats",
    "SELECT_TILES_DELETE": "Selectionnez les tiles a supprimer.",
    "TILES_REMOVED": "tiles supprimes.",
    # Task status
    "STATUS_QUEUED": "En file",
    "STATUS_RUNNING": "En cours",
    "STATUS_COMPLETED": "Complete",
    "STATUS_FINISHED": "Termine",
    "STATUS_ERROR": "Erreur",
    "STATUS_PUBLISHING": "Publication",
    "STATUS_PUBLISHED": "Publie",
    "STATUS_SKIPPED": "Ignore",
    # M4 - Training
    "MODEL_TRAINER": "Entraineur de modele",
    "ITERATIONS": "Iterations",
    "BATCH_SIZE": "Taille du lot",
    "LEARNING_RATE": "Taux d apprentissage",
    "HIDDEN_LAYERS": "Couches cachees",
    "ACTIVATION": "Activation",
    "DROPOUT": "Dropout",
    "OPTIMIZER": "Optimiseur",
    "LOSS_FN": "Fonction de perte",
    "METRICS": "Metriques",
    "SAMPLE_SELECTION": "Selection d echantillons",
    "EXTRACTION_MATRIX": "Matrice d extraction",
    "MODEL_CONFIG": "Configuration du modele",
    "GCS_DEST": "Destination GCS",
    "USAGE_GUIDE": "Guide d utilisation",
    # M4 - Canvas
    "METADATA": "Metadonnees",
    "KPIS": "KPIs",
    "CONFUSION": "Confusion",
    "HISTORY": "Historique",
    "PROB": "Prob",
    "PR_CURVE": "Courbe PR",
    "MANAGEMENT": "Gestion",
    "RANKING": "Classement / Depot",
    "SELECTED_CANVAS": "Selectionnes dans Canvas",
    "SEARCH_REPO": "Rechercher dans le depot...",
    "SEARCH_SAMPLES": "Rechercher echantillons...",
    "SYNC_CATALOG": "Synchroniser catalogue (GCS)",
    "APPLY_VISIBILITY": "Appliquer la visibilite",
    # M1 / M2
    "SYNC_DATA": "Synchroniser donnees",
    "SELECT_PENDING": "Selectionner en attente",
    "CLEAR_SELECTION": "Effacer la selection",
    "EXPORT_START": "Demarrer exportation",
    "MOSAIC_START": "Demarrer assemblage",
    # M6
    "POST_CLASSIFICATION": "Processeur post-classification",
    "USING_PRESET": "Utilisation configuration predefinie",
    "FILTER_START": "Demarrer filtrage",
    "EXPORT_TASK_STARTED": "Tache d exportation demarree",
    "CONFIG_SUMMARY": "Resume de configuration",
    # M7
    "CURATOR": "Curateur",
    "CURATOR_DESC": "Publication collection pre-officielle",
    "USING_VOTES_PRESET": "Utilisation vote predefini",
    "CURATION_START": "Demarrer curation",
    "EXPORT_ASSET_STARTED": "Exportation GEE Asset demarree",
    # Cache
    "CACHE_REMOVED": "Cache local supprime",
    "CACHE_NOT_FOUND": "Cache introuvable",
    # Misc
    "LOADING_TILES": "Chargement tiles...",
    "CONFIRM_DELETE": "Confirmer la suppression",
    "CONFIRM_DELETE_ALL": "Confirmer la suppression totale",
    "CANCELED": "Annule.",
    "GLOBAL_OPTS_SET": "Options globales configurees",
    # Dropdown labels
    "DROP_MODEL": "Modele:",
    "DROP_REGION": "Region:",
    "DROP_YEAR": "Annee:",
    "DROP_TASK": "Tache:",
    "DROP_TASK_NAME": "Nom Tache:",
    # Hyperparams
    "HP_EPOCHS": "Epoques",
    "HP_PATIENCE": "Patience",
    "HP_TEST_SPLIT": "Split de test",
    "HP_BALANCE": "Equilibrage",
    "HP_AUGMENT": "Augmentation donnees",
    "HP_ACTIVATION": "Fonction d activation",
    "HP_OPTIMIZER": "Optimiseur",
    "HP_LOSS": "Fonction de perte",
    # Extraction
    "EXTRACTION_TITLE": "Matrice d extraction (Multicapteur GCS)",
    "SAMPLE_SELECT": "Selection echantillons",
    "AVAILABLE": "Disponibles",
    "SELECTED": "Selectionnes",
    "ADD": "Ajouter",
    "REMOVE": "Retirer",
    "CAMPAIGN": "Campagne",
    "SENSOR": "Capteur",
    "BANDS": "Bandas",
    "STATUS_OK": "OK",
    "STATUS_RUN": "Exec.",
    "STATUS_MISS": "Manq.",
    # Training
    "TRAINING_ID": "ID Entrainement:",
    "SHORTNAME": "Nom court:",
    "COMMENTS": "Commentaires...",
    "START_TRAINING": "Demarrer entrainement",
    "CANVAS_TITLE": "Centre d entrainement et d audit",
    "CANVAS_EMPTY": "Canvas vide",
    "CANVAS_HINT": "Parcourez et selectionnez des modeles dans le panneau lateral.",
    "LOSS_ACC": "Perte / Precision",
    "VIZ_METADATA": "Metadonnees",
    "VIZ_KPIS": "KPIs",
    "VIZ_CONFUSION": "Confusion",
    "VIZ_HISTORY": "Historique",
    "VIZ_PROB": "Prob",
    "VIZ_PR_CURVE": "Courbe PR",
    "VIZ_MANAGEMENT": "Gestion",
    # Repository
    "REPO_TITLE": "Classement / Depot",
    "REPO_SEARCH": "Rechercher dans le depot...",
    "REPO_SYNC": "Synchroniser GCS",
    "REPO_ALL": "Tous",
    "REPO_CLEAR": "Effacer",
    "REPO_SYNC_CATALOG": "Synchroniser catalogue (GCS)",
    "REPO_SCANNING": "Analyse GCS... Patientez.",
    "REPO_SCAN_DONE": "Catalogue synchronise!",
    # Tab titles
    "SORT_BY": "Trier par:",
    "NEW_TRAINING": "Nouvel entrainement",
    "TRAININGS": "Entrainements",
    # M1 - Export
    "EXPORT_TITLE": "Exportation de collections",
    "EXPORT_SYNC": "Synchroniser donnees",
    "EXPORT_SELECT": "Selectionner en attente",
    "EXPORT_CLEAR": "Effacer selection",
    "EXPORT_START_BTN": "Demarrer exportation",
    "EXPORT_SENT": "taches envoyees.",
    "EXPORT_NONE_SEL": "Aucune option selectionnee pour l exportation.",
    # M2 - Mosaic
    "MOSAIC_TITLE": "Assemblage de mosaiques",
    "MOSAIC_SYNC": "Synchroniser donnees",
    "MOSAIC_SELECT": "Selectionner en attente",
    "MOSAIC_CLEAR": "Effacer selection",
    "MOSAIC_START_BTN": "Demarrer assemblage",
    "MOSAIC_DONE": "Assemblage termine avec succes",
    # M0 - Startup
    "START_COUNTRY": "Pays",
    "START_BUCKET": "Bucket",
    "START_VERSION": "Version",
    "START_SENSOR": "Capteur",
    "START_PERIODICITY": "Periodicite",
    "START_CAMPAIGN": "Campagne",
    "START_FOUND": "trouve",
    "START_NOT_FOUND": "non trouve",
    "START_GDAL_OK": "GDAL trouve et ajoute au PATH",
    "START_GDAL_MISSING": "Avertissement: Utilitaires GDAL non trouves",
    "START_COLAB_HINT": "Sur Google Colab, executez: !apt-get install -y gdal-bin",
    "START_WIN_HINT": "Sur Windows, assurez-vous que GDAL est dans votre PATH",
    # M6
    "M6_TITLE": "Processeur post-classification",
    "M6_PRESET": "Utilisation configuration predefinie",
    "M6_DOWNLOAD": "Telechargement fragments",
    "M6_VRT": "Construction VRT",
    "M6_COG": "Conversion en COG",
    "M6_UPLOAD": "Telecharge",
    "M6_START": "Demarrage filtrage",
    "M6_EXPORT_OK": "Tache exportation demarree",
    "M6_SUMMARY": "Resume configuration",
    # M7
    "M7_TITLE": "Curateur",
    "M7_DESC": "Publication collection pre-officielle",
    "M7_PRESET": "Utilisation vote predefini",
    "M7_START": "Demarrage curation",
    "M7_EXPORT_OK": "Exportation GEE Asset demarree pour",
    "M7_SUMMARY": "Resume configuration",
    # M3
    "M3_TITLE": "M3 - Collecte d echantillons (Passerelle GEE Toolkit)",
    "M3_SOURCE": "Code source (GitHub)",
    "M3_EDITOR": "Acces direct (Editeur GEE)",
    "M3_DOCS": "Documentation et normes d utilisation",
}

STRINGS_ID = {
    # General
    "LOADING": "Memuat...",
    "PROCESSING": "Memproses...",
    "DELETING": "Menghapus...",
    "SAVING": "Menyimpan...",
    "SYNCING": "Menyinkronkan...",
    "SEARCHING": "Mencari...",
    "DONE": "Selesai",
    "ERROR": "Kesalahan",
    "SUCCESS": "Berhasil",
    "WARNING": "Peringatan",
    "INFO": "Informasi",
    "ALL": "Semua",
    "ALL_F": "Semua",
    "NONE": "Tidak Ada",
    "BACK": "Kembali",
    "OK": "OK",
    "CONFIRM": "Konfirmasi",
    "CANCEL": "Batal",
    "SAVE": "Simpan",
    "DELETE": "Hapus",
    "SYNC": "Sinkron",
    "SEARCH": "Cari",
    "CLEAR": "Bersihkan",
    "REFRESH": "Muat Ulang",
    "APPLY": "Terapkan",
    "CLOSE": "Tutup",
    "MODEL": "Model",
    "REGION": "Wilayah",
    "YEAR": "Tahun",
    "PERIOD": "Periode",
    "TASK": "Tugas",
    "TASK_NAME": "Nama Tugas",
    "STATUS": "Status",
    "PROGRESS": "Progres",
    "DESCRIPTION": "Deskripsi",
    "NAME": "Nama",
    "DATE": "Tanggal",
    "ID": "ID",
    # Empty states
    "NO_DATA": "Tidak ada data tersedia.",
    "NO_RESULTS": "Tidak ada hasil ditemukan.",
    "NO_TASKS": "Tidak ada tugas tertunda.",
    "NO_TASKS_PUBLISH": "Tidak ada tugas siap dipublikasi.",
    "NO_TASKS_DONE": "Belum ada tugas selesai.",
    "NO_TILES_GCS": "Tidak ada tile di GCS.",
    "NO_MAP": "Tidak dapat membuat peta. Periksa koneksi GEE.",
    "NO_SELECTION": "Tidak ada opsi dipilih.",
    "NO_SAMPLES": "Tidak ada sampel ditemukan dengan filter ini.",
    "NO_COGS": "Tidak ada COG ditemukan di repositori GCS.",
    # M5 Widgets
    "ADD_BATCH": "Tambah Batch ke Antrean",
    "REFRESH_VIEW": "Muat Ulang Tampilan",
    "LOAD_TO_QUEUE": "Muat ke Antrean",
    "CLEAR_TEMP_TASKS": "Bersihkan Tugas Sementara",
    "SAVE_TASK_GCS": "Simpan Tugas GCS",
    "EXCLUDE_TASK_GCS": "Keluarkan Tugas GCS",
    "DELETE_MODEL": "Hapus Model",
    "DELETE_REGION": "Hapus Wilayah",
    "DELETE_SELECTED": "Hapus yang Dipilih",
    "DELETE_ALL": "Hapus Semua",
    "DELETE_JOB": "Hapus Semua",
    "VIEW_TILES": "Lihat Tile",
    "HIDE_TILES": "Sembunyikan",
    "REFRESH_MAP": "Muat Ulang Peta",
    "TASK_NAME_PLACEHOLDER": "Contoh: Klasifikasi Amazon Bawah 2025 (Lucas)",
    # M5 Tabs
    "TAB_GUIDE": "Panduan",
    "TAB_REGISTER": "Daftar",
    "TAB_PENDING": "Tertunda",
    "TAB_PUBLISH": "Untuk Publikasi",
    "TAB_MAP": "Peta",
    "TAB_DONE": "Selesai",
    # Map / Grid
    "LIVE_PROCESSING": "Pemrosesan Langsung",
    "CURRENT_TILE": "Tile saat ini",
    "COMPLETED": "Selesai",
    "GRID_REGION": "Wilayah",
    "GRID_CELLS": "Sel cim-world",
    # Tiles / GCS
    "TILES": "tile",
    "MOSAIC": "mozaik",
    "STATS": "statistik",
    "SELECT_TILES_DELETE": "Pilih tile untuk dihapus.",
    "TILES_REMOVED": "tile dihapus.",
    # Task status
    "STATUS_QUEUED": "Dalam antrean",
    "STATUS_RUNNING": "Berjalan",
    "STATUS_COMPLETED": "Selesai",
    "STATUS_FINISHED": "Terselesaikan",
    "STATUS_ERROR": "Kesalahan",
    "STATUS_PUBLISHING": "Mempublikasi",
    "STATUS_PUBLISHED": "Dipublikasi",
    "STATUS_SKIPPED": "Dilewati",
    # M4 - Training
    "MODEL_TRAINER": "Pelatih Model",
    "ITERATIONS": "Iterasi",
    "BATCH_SIZE": "Ukuran Batch",
    "LEARNING_RATE": "Laju Pembelajaran",
    "HIDDEN_LAYERS": "Lapisan Tersembunyi",
    "ACTIVATION": "Aktivasi",
    "DROPOUT": "Dropout",
    "OPTIMIZER": "Pengoptimal",
    "LOSS_FN": "Fungsi Kerugian",
    "METRICS": "Metrik",
    "SAMPLE_SELECTION": "Pemilihan Sampel",
    "EXTRACTION_MATRIX": "Matriks Ekstraksi",
    "MODEL_CONFIG": "Konfigurasi Model",
    "GCS_DEST": "Tujuan GCS",
    "USAGE_GUIDE": "Panduan Penggunaan",
    # M4 - Canvas
    "METADATA": "Metadata",
    "KPIS": "KPI",
    "CONFUSION": "Kebingungan",
    "HISTORY": "Riwayat",
    "PROB": "Prob",
    "PR_CURVE": "Kurva PR",
    "MANAGEMENT": "Manajemen",
    "RANKING": "Peringkat / Repositori",
    "SELECTED_CANVAS": "Dipilih di Canvas",
    "SEARCH_REPO": "Cari repositori...",
    "SEARCH_SAMPLES": "Cari sampel...",
    "SYNC_CATALOG": "Sinkron Katalog (GCS)",
    "APPLY_VISIBILITY": "Terapkan Visibilitas",
    # M1 / M2
    "SYNC_DATA": "Sinkron Data",
    "SELECT_PENDING": "Pilih Tertunda",
    "CLEAR_SELECTION": "Bersihkan Pilihan",
    "EXPORT_START": "Mulai Ekspor",
    "MOSAIC_START": "Mulai Perakitan",
    # M6
    "POST_CLASSIFICATION": "Pemroses Pasca-Klasifikasi",
    "USING_PRESET": "Menggunakan Konfigurasi Preset",
    "FILTER_START": "Mulai Penyaringan",
    "EXPORT_TASK_STARTED": "Tugas ekspor dimulai",
    "CONFIG_SUMMARY": "Ringkasan Konfigurasi",
    # M7
    "CURATOR": "Kurator",
    "CURATOR_DESC": "Publikasi Koleksi Pra-Resmi",
    "USING_VOTES_PRESET": "Menggunakan Suara Preset",
    "CURATION_START": "Mulai Kurasi",
    "EXPORT_ASSET_STARTED": "Ekspor GEE Asset dimulai",
    # Cache
    "CACHE_REMOVED": "Cache lokal dihapus",
    "CACHE_NOT_FOUND": "Cache tidak ditemukan",
    # Misc
    "LOADING_TILES": "Memuat tile...",
    "CONFIRM_DELETE": "Konfirmasi Penghapusan",
    "CONFIRM_DELETE_ALL": "Konfirmasi Hapus Semua",
    "CANCELED": "Dibatalkan.",
    "GLOBAL_OPTS_SET": "Opsi global dikonfigurasi",
    # Dropdown labels
    "DROP_MODEL": "Model:",
    "DROP_REGION": "Wilayah:",
    "DROP_YEAR": "Tahun:",
    "DROP_TASK": "Tugas:",
    "DROP_TASK_NAME": "Nama Tugas:",
    # Hyperparams
    "HP_EPOCHS": "Epoch",
    "HP_PATIENCE": "Kesabaran",
    "HP_TEST_SPLIT": "Split Uji",
    "HP_BALANCE": "Keseimbangan",
    "HP_AUGMENT": "Augmentasi Data",
    "HP_ACTIVATION": "Fungsi Aktivasi",
    "HP_OPTIMIZER": "Pengoptimal",
    "HP_LOSS": "Fungsi Kerugian",
    # Extraction
    "EXTRACTION_TITLE": "Matriks Ekstraksi (Multisensor GCS)",
    "SAMPLE_SELECT": "Pemilihan Sampel",
    "AVAILABLE": "Tersedia",
    "SELECTED": "Dipilih",
    "ADD": "Tambah",
    "REMOVE": "Hapus",
    "CAMPAIGN": "Kampanye",
    "SENSOR": "Sensor",
    "BANDS": "Band",
    "STATUS_OK": "OK",
    "STATUS_RUN": "Jal.",
    "STATUS_MISS": "Hil.",
    # Training
    "TRAINING_ID": "ID Pelatihan:",
    "SHORTNAME": "Nama Singkat:",
    "COMMENTS": "Komentar...",
    "START_TRAINING": "Mulai Pelatihan",
    "CANVAS_TITLE": "Pusat Pelatihan dan Audit",
    "CANVAS_EMPTY": "Canvas kosong",
    "CANVAS_HINT": "Jelajahi dan pilih model di panel samping untuk melihatnya di sini.",
    "LOSS_ACC": "Loss / Akurasi",
    "VIZ_METADATA": "Metadata",
    "VIZ_KPIS": "KPI",
    "VIZ_CONFUSION": "Kebingungan",
    "VIZ_HISTORY": "Riwayat",
    "VIZ_PROB": "Prob",
    "VIZ_PR_CURVE": "Kurva PR",
    "VIZ_MANAGEMENT": "Manajemen",
    # Repository
    "REPO_TITLE": "Peringkat / Repositori",
    "REPO_SEARCH": "Cari repositori...",
    "REPO_SYNC": "Sinkron GCS",
    "REPO_ALL": "Semua",
    "REPO_CLEAR": "Bersihkan",
    "REPO_SYNC_CATALOG": "Sinkron Katalog (GCS)",
    "REPO_SCANNING": "Memindai GCS... Harap tunggu.",
    "REPO_SCAN_DONE": "Katalog tersinkronisasi!",
    # Tab titles
    "SORT_BY": "Urutkan:",
    "NEW_TRAINING": "Pelatihan Baru",
    "TRAININGS": "Pelatihan",
    # M1 - Export
    "EXPORT_TITLE": "Ekspor Koleksi",
    "EXPORT_SYNC": "Sinkron Data",
    "EXPORT_SELECT": "Pilih Tertunda",
    "EXPORT_CLEAR": "Bersihkan Pilihan",
    "EXPORT_START_BTN": "Mulai Ekspor",
    "EXPORT_SENT": "tugas terkirim.",
    "EXPORT_NONE_SEL": "Tidak ada opsi dipilih untuk ekspor.",
    # M2 - Mosaic
    "MOSAIC_TITLE": "Perakitan Mozaik",
    "MOSAIC_SYNC": "Sinkron Data",
    "MOSAIC_SELECT": "Pilih Tertunda",
    "MOSAIC_CLEAR": "Bersihkan Pilihan",
    "MOSAIC_START_BTN": "Mulai Perakitan",
    "MOSAIC_DONE": "Perakitan berhasil diselesaikan",
    # M0 - Startup
    "START_COUNTRY": "Negara",
    "START_BUCKET": "Bucket",
    "START_VERSION": "Versi",
    "START_SENSOR": "Sensor",
    "START_PERIODICITY": "Periodisitas",
    "START_CAMPAIGN": "Kampanye",
    "START_FOUND": "ditemukan",
    "START_NOT_FOUND": "tidak ditemukan",
    "START_GDAL_OK": "GDAL ditemukan dan ditambahkan ke PATH",
    "START_GDAL_MISSING": "Peringatan: Utilitas GDAL tidak ditemukan",
    "START_COLAB_HINT": "Di Google Colab, jalankan: !apt-get install -y gdal-bin",
    "START_WIN_HINT": "Di Windows, pastikan GDAL ada di PATH Anda",
    # M6
    "M6_TITLE": "Pemroses Pasca-Klasifikasi",
    "M6_PRESET": "Menggunakan Konfigurasi Preset",
    "M6_DOWNLOAD": "Mengunduh fragmen",
    "M6_VRT": "Membangun VRT",
    "M6_COG": "Mengonversi ke COG",
    "M6_UPLOAD": "Diunggah",
    "M6_START": "Memulai Penyaringan",
    "M6_EXPORT_OK": "Tugas ekspor dimulai",
    "M6_SUMMARY": "Ringkasan Konfigurasi",
    # M7
    "M7_TITLE": "Kurator",
    "M7_DESC": "Publikasi Koleksi Pra-Resmi",
    "M7_PRESET": "Menggunakan Suara Preset",
    "M7_START": "Memulai Kurasi",
    "M7_EXPORT_OK": "Ekspor GEE Asset dimulai untuk",
    "M7_SUMMARY": "Ringkasan Konfigurasi",
    # M3
    "M3_TITLE": "M3 - Koleksi Sampel (Gateway Toolkit GEE)",
    "M3_SOURCE": "Kode sumber (GitHub)",
    "M3_EDITOR": "Akses langsung (Editor GEE)",
    "M3_DOCS": "Dokumentasi dan panduan penggunaan",
}

SUPPORTED_LOCALES = {
    "en": None,        # English is the default (class attributes)
    "es": STRINGS_ES,
    "pt": STRINGS_PT,
    "fr": STRINGS_FR,
    "id": STRINGS_ID,
}

LOCALE_LABELS = {
    "en": "English",
    "es": "Espanol",
    "pt": "Portugues",
    "fr": "Francais",
    "id": "Bahasa Indonesia",
}


# ── Locale switching ─────────────────────────────────────────

def _load_locale(cls, locale="en"):
    """Swap all class attributes to the given locale.

    - English ('en') → restores the original class defaults.
    - Others ('es', 'pt', 'fr', 'id') → applies the corresponding STRINGS_XX dict.
    """
    strings = SUPPORTED_LOCALES.get(locale)
    if strings is None:
        if locale == "en":
            return  # already English defaults
        raise ValueError(f"Locale '{locale}' is not supported. Supported: {list(SUPPORTED_LOCALES)}")
    for k, v in strings.items():
        if hasattr(cls, k):
            setattr(cls, k, v)


# Install the method on the class
L.load_locale = classmethod(_load_locale)
