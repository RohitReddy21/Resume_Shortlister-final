import os
import sys

# Ensure the backend project root is on sys.path so `app` package imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from pydantic import ValidationError

from app.schemas.anonymize import MaskPolicy, TaskResponse


def test_maskpolicy_conflicting_image_options():
    # image_blur and image_remove cannot both be True
    with pytest.raises(ValidationError):
        MaskPolicy(image_blur=True, image_remove=True)


def test_maskpolicy_defaults_and_bounds():
    p = MaskPolicy()
    assert p.pseudonymize is True
    assert p.image_blur is True
    assert p.image_blur_radius == 12

    # invalid blur radius should raise
    with pytest.raises(ValidationError):
        MaskPolicy(image_blur_radius=-1)
    with pytest.raises(ValidationError):
        MaskPolicy(image_blur_radius=1000)


def test_taskresponse_serialization():
    tr = TaskResponse(task_id="abc-123", status="completed")
    d = tr.model_dump()
    assert d["task_id"] == "abc-123"
    assert d["status"] == "completed"

    j = tr.model_dump_json()
    assert "abc-123" in j
