from typing import List, Optional, Literal
import json

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class JobBase(BaseModel):
    title: str = Field(..., max_length=300)
    description: Optional[str] = None
    department_id: Optional[str] = None
    hiring_manager_id: Optional[str] = None
    skills: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    remote_type: Optional[Literal["onsite", "remote", "hybrid"]] = Field(
        None, description="onsite|remote|hybrid"
    )
    status: Optional[Literal["draft", "published", "closed"]] = Field(
        "draft", description="draft|published|closed"
    )
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    currency: Optional[str] = None

    @field_validator("skills", "locations", mode="before")
    @classmethod
    def parse_json_text_lists(cls, value):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @model_validator(mode="after")
    def check_salary_bounds(self):
        if self.min_salary is not None and self.min_salary < 0:
            raise ValueError("min_salary must be non-negative")
        if self.max_salary is not None and self.max_salary < 0:
            raise ValueError("max_salary must be non-negative")
        if self.min_salary is not None and self.max_salary is not None:
            if self.min_salary > self.max_salary:
                raise ValueError("min_salary cannot be greater than max_salary")
        return self


class JobCreate(JobBase):
    pass


class JobUpdate(JobBase):
    title: Optional[str] = None


class JobOut(JobBase):
    id: str

    model_config = ConfigDict(from_attributes=True)
