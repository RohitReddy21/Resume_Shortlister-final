import os
import sys
import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.pipeline import ApplicationStageUpdate, CommentCreate
from app.api.routers.pipeline import VALID_STAGES, PIPELINE_STAGES

def test_pipeline_stages():
    assert len(PIPELINE_STAGES) == 9
    assert "Applied" in VALID_STAGES
    assert "Screening" in VALID_STAGES
    assert "Shortlisted" in VALID_STAGES
    assert "Interview" in VALID_STAGES
    assert "Technical" in VALID_STAGES
    assert "HR" in VALID_STAGES
    assert "Offer" in VALID_STAGES
    assert "Hired" in VALID_STAGES
    assert "Rejected" in VALID_STAGES

def test_application_stage_update_validation():
    # Valid stages
    for stage in PIPELINE_STAGES:
        update = ApplicationStageUpdate(stage=stage)
        assert update.stage == stage

    # Invalid stage should raise ValidationError
    with pytest.raises(ValidationError):
        ApplicationStageUpdate(stage="InvalidStage")
