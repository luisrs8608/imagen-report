"""Obtiene un refresh token OAuth para una cuenta Google."""

import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

DOCUMENT_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]
GMAIL_DRAFT_SCOPE = "https://www.googleapis.com/auth/gmail.compose"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Autoriza Google Drive y Docs, opcionalmente Gmail, y muestra las variables para .env."
        )
    )
    parser.add_argument(
        "client_secrets_file",
        type=Path,
        help="JSON descargado del cliente OAuth de tipo Aplicación de escritorio.",
    )
    parser.add_argument(
        "--with-gmail",
        action="store_true",
        help="Solicita además permiso para crear borradores de Gmail.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(args.client_secrets_file.read_text(encoding="utf-8"))
    client_config = payload.get("installed") or payload.get("web")
    if not client_config:
        raise SystemExit("El JSON no contiene una configuración OAuth válida.")

    scopes = [*DOCUMENT_SCOPES, *([GMAIL_DRAFT_SCOPE] if args.with_gmail else [])]
    flow = InstalledAppFlow.from_client_secrets_file(str(args.client_secrets_file), scopes)
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        access_type="offline",
        prompt="consent",
        authorization_prompt_message="Abriendo Google para autorizar la cuenta institucional...",
        success_message="Autorización completada. Puedes cerrar esta pestaña.",
    )
    if not credentials.refresh_token:
        raise SystemExit(
            "Google no devolvió un refresh token. Revoca el acceso anterior y ejecuta de nuevo."
        )

    print("\nCopia estas líneas en el archivo .env:\n")
    print(f"GOOGLE_OAUTH_CLIENT_ID={client_config['client_id']}")
    print(f"GOOGLE_OAUTH_CLIENT_SECRET={client_config['client_secret']}")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={credentials.refresh_token}")


if __name__ == "__main__":
    main()
