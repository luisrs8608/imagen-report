import re
import unicodedata
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.config import Settings
from app.schemas.patient import PatientSummary, SheetSelectionResponse
from app.services.errors import IntegrationFailed, IntegrationNotConfigured

READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
EMAIL_ADAPTER = TypeAdapter(EmailStr)
EMAIL_CANDIDATE_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
    re.IGNORECASE,
)


def normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", normalized.strip()).casefold()


def parse_configured_range(configured_range: str) -> tuple[str, str]:
    """Return the configured default sheet title and the reusable cell range."""
    if "!" not in configured_range:
        return "", configured_range.strip()
    raw_title, data_range = configured_range.rsplit("!", maxsplit=1)
    raw_title = raw_title.strip()
    if raw_title.startswith("'") and raw_title.endswith("'"):
        raw_title = raw_title[1:-1].replace("''", "'")
    return raw_title, data_range.strip()


def build_sheet_range(sheet_title: str, data_range: str) -> str:
    escaped_title = sheet_title.replace("'", "''")
    return f"'{escaped_title}'!{data_range}"


def extract_valid_email(value: str) -> str | None:
    """Return a valid address from a cell or None when it only contains notes."""
    stripped_value = value.strip()
    if not stripped_value:
        return None

    candidates = [stripped_value, *EMAIL_CANDIDATE_PATTERN.findall(stripped_value)]
    for candidate in dict.fromkeys(candidates):
        try:
            return str(EMAIL_ADAPTER.validate_python(candidate))
        except ValidationError:
            continue
    return None


class SheetsPatientReader:
    def __init__(self, settings: Settings):
        self.settings = settings

    def list_sheets(self) -> SheetSelectionResponse:
        service = self._service()
        try:
            sheet_titles = self._sheet_titles(service)
        except Exception as exc:  # Google clients expose several transport-specific errors.
            raise IntegrationFailed("No fue posible consultar las hojas disponibles.") from exc

        if not sheet_titles:
            raise IntegrationFailed("La Google Sheet no contiene hojas visibles para seleccionar.")

        configured_sheet, _ = parse_configured_range(self.settings.google_sheet_range)
        default_sheet = configured_sheet if configured_sheet in sheet_titles else sheet_titles[0]
        return SheetSelectionResponse(sheets=sheet_titles, default_sheet=default_sheet)

    def search(
        self,
        query: str,
        sheet_name: str | None = None,
        limit: int = 20,
    ) -> list[PatientSummary]:
        values, data_range = self._read_values(sheet_name)
        if not values:
            return []

        headers, indexes = self._column_indexes(values[0])

        query_normalized = normalize_header(query)
        start_row = self._range_start_row(data_range)
        matches: list[PatientSummary] = []
        for offset, row in enumerate(values[1:], start=1):
            patient = self._patient_from_row(
                row=row,
                headers=headers,
                indexes=indexes,
                row_number=start_row + offset,
            )
            if patient is None:
                continue
            haystack = normalize_header(
                f"{patient.nombrePaciente} {patient.ciPaciente} {patient.doctor}"
            )
            if query_normalized not in haystack:
                continue
            matches.append(patient)
            if len(matches) >= limit:
                break
        return matches

    def get_by_row(
        self,
        row_number: int,
        sheet_name: str | None = None,
    ) -> PatientSummary | None:
        values, data_range = self._read_values(sheet_name)
        if not values:
            return None

        start_row = self._range_start_row(data_range)
        if row_number <= start_row:
            raise IntegrationFailed(
                f"La fila debe ser posterior a la fila de encabezados ({start_row})."
            )

        offset = row_number - start_row
        if offset >= len(values):
            return None

        headers, indexes = self._column_indexes(values[0])
        return self._patient_from_row(
            row=values[offset],
            headers=headers,
            indexes=indexes,
            row_number=row_number,
        )

    def _read_values(self, sheet_name: str | None) -> tuple[list[list[str]], str]:
        service = self._service()
        configured_sheet, data_range = parse_configured_range(self.settings.google_sheet_range)

        try:
            sheet_titles = self._sheet_titles(service)
            if sheet_name:
                selected_sheet = sheet_name
            elif configured_sheet in sheet_titles:
                selected_sheet = configured_sheet
            else:
                selected_sheet = sheet_titles[0] if sheet_titles else ""
            if selected_sheet not in sheet_titles:
                raise IntegrationFailed("La hoja seleccionada no existe o no está disponible.")

            selected_range = build_sheet_range(selected_sheet, data_range)
            result = (
                service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self.settings.google_sheet_id,
                    range=selected_range,
                )
                .execute()
            )
        except IntegrationFailed:
            raise
        except Exception as exc:  # Google clients expose several transport-specific errors.
            raise IntegrationFailed("No fue posible leer la Google Sheet.") from exc

        return result.get("values", []), data_range

    def _column_indexes(
        self,
        header_row: list[str],
    ) -> tuple[list[str], dict[str, int | None]]:
        headers = [normalize_header(str(value)) for value in header_row]
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
        return headers, indexes

    def _patient_from_row(
        self,
        *,
        row: list[str],
        headers: list[str],
        indexes: dict[str, int | None],
        row_number: int,
    ) -> PatientSummary | None:
        padded = row + [""] * max(0, len(headers) - len(row))
        name = str(padded[indexes["name"]]).strip()  # type: ignore[index]
        patient_id = str(padded[indexes["patient_id"]]).strip()  # type: ignore[index]
        doctor = str(padded[indexes["doctor"]]).strip()  # type: ignore[index]
        if not any((name, patient_id, doctor)):
            return None

        email_index = indexes["email"]
        email_cell = str(padded[email_index]) if email_index is not None else ""
        return PatientSummary(
            row_number=row_number,
            nombrePaciente=name,
            ciPaciente=patient_id,
            doctor=doctor,
            recipientEmail=extract_valid_email(email_cell),
        )

    def _service(self):
        credential_file = self.settings.google_sheets_service_account_file
        if not credential_file or not Path(credential_file).is_file():
            raise IntegrationNotConfigured(
                "No se encontró la cuenta de servicio de Google Sheets configurada para lectura."
            )

        credentials = Credentials.from_service_account_file(
            credential_file,
            scopes=[READONLY_SCOPE],
        )
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def _sheet_titles(self, service) -> list[str]:
        metadata = (
            service.spreadsheets()
            .get(
                spreadsheetId=self.settings.google_sheet_id,
                fields="sheets.properties(title,index,hidden)",
            )
            .execute()
        )
        sheets = sorted(
            metadata.get("sheets", []),
            key=lambda item: item.get("properties", {}).get("index", 0),
        )
        return [
            str(item["properties"]["title"])
            for item in sheets
            if not item.get("properties", {}).get("hidden", False)
        ]

    def _range_start_row(self, data_range: str) -> int:
        match = re.search(r"^[A-Z]+(\d+)", data_range.upper())
        return int(match.group(1)) if match else 1
