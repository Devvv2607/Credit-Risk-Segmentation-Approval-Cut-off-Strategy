"""Shared fixtures. Tests read pipeline outputs and the local (gitignored) data/ files."""

import warnings

import pandas as pd
import pytest

from src.common import connect, load_settings, path, read_json

warnings.filterwarnings("ignore")


@pytest.fixture(scope="session")
def settings():
    return load_settings()


@pytest.fixture(scope="session")
def out():
    return path("outputs")


@pytest.fixture(scope="session")
def con():
    c = connect(read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="session")
def metrics(out):
    return read_json(out / "metrics.json")


@pytest.fixture(scope="session")
def scores():
    return pd.read_parquet(path("clean_dir") / "scores.parquet")


@pytest.fixture(scope="session")
def segments(out):
    return pd.read_csv(out / "segments.csv")


@pytest.fixture(scope="session")
def cutoff_table(out):
    return pd.read_csv(out / "cutoff_table.csv")
