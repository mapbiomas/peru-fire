# MapBiomas Fire Monitor - Perú

Este directorio concentra el gestor central y la lógica interactiva del ecosistema MapBiomas Fuego enfocada en el flujo de datos para monitoreo temporal de satélites en Perú.

Debido a la evolución natural de la iniciativa, con sus posibles cambios de esquemas de almacenamiento o arquitecturas de modelo, los ecosistemas de código están paquetizados en distintas **versiones**.

## Versiones Activas

- **[`version_01/`](./version_01/)**: 
  Nuestra implementación más reciente. Centraliza la base lógica e interfaces gráficas interactivas para Google Earth Engine (exportación interactiva), manejo en Google Cloud Storage y el stack de paralelismo GDAL local (para armado masivo de mosaicos continuos), estableciendo el paso inicial y fundamental hacia el modelo Deep Learning local.

> Visita los directorios de cada versión para consultar su `README.md` respectivo. Allí encontrarás instrucciones puntuales sobre la instanciación de Python, explicación detallada de los Módulos del Pipeline (de la descarga inicial al post-procesamiento de mapas) y todas sus metas / tareas pendientes de resolver.
