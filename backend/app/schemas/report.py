from datetime import date

from pydantic import BaseModel, EmailStr, Field, model_validator


class GenerateReportRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=30_000)


class GenerateReportResponse(BaseModel):
    report: str


class PublishReportRequest(BaseModel):
    ciPaciente: str = Field(min_length=1, max_length=80)
    nombrePaciente: str = Field(min_length=1, max_length=250)
    doctor_gender: str = Field(pattern=r"^(Dr\.|Dra\.)$")
    doctor: str = Field(min_length=1, max_length=250)
    fecha: date
    measures: str = Field(min_length=1, max_length=100)
    texto: str = Field(min_length=1, max_length=50_000)
    driveUrl: str = Field(min_length=1, max_length=2_000)
    recipientEmail: EmailStr | None = None
    createGmailDraft: bool = False
    approved: bool = False

    @model_validator(mode="after")
    def validate_publish_rules(self) -> "PublishReportRequest":
        if not self.approved:
            raise ValueError("El informe debe estar aprobado antes de publicarse.")
        if self.createGmailDraft and not self.recipientEmail:
            raise ValueError("El correo destinatario es obligatorio para crear el borrador.")
        return self


class PublishReportResponse(BaseModel):
    document_id: str
    document_url: str
    pdf_id: str
    pdf_url: str
    gmail_draft_id: str | None = None
