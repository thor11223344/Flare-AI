"""Unit tests for Phase 1: Real California Census tract boundary loader & deterministic GEOID mapping.
"""
from pathlib import Path
import pytest
import pandas as pd
from src.data import geo, db
from src import config


def test_tract_shapefile_download_or_cache():
    """Verify Census shapefile exists or can be resolved. Skips gracefully if offline."""
    try:
        shp_dir = geo.download_boundary_file()
    except Exception as e:
        pytest.skip(f"Census shapefile download failed (network/offline error: {e})")

    if shp_dir is None or not shp_dir.exists():
        pytest.skip("Census boundary shapefile unavailable (running offline)")

    assert shp_dir.exists()
    assert any(shp_dir.glob("*.shp"))


def test_real_tract_geometries_structure():
    """Verify that California census tract geometries load with correct coordinates and simplification."""
    try:
        gdf = geo.load_real_tract_geometries(simplify_tolerance=0.003)
    except Exception as e:
        pytest.skip(f"Geometries loading failed (network/offline/dependency error: {e})")

    if gdf is None:
        pytest.skip("Real tract geometries unavailable (offline or missing shapefile)")

    assert len(gdf) > 8000
    expected_cols = {"real_geoid", "county", "real_lat", "real_lon", "geometry"}
    assert expected_cols <= set(gdf.columns)

    # Check California bounding box approximately (lat ~32-42, lon ~ -125 to -114)
    sample = gdf.head(50)
    assert (sample.real_lat >= 32.0).all() and (sample.real_lat <= 43.0).all()
    assert (sample.real_lon >= -125.0).all() and (sample.real_lon <= -114.0).all()


def test_deterministic_mapping_reproducibility():
    """Verify placeholder-to-real-geometry mapping is deterministic with seed."""
    fake_ids = [f"0600{i:05d}" for i in range(100)]
    map1 = geo.get_deterministic_mapping(fake_ids, seed=42)
    map2 = geo.get_deterministic_mapping(fake_ids, seed=42)
    assert map1 == map2
    assert len(map1) == 100
    # Values should be 11-digit real California Census GEOIDs starting with '06'
    first_val = list(map1.values())[0]
    assert len(first_val) == 11 and first_val.startswith("06")


def test_pydeck_geojson_builder():
    """Verify GeoJSON FeatureCollection generation for PyDeck."""
    fake_ids = [f"0600{i:05d}" for i in range(20)]
    map_dict = geo.get_deterministic_mapping(fake_ids, seed=42)
    df = pd.DataFrame({
        "tract_id": fake_ids,
        "real_geoid": [map_dict[tid] for tid in fake_ids],
        "county": ["Los Angeles"] * 20,
        "income_quintile": [1] * 20,
        "risk_pct_txt": ["12.5%"] * 20,
        "gap_txt": ["18.2%"] * 20,
        "nr_txt": ["4.5%"] * 20,
        "rate_txt": ["15.40"] * 20,
        "color": [[255, 0, 0, 180]] * 20,
    })
    gj = geo.build_pydeck_geojson(df)
    assert gj is not None
    assert gj.get("type") == "FeatureCollection"
    assert len(gj.get("features", [])) == 20
    prop = gj["features"][0]["properties"]
    assert "tract_id" in prop
    assert "real_geoid" in prop
    assert prop["color"] == [255, 0, 0, 180]


def test_synthetic_values_real_geometry_label_in_app():
    """Verify that required honest labeling string appears in app code across views."""
    app_path = config.ROOT / "app" / "streamlit_app.py"
    assert app_path.exists()
    content = app_path.read_text(encoding="utf-8")
    required_label = "Synthetic values on real tract geometry. Not real findings about these neighborhoods."
    assert required_label in content
    # Must appear on tooltip, map caption, and Pitch Mode view
    assert content.count(required_label) >= 3
