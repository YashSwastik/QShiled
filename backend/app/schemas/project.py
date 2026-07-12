"""
Pydantic v2 schemas for Organization, Project, Application.
"""
import re
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.schemas.common import OrmBase
from app.models.application import (
    BusinessCriticality,
    Environment,
    DataSensitivity,
    ConfidentialityRequirement,
)
from app.models.project import ProjectStatus


# ── Organization ──────────────────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    slug: Annotated[str, Field(min_length=1, max_length=255, pattern=r'^[a-z0-9-]+$')]
    description: str | None = None

    @field_validator('slug')
    @classmethod
    def slug_format(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('slug must be lowercase alphanumeric and hyphens only')
        return v


class OrganizationResponse(OrmBase):
    id: str
    name: str
    slug: str
    description: str | None
    created_at: datetime
    updated_at: datetime


# ── Project ───────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    organization_id: str
    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: str | None = None
    status: ProjectStatus = ProjectStatus.active


class ProjectUpdate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectResponse(OrmBase):
    id: str
    organization_id: str
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(OrmBase):
    total: int
    items: list[ProjectResponse]


# ── Application ───────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    project_id: str
    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: str | None = None
    tech_stack: str | None = Field(default=None, max_length=512)
    business_criticality: BusinessCriticality = BusinessCriticality.medium
    environment: Environment = Environment.production
    internet_exposed: bool = False
    data_sensitivity: DataSensitivity = DataSensitivity.internal
    confidentiality_requirement: ConfidentialityRequirement = ConfidentialityRequirement.medium_term
    data_lifetime_years: Annotated[int, Field(ge=1, le=100)] = 5
    owner_team: str | None = Field(default=None, max_length=255)


class ApplicationUpdate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)] | None = None
    description: str | None = None
    tech_stack: str | None = None
    business_criticality: BusinessCriticality | None = None
    environment: Environment | None = None
    internet_exposed: bool | None = None
    data_sensitivity: DataSensitivity | None = None
    confidentiality_requirement: ConfidentialityRequirement | None = None
    data_lifetime_years: Annotated[int, Field(ge=1, le=100)] | None = None
    owner_team: str | None = None


class ApplicationResponse(OrmBase):
    id: str
    project_id: str
    name: str
    description: str | None
    tech_stack: str | None
    business_criticality: BusinessCriticality
    environment: Environment
    internet_exposed: bool
    data_sensitivity: DataSensitivity
    confidentiality_requirement: ConfidentialityRequirement
    data_lifetime_years: int
    owner_team: str | None
    created_at: datetime
    updated_at: datetime


class ApplicationListResponse(OrmBase):
    total: int
    items: list[ApplicationResponse]
