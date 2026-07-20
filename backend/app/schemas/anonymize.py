from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MaskPolicy(BaseModel):
    pseudonymize: bool = Field(True, description="Replace PII with pseudonyms")
    image_blur: bool = Field(True, description="Blur images instead of removing")
    image_blur_radius: Optional[int] = Field(12, ge=0, le=200, description="Gaussian blur radius for images")
    image_remove: bool = Field(False, description="Remove images entirely instead of blurring")
    generate_pdf: bool = Field(True, description="Produce a masked PDF output")
    generate_docx: bool = Field(False, description="Produce a masked DOCX output")

    @model_validator(mode="after")
    def check_image_options(self):
        if self.image_remove and self.image_blur:
            raise ValueError("image_blur and image_remove cannot both be True")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "pseudonymize": True,
                "image_blur": True,
                "image_blur_radius": 12,
                "image_remove": False,
                "generate_pdf": True,
                "generate_docx": False,
            }
        }
    )


class TaskResponse(BaseModel):
    task_id: str
    status: str = Field("completed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"task_id": "b7f3c9e0-12ab-4cd3-9ef0-123456789abc", "status": "completed"}
        }
    )


class MaskedMetadata(BaseModel):
    masked_candidate_id: Optional[str]
    masked_pdf: Optional[str]
    masked_docx: Optional[str]
    mask_policy: Optional[Dict[str, Any]]
    masked_at: Optional[datetime]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "masked_candidate_id": "c3f1a2b4-5d6e-7f89-0123-abcdef456789",
                "masked_pdf": "uploads/resumes/12345_resume.pdf.masked.pdf",
                "masked_docx": None,
                "mask_policy": {
                    "pseudonymize": True,
                    "image_blur": True,
                    "image_blur_radius": 12,
                    "image_remove": False,
                    "generate_pdf": True,
                    "generate_docx": False,
                },
                "masked_at": "2026-07-06T12:34:56Z",
            }
        },
    )
