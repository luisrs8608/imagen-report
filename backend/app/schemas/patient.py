from pydantic import BaseModel, EmailStr


class PatientSummary(BaseModel):
    row_number: int
    nombrePaciente: str
    ciPaciente: str
    doctor: str
    recipientEmail: EmailStr | None = None
    driveUrl: str | None = None


class SheetSelectionResponse(BaseModel):
    sheets: list[str]
    default_sheet: str
