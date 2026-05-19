import os
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer
from M0_auth_config import CONFIG, mosaic_name, monthly_cog_path, yearly_cog_path, get_temp_dir, _gcs_download, _gcs_upload
from M4_data_extractor import normalize

def load_model_from_gcs(model_dir, fs, logger=None):
    """Carga modelo Keras + metadatos desde GCS."""
    import json
    import tensorflow as tf

    meta_path = f"{model_dir}/metadata.json"
    if not fs.exists(meta_path):
        raise ValueError(f"metadata.json no encontrado en {meta_path}")

    with fs.open(meta_path, 'r') as f:
        meta = json.load(f)

    bands_config = meta.get('bands_config', {})
    if not bands_config:
        raise ValueError("Modelo no tiene 'bands_config' en los metadatos.")

    norm_stats = {int(k): tuple(v) for k, v in meta.get('norm_stats', {}).items()}
    num_input = meta['num_input']
    layers_cfg = meta['layers']

    local_npz = os.path.join(get_temp_dir(), f"{meta.get('training_id', 'model')}_weights.npz")
    _gcs_download(f"{model_dir}/weights.npz", local_npz)

    if logger:
        logger(f"    Modelo cargado: {meta.get('training_id')} | {num_input} bandas | layers {layers_cfg}")

    model = tf.keras.Sequential()
    model.add(tf.keras.layers.Input(shape=(num_input,)))
    for n_units in layers_cfg:
        model.add(tf.keras.layers.Dense(n_units, activation='relu'))
    model.add(tf.keras.layers.Dense(1, activation='sigmoid'))

    w = np.load(local_npz)
    layer_names = [f'fc_{i}' for i in range(len(layers_cfg))] + ['output']
    weights_list = []
    for ln in layer_names:
        weights_list.append(w[f'{ln}/kernel:0'])
        weights_list.append(w[f'{ln}/bias:0'])
    model.set_weights(weights_list)

    os.remove(local_npz)
    return model, meta, bands_config, norm_stats

def build_band_paths(bands_config, year, month):
    """Construye diccionario {banda: gcs_path} para un periodo."""
    from M0_auth_config import CONFIG
    periodicity = 'monthly' if month else 'yearly'
    paths = {}
    for b, cfg in bands_config.items():
        s_name = cfg.get('sensor', 'sentinel2').lower()
        m_type = cfg.get('mosaic', 'minnbr').lower()

        if periodicity == 'monthly':
            rel_folder = monthly_cog_path(year, month, mosaic=m_type, sensor=s_name)
        else:
            rel_folder = yearly_cog_path(year, mosaic=m_type, sensor=s_name)

        b_correct = 'dayOfYear' if b.lower() == 'dayofyear' else b
        cog_name = f"{mosaic_name(year, month, periodicity, band=b_correct, mosaic=m_type, sensor=s_name)}_cog.tif"
        paths[b] = f"{CONFIG['bucket']}/{rel_folder}/{cog_name}"
    return paths

def _reproject_geometry(geom_coords, src_crs):
    """Reprojecta geometria EPSG:4326 -> src_crs. Retorna lista [geojson] para mask()."""
    if src_crs and str(src_crs).upper() != 'EPSG:4326':
        geom_shape = shape(geom_coords)
        transformer = Transformer.from_crs('EPSG:4326', src_crs, always_xy=True)
        geom_proj = transform(transformer.transform, geom_shape)
        return [mapping(geom_proj)]
    return [geom_coords]

def classify_cell_with_cogs(cell_id, predict_fn, bands_config, norm_stats, out_gcs_path, cogs, logger=None):
    """Clasifica un tile cim-world usando COGs ya descargados.

    Args:
        cogs: dict {banda: ruta_local_o_vsig} con los COGs listos para abrir.
    """
    import ee
    bands_sorted = sorted(bands_config.keys())

    cim = ee.FeatureCollection("projects/mapbiomas-workspace/AUXILIAR/cim-world-1-250000")
    cell_feature = cim.filter(ee.Filter.eq('name', cell_id)).first()
    cell_geom = cell_feature.geometry()

    sources = {}
    try:
        geom_coords = cell_geom.getInfo()

        for b in bands_sorted:
            sources[b] = rasterio.open(cogs[b])

        src_crs = sources[bands_sorted[0]].crs
        clip_geom = _reproject_geometry(geom_coords, src_crs)

        band_data = {}
        profile = None

        for b in bands_sorted:
            out_image, out_transform = mask(
                sources[b], clip_geom, crop=True, filled=True,
                nodata=sources[b].nodata or -9999
            )
            band_data[b] = out_image.data[0]
            if profile is None:
                profile = sources[b].profile.copy()

        height, width = band_data[bands_sorted[0]].shape
        stack = np.stack([band_data[b] for b in bands_sorted], axis=-1)
        valid_mask = np.all(stack > -9999, axis=-1)

        valid_pixels = stack[valid_mask]
        total_valid = valid_pixels.shape[0]

        if total_valid == 0:
            if logger:
                logger(f"    [AVISO] Ningun pixel valido en {cell_id} (CRS COG: {src_crs})")
            return None

        X_norm = normalize(valid_pixels, norm_stats)
        probs = predict_fn(X_norm)

        if probs.ndim > 1 and probs.shape[1] == 1:
            probs = probs.flatten()

        output_class = np.zeros((height, width), dtype=np.uint8)
        output_prob = np.zeros((height, width), dtype=np.float32)
        output_class[valid_mask] = (probs > 0.5).astype(np.uint8)
        output_prob[valid_mask] = probs.astype(np.float32)

        profile.update(dtype=rasterio.float32, count=2, compress='lzw', nodata=-9999)

        local_tmp = os.path.join(get_temp_dir(), f"{cell_id}.tif")
        with rasterio.open(local_tmp, 'w', **profile) as dst:
            dst.write(output_class, 1)
            dst.write(output_prob, 2)

        fs.put(local_tmp, out_gcs_path)
        os.remove(local_tmp)

        burned_mask = probs > 0.5
        n_burned = burned_mask.sum()
        mean_conf = float(probs[burned_mask].mean()) if n_burned > 0 else 0.0

        return {
            'total_pixels': total_valid,
            'burned_pixels': int(n_burned),
            'mean_confidence': mean_conf,
        }

    except Exception as e:
        if logger:
            logger(f"    [ERROR] Fallo al clasificar {cell_id}: {e}")
        raise
    finally:
        for s in sources.values():
            s.close()

