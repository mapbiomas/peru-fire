# MapBiomas Fuego - Perú (peru-fire)

Este repositorio es el punto de entrada (directorio raíz) de los scripts y proyectos dedicados al mapeo de áreas quemadas en Perú, impulsados por la red colaborativa de [MapBiomas Fuego](https://brasil.mapbiomas.org/es/metodo-mapbiomas-fogo/).

El ecosistema contiene módulos independientes pero interconectados para la gestión integral de datos y algoritmos:

## Módulos del Repositorio

1. **[MapBiomas Fire Monitor (`mapbiomas_fire_monitor/`)](./mapbiomas_fire_monitor/README.md)**  
   Aplicación interactiva y pipeline de datos (M1, M2, etc.) responsable de la orquestación, exportación, descarga y validación de las imágenes y mosaicos satelitales que alimentan la clasificación.

2. **[Fire Landsat 30m (`fire_landsat_30m/`)](./fire_landsat_30m/README.md)**  
   Rutinas, cuadernos y parametrizaciones metodológicas específicas para la clasificación de cicatrices usando imágenes Landsat de 30 metros, en la `collection_01` correspondientes a las ecorregiones del Perú.

## Equipo Institucional y Contacto

Desarrollado con apoyo tecnológico y metodológico del **Instituto de Pesquisa Ambiental da Amazônia (IPAM)**.

Para dudas técnicas, colaboración o reporte de problemas:
* **Vera Arruda** - vera.arruda@ipam.org.br
* **Wallace Silva** - wallace.silva@ipam.org.br
