"""Verificaciones de las salidas de modelado y evaluación. Requieren haber ejecutado el pipeline completo."""

import json

import pandas as pd
import pytest

from src.config import load_config, path

EV = path("evaluation")


@pytest.mark.skipif(not (EV / "evaluation_core.json").exists(), reason="evaluación no ejecutada")
def test_evaluation_core_consistent():
    r = json.loads((EV / "evaluation_core.json").read_text())
    h = load_config()["hypotheses"]
    assert r["H1"]["rejected"] == (r["H1"]["nmi_fine_group_h2"] >= h["h1_max_nmi_fine_position"])
    assert 0 <= r["H3"]["temporal_same_profile_share"] <= 1
    assert sum(r["reserve"]["cluster_sizes_h2"]) == r["n_h2"]


@pytest.mark.skipif(not (path("models") / "selected_model.json").exists(), reason="selección no ejecutada")
def test_selected_model_meets_protocol():
    s = json.loads((path("models") / "selected_model.json").read_text())
    h = load_config()["hypotheses"]
    assert s["ari_mean"] >= h["h3_min_mean_ari"]
    assert s["nmi_team"] < h["max_nmi_team"]


@pytest.mark.skipif(
    not (path("models") / "profiles_full_assignments.parquet").exists(), reason="perfiles no generados"
)
def test_profiles_cover_population():
    a = pd.read_parquet(path("models") / "profiles_full_assignments.parquet")
    f = pd.read_parquet(path("features") / "player_features_full.parquet")
    assert len(a) == int(f.eligible.sum())
    assert a.profile.notna().all()
