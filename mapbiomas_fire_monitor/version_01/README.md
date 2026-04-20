# MapBiomas Fire Monitor - Version 01 (Perú)

Esta es la implementación técnica completa del ecosistema MapBiomas Fuego para la gestión automatizada y el procesamiento de imágenes en Perú.

A diferencia del planteamiento teórico, **todos los módulos (del M1 al M7) ya han sido implementados en el código base**, contando con su propia arquitectura distribuida, soporte para Deep Learning (TensorFlow) y herramientas nativas de geoprocesamiento (GDAL, Rasterio).

## Flujo de Trabajo y Etapas del Pipeline (M1 a M7)

El modelo asume un procesamiento híbrido: la nube (Google Earth Engine y Google Cloud Storage) se encarga del cómputo masivo inicial y el almacenamiento, y el procesamiento local se encarga del entrenamiento neuronal, inferencia y consolidación geográfica pesada.

1. **[M1] Exportación de Mosaicos (`M1_export_logic` / `ui`)**  
   Generación de los mosaicos crudos (Landsat/Sentinel) en Earth Engine y dictado masivo (Export.image.toCloudStorage) hacia los *buckets* (GCS).

2. **[M2] Descarga y Mosaico Local (`M2_mosaic`...)**  
   Sincronización multi-hilo desde GCS. Utiliza `gdalbuildvrt` y `gdal_translate` para unir (*stacking* y *mosaicking*) las bandas disgregadas y reconstruir un Cloud Optimized GeoTIFF (COG) continuo.

3. **[M3] Gestor de Muestras (`M3_sample_manager`)**  
   Extrae firmas espectrales reales intersectando un FeatureCollection de puntos (etiquetados 1=quemado, 0=no-quemado) con los mosaicos. Consolida el Dataset.

4. **[M4] Entrenador del Modelo (`M4_model_trainer`)**  
   Despliega una Red Neuronal Profunda (DNN) mediante TensorFlow 1.x con `NUM_INPUT` completamente dinámico basado en las bandas seleccionadas. Gestiona el hold-out (split), entrena localmente y exporta los pesos y el `hyperparameters.json` de vuelta a GCS.

5. **[M5] Clasificador (`M5_classifier`)**  
   Módulo de Inferencia. Recupera los pesos desde GCS, fragmenta (genera *tiles* y *Dynamic Grids*) la imagen a clasificar para evitar saturación de RAM, corre las matrices sobre la DNN y escribe el resultado *dayOfYear* (día de quema juliano, en lugar de un mero binario). Aplica un primer grado de filtro morfológico.

6. **[M6] Publicador y Filtros LULC (`M6_publisher`)**  
   Asume las clasificaciones (M5) y cruza la capa contra las máscaras MapBiomas LULC (para excluir agua dinámica, vías urbanas, nieve, etc.). Limpia "pixeles aislados", reensambla los *tiles* clasificados en un COG único, e inyecta la Metadata en EE como *ImageCollection*.

7. **[M7] Curador de Colecciones (`M7_curator`)**  
   Tablero de revisión para seleccionar de entre las distintas variantes (modelos / filtros corridos) cuál es la "ganadora", para luego forjar el *commit* de Exportación final hacia el `GEE Asset` de Colección Pre-Oficial.

## Requisitos de Entorno

Debido a la magnitud del pipeline de IA:
```bash
conda env create -f environment.yml
conda activate fire_monitor
```
Es altamente estricto asegurar:
- Tener **TensorFlow 1.x / `tensorflow.compat.v1`** disponible.
- **`rasterio` y `scipy`** deben estar funcionales (para filtros espaciales como `sieve` y morfológicos).
- Presencia nativa de **GDAL** instalado.

## Demandas y Tareas Pendientes (Issues / TODO)

Al haber verificado el despliegue del software y sus clases (Python Scripts), listamos las optimizaciones o deudas técnicas a subsanar:

- [ ] **Despliegue de Notebooks y UIs**: M1 y M2 ya operan mediante UI (`_ui.py`). Es urgente integrar las clases de control e ipywidgets creadas en M3, M4, M5, M6 y M7 en *Jupyter Notebooks* limpios (directorio `/notebooks`) para el usuario final.
- [ ] **Validación TensorFlow**: Certificar el comportamiento del Entrenador DNN desarrollado (M4) usando las cuencas y las ecorregiones peruanas. Si existen disonancias en RAM por TF1, proponer eventual upgrade a TF2/Keras de ser mandatorio.
- [ ] **Verificación de LULC en M6**: El publicador M6 invoca `mapbiomas_peru_collection2_integration_v1`. Validar si las clases (26=Agua, 22=Suelo desnudo, 33=Ríos, 24=Infraestructura) son correctas e identitarias a la taxonomía peruana actual.
- [ ] **Prueba de Calibración End-to-End**: Realizar una corrida integral (M1 al M7). Documentar tiempos de ejecución y generar un breve tutorial en video o imágenes (*Walkthrough*) demostrando cómo operar las interfaces desde los notebooks.
