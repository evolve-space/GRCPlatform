import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.core.risk_scoring import clasificar_nivel
from app.models.risk import RiskStatus, RiskTreatment


class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    asset_id: uuid.UUID | None = None
    category: str = Field(min_length=1, max_length=255)
    threat: str = Field(min_length=1, max_length=255)
    vulnerability: str = Field(min_length=1, max_length=255)
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    treatment: RiskTreatment
    owner: str = Field(min_length=1, max_length=255)
    review_date: date
    status: RiskStatus = RiskStatus.IDENTIFIED
    residual_likelihood: int | None = Field(default=None, ge=1, le=5)
    residual_impact: int | None = Field(default=None, ge=1, le=5)
    comments: str | None = None

    @model_validator(mode="after")
    def _residual_ambos_o_ninguno(self) -> "RiskCreate":
        tiene_alguno = self.residual_likelihood is not None or self.residual_impact is not None
        tiene_ambos = self.residual_likelihood is not None and self.residual_impact is not None
        if tiene_alguno and not tiene_ambos:
            raise ValueError(
                "Para calcular el riesgo residual se necesitan tanto la probabilidad como el impacto residual."
            )
        return self


class RiskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    asset_id: uuid.UUID | None = None
    category: str | None = Field(default=None, min_length=1, max_length=255)
    threat: str | None = Field(default=None, min_length=1, max_length=255)
    vulnerability: str | None = Field(default=None, min_length=1, max_length=255)
    likelihood: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    treatment: RiskTreatment | None = None
    owner: str | None = Field(default=None, min_length=1, max_length=255)
    review_date: date | None = None
    status: RiskStatus | None = None
    residual_likelihood: int | None = Field(default=None, ge=1, le=5)
    residual_impact: int | None = Field(default=None, ge=1, le=5)
    comments: str | None = None


class RiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    description: str | None
    asset_id: uuid.UUID | None
    category: str
    threat: str
    vulnerability: str
    likelihood: int
    impact: int
    inherent_score: int
    treatment: RiskTreatment
    owner: str
    review_date: date
    status: RiskStatus
    residual_likelihood: int | None
    residual_impact: int | None
    residual_score: int | None
    comments: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def inherent_level(self) -> str:
        return clasificar_nivel(self.inherent_score)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def residual_level(self) -> str | None:
        if self.residual_score is None:
            return None
        return clasificar_nivel(self.residual_score)
