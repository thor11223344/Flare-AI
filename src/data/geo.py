"""Geospatial utilities: Census tract polygon boundaries, geometry simplification,
and deterministic synthetic-to-real GEOID mapping.
"""
import json
import zipfile
import warnings
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd
from src import config

SHAPEFILE_URL = "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_06_tract_500k.zip"
RAW_DIR = config.DATA_DIR / "raw"
PROCESSED_DIR = config.DATA_DIR / "processed"
ZIP_PATH = RAW_DIR / "cb_2022_06_tract_500k.zip"
SHP_DIR = RAW_DIR / "cb_2022_06_tract_500k"
GEOID_MAP_PATH = PROCESSED_DIR / "tract_geoid_map.json"

_cached_gdf = None


def download_boundary_file() -> Optional[Path]:
    """Download Census cartographic boundary file (cb_2022_06_tract_500k.zip).
    Returns path to unzipped shapefile directory, or None on failure.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if SHP_DIR.exists() and any(SHP_DIR.glob("*.shp")):
        return SHP_DIR

    # Check repository root data/raw if running in test environment with temp data dir
    root_shp = config.ROOT / "data" / "raw" / "cb_2022_06_tract_500k"
    if root_shp.exists() and any(root_shp.glob("*.shp")):
        return root_shp

    root_zip = config.ROOT / "data" / "raw" / "cb_2022_06_tract_500k.zip"
    if root_zip.exists() and not ZIP_PATH.exists():
        import shutil
        try:
            shutil.copy2(root_zip, ZIP_PATH)
        except Exception:
            pass

    if not ZIP_PATH.exists() and not root_zip.exists():
        try:
            import requests
            print("[geo] Downloading Census boundary file cb_2022_06_tract_500k.zip...")
            resp = requests.get(SHAPEFILE_URL, timeout=30)
            resp.raise_for_status()
            ZIP_PATH.write_bytes(resp.content)
            print(f"[geo] Downloaded Census boundaries ({len(resp.content):,} bytes).")
        except Exception as e:
            print(f"[geo] Warning: Failed to download Census boundaries ({e}). Falling back to centroid map.")
            return None

    try:
        SHP_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(ZIP_PATH) as z:
            z.extractall(SHP_DIR)
        print(f"[geo] Extracted boundary shapefiles to {SHP_DIR}")
        return SHP_DIR
    except Exception as e:
        print(f"[geo] Warning: Failed to extract shapefile ({e}). Falling back to centroid map.")
        return None


def load_real_tract_geometries(simplify_tolerance: float = 0.003) -> Optional[pd.DataFrame]:
    """Load, reproject to WGS84, and simplify tract geometries from Census boundary shapefile."""
    global _cached_gdf
    if _cached_gdf is not None:
        return _cached_gdf

    shp_path = download_boundary_file()
    if shp_path is None:
        return None

    try:
        import geopandas as gpd
        gdf = gpd.read_file(shp_path)
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)

        gdf["county"] = gdf["NAMELSADCO"].str.replace(" County", "", regex=False)
        gdf["real_geoid"] = gdf["GEOID"]

        # Calculate accurate projected centroids then convert to EPSG:4326
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            centroids_proj = gdf.to_crs(epsg=3857).geometry.centroid.to_crs(epsg=4326)
            gdf["real_lat"] = centroids_proj.y
            gdf["real_lon"] = centroids_proj.x

        # Simplify geometry for fast browser rendering
        if simplify_tolerance > 0:
            gdf["geometry"] = gdf["geometry"].simplify(tolerance=simplify_tolerance, preserve_topology=True)

        res = gdf[["real_geoid", "county", "real_lat", "real_lon", "geometry"]].sort_values("real_geoid").reset_index(drop=True)
        _cached_gdf = res
        return res
    except Exception as e:
        print(f"[geo] Error loading boundary shapefile ({e}). Falling back to centroid map.")
        return None


def get_deterministic_mapping(synthetic_tract_ids: list, seed: int = 42) -> Optional[Dict[str, str]]:
    """Deterministically map synthetic tract IDs to real California GEOIDs."""
    if GEOID_MAP_PATH.exists():
        try:
            cached = json.loads(GEOID_MAP_PATH.read_text()).get("mapping", {})
            if all(tid in cached for tid in synthetic_tract_ids):
                return cached
        except Exception:
            pass

    gdf = load_real_tract_geometries()
    if gdf is None or len(gdf) == 0:
        return None

    rng = np.random.default_rng(seed)
    n = len(synthetic_tract_ids)
    all_geoids = sorted(gdf["real_geoid"].unique())
    if len(all_geoids) >= n:
        sampled_geoids = rng.choice(all_geoids, size=n, replace=False)
    else:
        sampled_geoids = rng.choice(all_geoids, size=n, replace=True)

    mapping = dict(zip(synthetic_tract_ids, sampled_geoids))
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(GEOID_MAP_PATH, "w") as f:
        json.dump({"note": "placeholder-to-real-geometry mapping", "seed": seed, "mapping": mapping}, f, indent=2)
    return mapping


def build_pydeck_geojson(df_display: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Build a GeoJSON FeatureCollection dict with polygon geometries and tract properties for pydeck."""
    gdf = load_real_tract_geometries()
    if gdf is None or len(gdf) == 0:
        return None

    try:
        import geopandas as gpd
        df = df_display.copy()
        if "real_geoid" not in df.columns or df["real_geoid"].isna().any():
            mapping = get_deterministic_mapping(df["tract_id"].tolist(), seed=config.SEED)
            if mapping:
                df["real_geoid"] = df["tract_id"].map(mapping)
            else:
                return None

        merged = gdf.merge(df, on="real_geoid", how="inner")
        if merged.empty:
            return None

        # Clean non-serializable columns
        drop_cols = [c for c in merged.columns if c in ["county_x", "county_y"] and c != "county"]
        if drop_cols:
            merged = merged.drop(columns=drop_cols)

        merged_gdf = gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:4326")
        geojson_str = merged_gdf.to_json()
        return json.loads(geojson_str)
    except Exception as e:
        print(f"[geo] Failed to build GeoJSON ({e})")
        return None
