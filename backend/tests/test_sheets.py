import pytest

from app.core.config import Settings
from app.services.errors import IntegrationFailed
from app.services.sheets import (
    SheetsPatientReader,
    build_sheet_range,
    extract_valid_email,
    parse_configured_range,
)


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class FakeValues:
    def __init__(self, payload):
        self.payload = payload
        self.requested_range = ""

    def get(self, *, spreadsheetId, range):
        assert spreadsheetId == "sheet-id"
        self.requested_range = range
        return FakeRequest(self.payload)


class FakeSpreadsheets:
    def __init__(self, *, sheets, values):
        self.sheets = sheets
        self.fake_values = FakeValues(values)

    def get(self, *, spreadsheetId, fields):
        assert spreadsheetId == "sheet-id"
        assert fields == "sheets.properties(title,index,hidden)"
        return FakeRequest({"sheets": self.sheets})

    def values(self):
        return self.fake_values


class FakeService:
    def __init__(self, spreadsheets):
        self.fake_spreadsheets = spreadsheets

    def spreadsheets(self):
        return self.fake_spreadsheets


def make_reader():
    return SheetsPatientReader(
        Settings(
            google_sheet_id="sheet-id",
            google_sheet_range="'Julio 2026'!A11:K",
        )
    )


def make_service():
    spreadsheets = FakeSpreadsheets(
        sheets=[
            {"properties": {"title": "Agosto 2026", "index": 1}},
            {"properties": {"title": "Oculta", "index": 2, "hidden": True}},
            {"properties": {"title": "Julio 2026", "index": 0}},
        ],
        values={
            "values": [
                ["NOMBRE", "CEDULA", "DR.", "ENVIO A..."],
                ["Ana Pérez", "123", "Dra. Silva", "destino@example.com"],
            ]
        },
    )
    return FakeService(spreadsheets)


def test_configured_range_can_be_reused_with_another_sheet():
    assert parse_configured_range("'Julio 2026'!A11:K") == ("Julio 2026", "A11:K")
    assert build_sheet_range("O'Brien", "A11:K") == "'O''Brien'!A11:K"


@pytest.mark.parametrize(
    ("cell_value", "expected"),
    [
        ("doctor@example.com", "doctor@example.com"),
        ("STL en carpeta- doctor@example.com", "doctor@example.com"),
        ("Faltó 29/5", None),
        ("", None),
    ],
)
def test_extracts_email_without_failing_on_notes(cell_value, expected):
    assert extract_valid_email(cell_value) == expected


def test_lists_visible_sheets_in_tab_order(monkeypatch):
    reader = make_reader()
    service = make_service()
    monkeypatch.setattr(reader, "_service", lambda: service)

    selection = reader.list_sheets()

    assert selection.sheets == ["Julio 2026", "Agosto 2026"]
    assert selection.default_sheet == "Julio 2026"


def test_search_reads_the_visually_selected_sheet(monkeypatch):
    reader = make_reader()
    service = make_service()
    monkeypatch.setattr(reader, "_service", lambda: service)

    patients = reader.search("Ana", sheet_name="Agosto 2026")

    assert service.fake_spreadsheets.fake_values.requested_range == "'Agosto 2026'!A11:K"
    assert patients[0].row_number == 12
    assert patients[0].nombrePaciente == "Ana Pérez"


def test_loads_the_exact_patient_row_from_the_selected_sheet(monkeypatch):
    reader = make_reader()
    service = make_service()
    monkeypatch.setattr(reader, "_service", lambda: service)

    patient = reader.get_by_row(12, sheet_name="Agosto 2026")

    assert service.fake_spreadsheets.fake_values.requested_range == "'Agosto 2026'!A11:K"
    assert patient is not None
    assert patient.row_number == 12
    assert patient.nombrePaciente == "Ana Pérez"


def test_exact_row_returns_none_when_it_is_outside_the_sheet(monkeypatch):
    reader = make_reader()
    monkeypatch.setattr(reader, "_service", make_service)

    assert reader.get_by_row(99, sheet_name="Julio 2026") is None


def test_exact_row_rejects_the_header_row(monkeypatch):
    reader = make_reader()
    monkeypatch.setattr(reader, "_service", make_service)

    with pytest.raises(IntegrationFailed, match="encabezados"):
        reader.get_by_row(11, sheet_name="Julio 2026")


def test_search_rejects_a_sheet_outside_the_spreadsheet(monkeypatch):
    reader = make_reader()
    monkeypatch.setattr(reader, "_service", make_service)

    with pytest.raises(IntegrationFailed, match="no existe"):
        reader.search("Ana", sheet_name="Otra hoja")


def test_search_falls_back_to_first_visible_sheet_when_default_was_deleted(monkeypatch):
    reader = SheetsPatientReader(
        Settings(
            google_sheet_id="sheet-id",
            google_sheet_range="'Hoja eliminada'!A11:K",
        )
    )
    service = make_service()
    monkeypatch.setattr(reader, "_service", lambda: service)

    reader.search("Ana")

    assert service.fake_spreadsheets.fake_values.requested_range == "'Julio 2026'!A11:K"
