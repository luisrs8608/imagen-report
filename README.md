# Imagen Report

Aplicación web para generar informes radiológicos odontológicos a partir de un dictado, revisarlos profesionalmente y publicarlos mediante una plantilla institucional de Google Docs.

## Flujo funcional

1. Un usuario interno inicia sesión con contraseña y un código enviado a su correo autorizado.
2. Selecciona visualmente la pestaña o período de la Google Sheet y busca allí al paciente por nombre, cédula o médico. También puede cargar una fila exacta cuando existen registros repetidos. El enlace del estudio se completa desde la columna `L`.
3. Dicta el informe mediante el reconocimiento de voz del navegador y puede corregir la transcripción.
4. FastAPI envía únicamente el texto a Gemini para producir un borrador técnico.
5. El profesional edita y aprueba expresamente el informe.
6. El backend copia la plantilla de Google Docs, reemplaza los marcadores, exporta un PDF y guarda ambos archivos en Drive.
7. Si la integración Gmail está habilitada, permite crear opcionalmente un borrador con el PDF adjunto. Nunca envía el correo automáticamente.

No existe registro público. Los administradores crean y gestionan los usuarios autorizados desde
el botón **Usuarios** de la aplicación.

La aplicación no conserva audios, informes ni PDF en su base de datos. Los documentos finales permanecen en Google Drive.

## Campos conservados

- `recordData`: ayuda para pegar nombre, médico y cédula separados por tabuladores.
- `ciPaciente`: cédula de identidad.
- `nombrePaciente`: nombre del paciente.
- `doctor_gender`: `Dr.` o `Dra.`.
- `doctor`: médico solicitante.
- `fecha`: fecha del informe.
- `measures`: medidas en milímetros.
- `texto`: informe revisado.
- `driveUrl`: enlace al estudio en Google Drive.

Se añadieron `recipientEmail`, `createGmailDraft` y `approved` para cubrir el correo opcional y la aprobación médica explícita.

## Estructura

```text
backend/       FastAPI, autenticación, Gemini y APIs de Google
frontend/      React, Vite, TypeScript y Tailwind
deploy/        Proxy HTTPS
docker-compose.yml
```

## Desarrollo local

La aplicación utiliza PostgreSQL tanto en desarrollo como en producción. La conexión se arma con
las variables `POSTGRES_*` del archivo `.env`; SQLite está limitado a la suite automatizada de
tests y no es una opción de ejecución de la aplicación.

La guía completa, con valores, credenciales, comandos y verificaciones, está en
[CONFIGURACION_LOCAL.md](CONFIGURACION_LOCAL.md).

## Configuración externa

1. Copiar `.env.example` como `.env` y completar todos los valores indicados en la guía local.
2. Colocar la cuenta de servicio de lectura de Sheets fuera del repositorio, por ejemplo en `secrets/google-service-account.json`.
3. Compartir la Google Sheet con esa cuenta exclusivamente como lector.
4. Configurar las credenciales OAuth de una cuenta Google personal o Workspace para Docs y Drive.
5. Confirmar que la plantilla y la carpeta de salida sean accesibles por esa cuenta.
6. Si se desean borradores, habilitar Gmail en `.env` y autorizar también ese permiso.
7. Configurar SMTP para los códigos de acceso.

En producción se debe establecer `APP_ENV=production` y `COOKIE_SECURE=true`. El backend se negará a iniciar si detecta los secretos o la contraseña inicial de desarrollo.

Los identificadores actuales de la Sheet, la plantilla y la carpeta de Drive están reflejados en `.env.example`; no se incluyen claves privadas ni tokens.

## Producción

El despliegue previsto utiliza Docker Compose con PostgreSQL y Caddy. Solo el proxy debe exponerse a la red. Antes de habilitar acceso externo se debe configurar un dominio, HTTPS, copias de seguridad y preferentemente una VPN o pasarela de acceso protegida.
