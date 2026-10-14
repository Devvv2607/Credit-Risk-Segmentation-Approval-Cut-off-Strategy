import pytest

from src import claims as C
from src.common import path, read_json


def test_every_claim_renders_and_matches():
    C._load.cache_clear()
    reg = C.load_registry()
    rendered = {c["id"]: c for c in read_json(path("outputs") / "claims_rendered.json")["claims"]}
    assert set(rendered) == {c["id"] for c in reg["claims"]}
    for c in reg["claims"]:
        text, values = C.render(c["template"], c["metrics"])
        assert rendered[c["id"]]["text"] == text
        for name, v in values.items():
            # the stored raw value equals the metric file's value right now
            assert rendered[c["id"]]["values"][name]["raw"] == C.resolve(c["metrics"][name])
            assert v["formatted"] in text


def test_templates_contain_no_digits():
    """Numbers must come from metrics, never typed into a template."""
    reg = C.load_registry()
    import re

    for c in reg["claims"]:
        assert not re.search(r"\d", re.sub(r"{\w+}", "", c["template"]).replace("EXT_SOURCE_3", "")), c["id"]


def test_missing_metric_fails():
    C._load.cache_clear()
    with pytest.raises(C.MissingMetric):
        C.render("{x}", {"x": {"source": "metrics.json", "path": "does.not.exist", "format": "num3"}})


def test_terminology_in_claims_and_bullets():
    text = (path("outputs") / "claims_rendered.json").read_text(encoding="utf-8").lower()
    text += (path("outputs") / "resume_bullets.md").read_text(encoding="utf-8").lower()
    assert "default rate" not in text and "bad rate" not in text
