"""Shapes the browser sees. Deliberately narrower than the upstream records."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Mirrors the upstream's accepted values (upstream/records_api/seed.py).
Sector = Literal["energy", "mining", "water", "transport", "oil_and_gas", "ict"]
Stage = Literal["idea", "feasibility", "tender", "financing", "construction", "operation", "cancelled"]
CompanyRole = Literal["owner", "developer", "epc_contractor", "financier", "consultant"]


class KeyDate(BaseModel):
    label: str = Field(min_length=1)
    date: date


class LinkedCompany(BaseModel):
    name: str
    role: CompanyRole


class Editable(BaseModel):
    """The fields a user can change from the edit form."""

    name: str = Field(min_length=1)
    sector: Sector
    country: str = Field(min_length=1)
    stage: Stage
    key_dates: list[KeyDate]

    @field_validator("key_dates")
    @classmethod
    def _labels_are_unique(cls, key_dates: list[KeyDate]) -> list[KeyDate]:
        # The merge treats each label as one field, so a label may appear once.
        labels = [kd.label for kd in key_dates]
        duplicates = sorted({label for label in labels if labels.count(label) > 1})
        if duplicates:
            raise ValueError(f"duplicate key date label: {', '.join(duplicates)}")
        return key_dates


class Conflict(BaseModel):
    """One field both the user and someone else changed, to different values."""

    field: str
    base: Any
    theirs: Any
    yours: Any


class SaveRequest(BaseModel):
    """`base` is what the form loaded; `yours` is what the form holds now."""

    base: Editable
    yours: Editable


class ProjectDetail(Editable):
    """One project as the edit form needs it. Linked companies are shown, not edited."""

    id: str
    linked_companies: list[LinkedCompany]


class ProjectSummary(BaseModel):
    """One row of the project list."""

    id: str
    name: str
    sector: Sector
    country: str
    stage: Stage
