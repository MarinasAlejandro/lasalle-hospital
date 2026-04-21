"""Pydantic response schemas for the API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Admission(BaseModel):
    model_config = ConfigDict(extra="ignore")

    patient_external_id: str | None = None
    admission_date: str | None = None
    discharge_date: str | None = None
    department: str | None = None
    diagnosis_code: str | None = None
    diagnosis_description: str | None = None
    diagnosis_category: str | None = None
    status: str | None = None


class Radiography(BaseModel):
    model_config = ConfigDict(extra="ignore")

    patient_external_id: str | None = None
    minio_object_key: str
    original_filename: str | None = None
    file_size_bytes: int | None = None
    ingested_at: str | None = None
    classification: str | None = None


class Patient(BaseModel):
    model_config = ConfigDict(extra="ignore")

    external_id: str
    name: str | None = None
    birth_date: str | None = None
    age: int | None = None
    gender: str | None = None
    blood_type: str | None = None
    admissions: list[Admission] = Field(default_factory=list)
    radiographies: list[Radiography] = Field(default_factory=list)


class Page(BaseModel):
    total: int
    limit: int
    offset: int


class PatientsPage(Page):
    items: list[Patient]


class AdmissionsPage(Page):
    items: list[Admission]


class RadiographiesPage(Page):
    items: list[Radiography]


class PipelineRun(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(alias="_id")
    trigger_type: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    records_processed: int = 0
    records_rejected: int = 0
    images_processed: int = 0
    error_message: str | None = None


class PipelineRunsPage(Page):
    items: list[PipelineRun]


class PipelineTriggerResponse(BaseModel):
    run_id: str
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
