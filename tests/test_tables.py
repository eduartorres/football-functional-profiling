"""Verificaciones de consistencia de las tablas derivadas. Requieren haber ejecutado el pipeline."""
import numpy as np
import pandas as pd
import pytest

from src.common.config import load_config, path

PM = path("interim") / "wyscout" / "player_match.parquet"
FULL = path("features") / "player_features_full.parquet"


@pytest.fixture(scope="module")
def pm():
    return pd.read_parquet(PM)


@pytest.fixture(scope="module")
def full():
    return pd.read_parquet(FULL)


def test_minutes_bounds(pm):
    assert (pm.minutes >= 0).all()
    assert (pm.minutes <= pm.match_minutes + 1e-9).all()


def test_players_on_pitch(pm):
    # 11 jugadores por equipo como máximo; menos solo por expulsiones
    r = pm.groupby(["match_id", "team_id"]).minutes.sum() / pm.groupby(["match_id", "team_id"]).match_minutes.first()
    assert r.max() <= 11 + 1e-6
    assert r.mean() > 10.9


def test_possession_sums_to_one():
    tm = pd.read_parquet(path("interim") / "wyscout" / "team_match.parquet")
    s = tm.groupby("match_id").possession_share.sum()
    assert np.allclose(s, 1)


def test_unique_keys(full):
    assert not full.duplicated(["player_id", "competition_file"]).any()


def test_composition(full):
    e = full[full.eligible]
    comp = e.filter(like="comp_").to_numpy()
    assert np.allclose(comp.sum(axis=1), 1)
    clr = e.filter(like="clr_").to_numpy()
    assert np.isfinite(clr).all()
    assert np.allclose(clr.sum(axis=1), 0)


def test_eligibility_rules(full):
    cfg = load_config()
    e = full[full.eligible]
    assert (e.minutes >= cfg["exposure"]["min_minutes"]).all()
    assert (e.role != "GK").all()
    assert e.fine_group.notna().all()
    assert e.competition_file.isin(cfg["core"]["competitions"]).all()


def test_volume_features_finite(full):
    v = full[full.eligible].filter(like="vol_")
    assert np.isfinite(v.to_numpy()).all()


def test_position_reference_unique_tm_id():
    r = pd.read_parquet(path("features") / "position_reference.parquet")
    linked = r[r.linked]
    assert not linked.tm_id.duplicated().any()
