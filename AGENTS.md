# AGENTS.md

## Propósito del proyecto

Imagen Report es una aplicación web para crear informes radiológicos odontológicos. El flujo
busca datos del paciente en una Google Sheet de solo lectura, captura un dictado y genera con un
modelo de IA seleccionable un borrador técnico. Luego exige revisión y aprobación profesional,
crea un Google Doc desde una
plantilla, exporta un PDF a Drive y puede crear opcionalmente un borrador de Gmail con el PDF
adjunto.

La interfaz y la documentación para usuarios están en español.

## Arquitectura

- `frontend/`: React 19, Vite, TypeScript y Tailwind CSS.
- `backend/`: FastAPI, SQLAlchemy, Pydantic, PostgreSQL e integraciones externas.
- `deploy/`: configuración de Caddy.
- `docker-compose.yml`: servicios `db`, `backend`, `frontend` y `proxy`.
- `CONFIGURACION_LOCAL.md`: guía operativa completa y fuente principal para preparar el entorno.
- `.env.example`: plantilla de variables; `.env` contiene secretos locales y no se debe leer,
  imprimir, modificar ni versionar salvo petición explícita del usuario.
- `secrets/`: credenciales locales ignoradas por Git; Docker la monta como `/run/secrets:ro`.

La aplicación normal usa PostgreSQL 17. SQLite solo está permitido con `APP_ENV=test` para la
suite automatizada.

## Flujo funcional que debe conservarse

1. Un usuario interno introduce usuario y contraseña.
2. La aplicación envía un OTP al correo autorizado; en desarrollo también lo muestra en pantalla.
3. El usuario elige una pestaña visible de la Google Sheet y busca allí los datos del paciente. La
   pestaña se recuerda por usuario en el navegador; el archivo y el rango de celdas continúan
   configurados en el backend y la integración sigue siendo de solo lectura. También puede cargar
   el número de fila exacto de Google Sheets para distinguir estudios repetidos del mismo paciente.
4. El navegador captura el dictado mediante reconocimiento de voz; el audio no se conserva.
5. El usuario elige entre los modelos de Gemini y OpenAI habilitados; la elección se recuerda por
   usuario en el navegador. El backend valida la selección, envía el texto al proveedor
   correspondiente y devuelve un borrador técnico.
6. El profesional edita el informe y debe aprobarlo expresamente.
7. El backend copia una plantilla nativa de Google Docs, reemplaza marcadores, exporta el PDF y
   guarda ambos en la carpeta configurada de Drive.
8. Si Gmail está habilitado y el usuario marca la opción, se crea un borrador con el PDF adjunto.
   Nunca se envía automáticamente.
9. El usuario puede limpiar la pantalla con **Nuevo informe**; esto no elimina archivos de Drive.

No hay registro público ni historial de informes dentro de la aplicación.

## Contrato de datos heredado

Mantener estos nombres y su capitalización porque reproducen el formulario y el flujo anterior:

- `recordData`: texto pegado con nombre, médico y cédula separados por tabuladores.
- `ciPaciente`: cédula del paciente.
- `nombrePaciente`: nombre del paciente.
- `doctor_gender`: `Dr.` o `Dra.`.
- `doctor`: profesional solicitante.
- `fecha`: fecha del informe.
- `measures`: medidas en milímetros.
- `texto`: informe revisado.
- `driveUrl`: enlace al estudio, leído desde la columna `L` de la pestaña seleccionada y editable
  antes de publicar.
- `recipientEmail`: correo destinatario leído de la Sheet o introducido manualmente.
- `createGmailDraft`: elección opcional por informe.
- `approved`: aprobación médica explícita.

Los marcadores de la plantilla están definidos en
`backend/app/services/google_publisher.py`. Son sensibles a mayúsculas y espacios. La plantilla
debe ser un documento nativo de Google Docs, no un `.docx` almacenado en Drive.

## Persistencia y privacidad

- PostgreSQL guarda usuarios, desafíos OTP y sesiones.
- No guardar audio, transcripciones, informes, Docs ni PDF en PostgreSQL.
- La Google Sheet es solo lectura.
- Los documentos finales se conservan en Google Drive.
- No ampliar la persistencia clínica sin una decisión explícita del usuario.
- No registrar payloads médicos, tokens, contraseñas, claves API ni contenido de credenciales.

## Autenticación y usuarios

- No existe registro público.
- Los administradores gestionan usuarios desde el botón **Usuarios**.
- Rutas administrativas: `GET/POST/PATCH /api/admin/users` y
  `POST /api/admin/users/{id}/reset-password`.
- Solo administradores pueden usar esas rutas.
- Debe permanecer al menos un administrador activo.
- Un administrador no puede desactivarse ni quitarse su propio rol.
- Desactivar un usuario o restablecer su contraseña revoca sesiones y OTP pendientes.
- Cambiar `BOOTSTRAP_ADMIN_*` no actualiza un usuario ya creado; esas variables solo crean el
  administrador inicial si todavía no existe.

En `.env`, los valores con `$` deben ir entre comillas simples para evitar que Docker Compose los
interprete, por ejemplo `BOOTSTRAP_ADMIN_PASSWORD='valor$con$dolares'`.

## Integraciones de Google

Hay dos credenciales separadas:

- `/run/secrets/google-service-account.json`: cuenta de servicio con permiso de lector sobre la
  Google Sheet.
- `/run/secrets/google-oauth-client.json`: cliente OAuth de escritorio usado por el script local
  para obtener el refresh token de Docs, Drive y Gmail opcional.

La cuenta Google que autorizó OAuth debe poder copiar la plantilla y escribir en la carpeta de
salida. Los valores `GOOGLE_DOCS_TEMPLATE_ID` y `GOOGLE_DRIVE_OUTPUT_FOLDER_ID` son IDs, no nombres.

`GMAIL_DRAFT_ENABLED=false` desactiva toda la función de borrador. Con `true`, sigue siendo opcional
para cada informe. `gmail.compose` permite crear el borrador; no agregar envío automático.

La implementación actual usa los scopes restringidos `drive` y `gmail.compose`. Una audiencia
External en Testing sirve para desarrollo, pero no es una solución operativa estable porque su
refresh token puede caducar a los siete días. Revisar la sección 6.10 de
`CONFIGURACION_LOCAL.md` antes de preparar producción o cambiar estos scopes.

SMTP para OTP y OAuth de Gmail para borradores son integraciones independientes.

## Archivos principales del backend

- `backend/app/core/config.py`: variables, PostgreSQL y validaciones de entorno.
- `backend/app/core/database.py`: engine, sesión y base SQLAlchemy.
- `backend/app/api/auth.py`: contraseña, OTP y sesión.
- `backend/app/api/admin_users.py`: gestión administrativa de usuarios.
- `backend/app/api/patients.py`: búsqueda en la Sheet.
- `backend/app/api/reports.py`: generación y publicación.
- `backend/app/services/sheets.py`: lectura de Google Sheets.
- `backend/app/services/gemini.py`: transformación del texto con Gemini.
- `backend/app/services/openai_report.py`: transformación del texto con OpenAI.
- `backend/app/services/report_generator.py`: selección y enrutamiento del proveedor de IA.
- `backend/app/services/google_publisher.py`: Docs, Drive, PDF y Gmail.
- `backend/scripts/google_oauth_setup.py`: autorización local y obtención del refresh token.

## Archivos principales del frontend

- `frontend/src/App.tsx`: sesión y vista raíz.
- `frontend/src/components/LoginPanel.tsx`: acceso y OTP.
- `frontend/src/components/ReportWorkspace.tsx`: flujo completo del informe.
- `frontend/src/components/ReportDraftEditor.tsx`: edición, revisión y herramientas del borrador.
- `frontend/src/components/UserManagementPanel.tsx`: administración de usuarios.
- `frontend/src/lib/api.ts`: cliente HTTP.
- `frontend/src/lib/types.ts`: contrato TypeScript.
- `frontend/src/lib/speech.ts`: reconocimiento de voz del navegador.

## Convenciones para cambios

- Mantener FastAPI con dependencias `Depends`, schemas Pydantic y acceso SQLAlchemy.
- Mantener el contrato entre schemas Python y tipos TypeScript.
- Normalizar usuarios y correos como lo hacen los endpoints existentes.
- No exponer secretos ni integrar directamente claves en el frontend.
- No omitir la aprobación profesional antes de publicar.
- No introducir envío automático de Gmail.
- Mantener la búsqueda de Sheet sin escritura.
- Preservar cambios ajenos en un worktree sucio.
- Actualizar `CONFIGURACION_LOCAL.md`, `.env.example` y tests cuando cambie la configuración o el
  comportamiento operativo.

## Verificación requerida

Después de modificar el backend:

```bash
./.venv/bin/ruff check backend
./.venv/bin/pytest -q backend/tests
```

Después de modificar el frontend:

```bash
cd frontend
npm run lint
npm run build
```

Para validar el despliegue local:

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
curl http://localhost/api/health
```

La prueba manual debe cubrir acceso con OTP, consulta de paciente, dictado, generación, edición,
aprobación, creación de Doc/PDF y las dos variantes de Gmail: opción desmarcada y borrador creado.

## Límites operativos conocidos

- Chrome es el navegador previsto para el reconocimiento de voz.
- Una aplicación OAuth `External` en estado `Testing` puede entregar refresh tokens que caducan a
  los siete días; volver a ejecutar el asistente si ocurre durante pruebas.
- Un error 403/404 de Drive suele indicar un ID incorrecto o que la cuenta OAuth no tiene permiso.
- El error de plantilla Office requiere convertir el `.docx` a Google Docs nativo.
- Después de cambiar `.env`, recrear el backend para que vuelva a cargar la configuración.
