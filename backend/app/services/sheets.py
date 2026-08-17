import re
import unicodedata
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.core.config import Settings
from app.schemas.patient import PatientSummary
from app.services.errors import IntegrationFailed, IntegrationNotConfigured

READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


def normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", normalized.strip()).casefold()


class SheetsPatientReader:
    def __init__(self, settings: Settings):
        self.settings = settings

    def search(self, query: str, limit: int = 20) -> list[PatientSummary]:
        credential_file = self.settings.google_sheets_service_account_file
        if not credential_file or not Path(credential_file).is_file():
            raise IntegrationNotConfigured(
                "No se encontró la cuenta de servicio de Google Sheets configurada para lectura."
            )

        credentials = Credentials.from_service_account_file(
            credential_file,
            scopes=[READONLY_SCOPE],
        )
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

        try:
            result = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self.settings.google_sheet_id,
                    range=self.settings.google_sheet_range,
                )
                .execute()
            )
        except Exception as exc:  # Google clients expose several transport-specific errors.
            raise IntegrationFailed("No fue posible leer la Google Sheet.") from exc

        values: list[list[str]] = result.get("values", [])
        if not values:
            return []

        headers = [normalize_header(str(value)) for value in values[0]]
        required = {
            "name": normalize_header(self.settings.sheet_patient_name_header),
            "patient_id": normalize_header(self.settings.sheet_patient_id_header),
            "doctor": normalize_header(self.settings.sheet_doctor_header),
            "email": normalize_header(self.settings.sheet_recipient_email_header),
        }
        indexes = {
            key: headers.index(header) if header in headers else None
            for key, header in required.items()
        }

        missing = [key for key in ("name", "patient_id", "doctor") if indexes[key] is None]
        if missing:
            raise IntegrationFailed(
                "La hoja no contiene todas las columnas requeridas: " + ", ".join(missing)
            )

        query_normalized = normalize_header(query)
        start_row = self._range_start_row()
        matches: list[PatientSummary] = []
        for offset, row in enumerate(values[1:], start=1):
            padded = row + [""] * max(0, len(headers) - len(row))
            name = str(padded[indexes["name"]]).strip()  # type: ignore[index]
            patient_id = str(padded[indexes["patient_id"]]).strip()  # type: ignore[index]
            doctor = str(padded[indexes["doctor"]]).strip()  # type: ignore[index]
            email_index = indexes["email"]
            email = str(padded[email_index]).strip() if email_index is not None else ""

            haystack = normalize_header(f"{name} {patient_id} {doctor}")
            if query_normalized not in haystack:
                continue
            matches.append(
                PatientSummary(
                    row_number=start_row + offset,
                    nombrePaciente=name,
                    ciPaciente=patient_id,
                    doctor=doctor,
                    recipientEmail=email or None,
                )
            )
            if len(matches) >= limit:
                break
        return matches

    def _range_start_row(self) -> int:
        match = re.search(r"![A-Z]+(\d+)", self.settings.google_sheet_range.upper())
        return int(match.group(1)) if match else 1
