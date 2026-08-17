# Configuración y prueba local de Imagen Report

Esta guía deja la aplicación completa funcionando en una computadora local con PostgreSQL. La
ruta recomendada es Docker Compose porque levanta PostgreSQL, FastAPI, React y el proxy con un
solo comando.

## 1. Qué se ejecuta

| Componente | Tecnología | Dirección local |
| --- | --- | --- |
| Interfaz | React + Vite, compilado en Nginx | `http://localhost` |
| API | FastAPI | `http://localhost/api` |
| Documentación de la API | FastAPI/OpenAPI | `http://localhost/api/docs` |
| Base de datos | PostgreSQL 17 | `127.0.0.1:5432` |
| Proxy local | Caddy en HTTP | puerto `80` |

PostgreSQL guarda únicamente usuarios, códigos temporales y sesiones. Los audios, informes y PDF
no se guardan en esta base. Los documentos finales quedan en Google Drive.

## 2. Requisitos previos

Instalar:

- Docker Desktop con Docker Compose.
- Google Chrome, necesario para el reconocimiento de voz del navegador.
- Python 3.12 o superior solo si se generará el token OAuth con el script incluido o si se
  ejecutarán los tests fuera de Docker.
- Node.js 22 solo para trabajar con el frontend fuera de Docker.

Comprobar Docker:

```bash
docker --version
docker compose version
```

Todos los comandos siguientes se ejecutan desde:

```bash
cd /Users/luisrs/Workspace/Personales/imagen_report
```

## 3. Crear el archivo de configuración

Crear `.env` a partir de la plantilla:

```bash
cp .env.example .env
```

El archivo `.env` es la única fuente de configuración local y está excluido de Git. No debe
enviarse por correo ni subirse al repositorio.

Generar dos secretos distintos:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Pegar el primer resultado en `APP_SECRET` y el segundo en `OTP_PEPPER`. Generar también una
contraseña de PostgreSQL:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Valores generales y PostgreSQL

| Variable | Valor para la prueba local | Explicación |
| --- | --- | --- |
| `APP_ENV` | `development` | Habilita documentación y muestra el OTP en pantalla. |
| `APP_SECRET` | primer valor aleatorio de 48 bytes | Firma las sesiones. |
| `OTP_PEPPER` | segundo valor aleatorio de 48 bytes | Protege los códigos OTP en la base. |
| `POSTGRES_HOST` | `127.0.0.1` | Host usado al ejecutar FastAPI fuera de Docker. Compose lo cambia internamente a `db`. |
| `POSTGRES_PORT` | `5432` | Puerto de PostgreSQL dentro y fuera del contenedor. |
| `POSTGRES_EXTERNAL_PORT` | `5432` | Puerto publicado exclusivamente en localhost. Si está ocupado, usar `5433`. |
| `POSTGRES_DB` | `imagen_report` | Nombre de la base. |
| `POSTGRES_USER` | `imagen_report` | Usuario propietario de la base. |
| `POSTGRES_PASSWORD` | tercer valor aleatorio | Contraseña del usuario PostgreSQL. |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Origen permitido cuando Vite se ejecuta por separado. |
| `COOKIE_SECURE` | `false` | En local se usa HTTP. Debe ser `true` con HTTPS en producción. |
| `APP_DOMAIN` | `localhost` | Dominio atendido por Caddy. |
| `APP_SCHEME` | `http` | Evita certificados locales durante esta prueba. |

No hay que escribir manualmente una URL de conexión. FastAPI construye
`postgresql+psycopg://...` con `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` y
`POSTGRES_PASSWORD`. Esto evita problemas si la contraseña contiene caracteres especiales.

### Usuario administrador inicial

| Variable | Valor de ejemplo | Qué poner realmente |
| --- | --- | --- |
| `BOOTSTRAP_ADMIN_USERNAME` | `admin` | Nombre con el que se iniciará sesión. |
| `BOOTSTRAP_ADMIN_EMAIL` | `doctor@gmail.com` | Correo real que recibirá el segundo factor. Puede ser Gmail personal. |
| `BOOTSTRAP_ADMIN_PASSWORD` | una contraseña larga y única | Nunca dejar `change-me-now`. |

El usuario se crea automáticamente la primera vez que inicia la API. Si luego se cambian estas
variables, el usuario ya creado no se modifica. En ese caso hay que administrar el usuario en la
base o reiniciar el volumen local, como se explica al final.

Si una contraseña contiene el carácter `$`, escribir el valor entre comillas simples para que
Docker Compose no intente interpretarlo como una variable. Por ejemplo:

```dotenv
BOOTSTRAP_ADMIN_PASSWORD='una$clave$segura'
```

### SMTP para el código de acceso

En `APP_ENV=development`, el código de seis dígitos también aparece en la pantalla. Por tanto,
SMTP puede dejarse vacío durante la primera prueba. Para probar el envío real con una cuenta Gmail
personal o Workspace, usar:

| Variable | Valor |
| --- | --- |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | correo completo, por ejemplo `informes@gmail.com` |
| `SMTP_PASSWORD` | contraseña de aplicación de Google, no la contraseña normal |
| `SMTP_FROM_EMAIL` | el mismo correo institucional |
| `SMTP_USE_TLS` | `true` |

Para Gmail personal se debe activar la verificación en dos pasos y crear una contraseña de
aplicación. No se coloca aquí la contraseña normal de Gmail. En cuentas administradas, esta opción
puede estar restringida por el administrador.

## 4. Configurar Google Sheet de solo lectura

Esta integración utiliza una cuenta de servicio distinta de la cuenta Google autorizada para
Docs, Drive y Gmail. La cuenta de servicio solo necesita leer la Sheet; no se le debe dar acceso a
la plantilla ni a la carpeta de informes.

### 4.1 Crear o seleccionar el proyecto de Google Cloud

1. Entrar en [Google Cloud Console](https://console.cloud.google.com/) con la cuenta que
   administrará la integración.
2. Abrir el selector de proyectos de la barra superior.
3. Seleccionar el proyecto existente o pulsar **Nuevo proyecto**.
4. Asignarle un nombre reconocible, por ejemplo `Imagen Report`, y crearlo.
5. Confirmar en la barra superior que ese proyecto quedó seleccionado antes de continuar.

### 4.2 Habilitar Google Sheets API

1. Dentro del proyecto, abrir **APIs y servicios > Biblioteca**.
2. Buscar `Google Sheets API`.
3. Abrir el resultado oficial y pulsar **Habilitar**.

### 4.3 Crear la cuenta de servicio y descargar su clave

1. Abrir **IAM y administración > Cuentas de servicio**.
2. Pulsar **Crear cuenta de servicio**.
3. Usar un nombre reconocible, por ejemplo `imagen-report-sheets-reader`.
4. En los pasos de roles del proyecto se puede pulsar **Continuar** sin asignar roles. El acceso a
   la Sheet se otorgará compartiendo el archivo concreto y no dando permisos globales al proyecto.
5. Abrir la cuenta de servicio creada y entrar en la pestaña **Claves**.
6. Pulsar **Agregar clave > Crear clave nueva > JSON**.
7. Descargar el archivo. La clave privada solo se muestra en esa descarga; debe tratarse como un
   secreto.

Desde la raíz del proyecto, crear la carpeta local y copiar allí el JSON con el nombre esperado:

```bash
mkdir -p secrets
cp /ruta/de/la/descarga.json secrets/google-service-account.json
chmod 600 secrets/google-service-account.json
```

No agregar este archivo a Git ni compartirlo por correo o chat.

### 4.4 Dar acceso de lectura a la Sheet

1. Abrir `secrets/google-service-account.json` localmente y copiar el valor de `client_email`.
2. Abrir la Google Sheet usada por la institución.
3. Pulsar **Compartir**, pegar ese correo y asignar el rol **Lector**.
4. No asignar **Editor**: la aplicación solo consulta estos datos.
5. Confirmar que el rango configurado comienza en la fila que contiene los encabezados.

Mantener estos valores ya identificados en `.env`:

```dotenv
GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE=/run/secrets/google-service-account.json
GOOGLE_SHEET_ID=1ATTcmm3rs4NjpBoD0113-Oht-YieQx-PdPk3b4SVJqU
GOOGLE_SHEET_RANGE="'Hoja 1'!A11:K"
SHEET_PATIENT_NAME_HEADER=NOMBRE
SHEET_PATIENT_ID_HEADER=CEDULA
SHEET_DOCTOR_HEADER=DR.
SHEET_RECIPIENT_EMAIL_HEADER=ENVIO A...
```

La ruta `/run/secrets/...` es la ruta interna del contenedor; Docker monta la carpeta local
`./secrets` en `/run/secrets` en modo de solo lectura. No hay que crear una carpeta `run` en el
proyecto ni poner la ruta absoluta de la Mac en `.env` cuando se usa Compose.

## 5. Configurar Gemini

1. Crear una API key en Google AI Studio dentro del proyecto que se utilizará.
2. Pegarla en `GEMINI_API_KEY`.
3. Mantener el modelo estable configurado:

```dotenv
GEMINI_API_KEY=pegar-aqui-la-clave-real
GEMINI_MODEL=gemini-3.6-flash
```

La clave solo es leída por FastAPI y nunca llega al navegador.

## 6. Configurar Google Docs, Drive y el borrador opcional de Gmail

La cuenta autorizada puede ser un Gmail personal o una cuenta de Google Workspace. Esta
integración usa OAuth con acceso offline y es independiente de la cuenta de servicio de la sección
4. La misma autorización permite que el backend copie la plantilla, escriba el informe, exporte el
PDF y, solo si se habilita, cree un borrador en Gmail.

### 6.1 Preparar la cuenta, la plantilla y la carpeta

1. Elegir la cuenta Google que será propietaria o tendrá acceso a los documentos finales. Puede
   ser una cuenta `@gmail.com` normal.
2. Abrir con esa cuenta la plantilla y la carpeta de destino para comprobar los permisos.
3. La cuenta debe poder editar la plantilla o, como mínimo, copiarla, y debe poder crear archivos
   dentro de la carpeta de salida.
4. Confirmar que la plantilla sea un documento nativo de Google Docs. Una plantilla cargada como
   `.docx` no sirve aunque se vea dentro de Drive. Si es un archivo de Office, abrirlo con Google
   Docs y usar **Archivo > Guardar como Documentos de Google**.
5. La plantilla debe conservar estos marcadores, respetando mayúsculas y espacios:

```text
{{ paciente }}
{{ doctor }}
{{ fecha }}
{{ analisis }}
{{ CI }}
{{ driver link }}
{{ measures }}
{{ doctor_gender }}
```

### 6.2 Habilitar las APIs en Google Cloud

1. Entrar en [Google Cloud Console](https://console.cloud.google.com/) y seleccionar el mismo
   proyecto creado en la sección 4.
2. Abrir **APIs y servicios > Biblioteca**.
3. Buscar y habilitar **Google Drive API**.
4. Volver a la biblioteca, buscar y habilitar **Google Docs API**.
5. Para la primera prueba sin Gmail no hace falta habilitar Gmail API todavía.
6. Si se probarán borradores, buscar y habilitar también **Gmail API**.

### 6.3 Configurar Google Auth Platform y la pantalla de consentimiento

La consola actual agrupa esta configuración en **Google Auth Platform**. Según el idioma o la
versión de la consola, también puede aparecer bajo **APIs y servicios > Pantalla de consentimiento
OAuth**.

1. Abrir **Google Auth Platform > Branding** y pulsar **Comenzar** si todavía no está configurado.
2. Completar un nombre de aplicación, por ejemplo `Imagen Report`.
3. Indicar un correo de asistencia del usuario y un correo de contacto del desarrollador.
4. En **Audience**, elegir:
   - **External** si se usa Gmail personal o si podrán autorizar cuentas fuera de una organización
     Workspace;
   - **Internal** únicamente si el proyecto pertenece a Google Workspace y todos los usuarios
     autorizados son de esa organización.
5. Si la audiencia es **External** y el estado es **Testing**, abrir **Audience > Test users** y
   agregar exactamente la cuenta Gmail que se usará al ejecutar el asistente OAuth.
6. Guardar los cambios. No es necesario publicar la aplicación para una prueba controlada con un
   usuario agregado como usuario de prueba.

### 6.4 Declarar los permisos OAuth

Abrir **Google Auth Platform > Data Access** y agregar los siguientes scopes:

```text
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/documents
```

Si también se crearán borradores, agregar:

```text
https://www.googleapis.com/auth/gmail.compose
```

El permiso `drive` se usa para copiar la plantilla, exportar el documento y guardar el PDF. El
permiso `documents` permite reemplazar los marcadores de la copia. `gmail.compose` permite crear y
modificar borradores; la aplicación no llama al endpoint de envío.

Google clasifica algunos permisos amplios como sensibles o restringidos. El modo **Testing** con
usuarios de prueba es suficiente para la validación local. Antes de una publicación externa y
continua puede ser necesario completar la verificación solicitada por Google.

### 6.5 Crear el cliente OAuth de escritorio

1. Abrir **Google Auth Platform > Clients**.
2. Pulsar **Create client** o **Crear cliente**.
3. Seleccionar **Desktop app / Aplicación de escritorio**.
4. Asignar un nombre, por ejemplo `Imagen Report local`.
5. Crear el cliente y descargar el JSON.
6. Guardarlo en el proyecto con este nombre exacto:

```bash
mkdir -p secrets
cp /ruta/de/la/descarga.json secrets/google-oauth-client.json
chmod 600 secrets/google-oauth-client.json
```

Al terminar deben existir dos archivos diferentes:

```text
secrets/
├── google-service-account.json  # lectura de Google Sheet
└── google-oauth-client.json     # Docs, Drive y Gmail opcional
```

No intercambiarlos: el primero contiene una cuenta de servicio y el segundo un cliente OAuth de
escritorio. Ninguno debe agregarse a Git.

### 6.6 Generar la autorización para Docs y Drive

Preparar una instalación local del backend:

```bash
python3 -m venv .venv
./.venv/bin/pip install -e backend
```

Para autorizar únicamente Docs y Drive, ejecutar:

```bash
./.venv/bin/python backend/scripts/google_oauth_setup.py \
  secrets/google-oauth-client.json
```

El asistente abre el navegador. Allí se debe:

1. Iniciar sesión con la cuenta preparada en 6.1.
2. Si la aplicación está en **Testing**, verificar que sea uno de los usuarios de prueba.
3. Revisar y aceptar los permisos de Drive y Docs.
4. Esperar el mensaje de autorización completada y volver a la terminal.

El script imprime tres variables. Copiarlas en el `.env` local, sin comillas adicionales y sin
publicarlas en el repositorio:

```dotenv
GOOGLE_OAUTH_CLIENT_ID=valor-impreso-por-el-script
GOOGLE_OAUTH_CLIENT_SECRET=valor-impreso-por-el-script
GOOGLE_OAUTH_REFRESH_TOKEN=valor-impreso-por-el-script
GOOGLE_OAUTH_TOKEN_URI=https://oauth2.googleapis.com/token
```

### 6.7 Obtener los identificadores de la plantilla y la carpeta

Los valores son identificadores de Google, no nombres de archivo ni nombres de carpeta.

- En `https://docs.google.com/document/d/ID_DE_LA_PLANTILLA/edit`, copiar solamente
  `ID_DE_LA_PLANTILLA`.
- En `https://drive.google.com/drive/folders/ID_DE_LA_CARPETA`, copiar solamente
  `ID_DE_LA_CARPETA`.

Completar `.env` con los IDs reales:

```dotenv
GOOGLE_DOCS_TEMPLATE_ID=pegar-id-del-documento-nativo
GOOGLE_DRIVE_OUTPUT_FOLDER_ID=pegar-id-de-la-carpeta
GMAIL_DRAFT_ENABLED=false
GMAIL_USER_ID=me
```

No es necesario que la plantilla o la carpeta tengan un nombre concreto. Lo importante es que los
IDs sean correctos y que la cuenta autorizada tenga acceso. Con `GMAIL_DRAFT_ENABLED=false`, Docs y
Drive funcionan normalmente y la aplicación no ofrece crear el correo.

### 6.8 Habilitar y autorizar los borradores de Gmail

Esta parte es opcional en la configuración y también será opcional para cada informe.

1. Confirmar que **Gmail API** esté habilitada, como se indica en 6.2.
2. Confirmar que `gmail.compose` esté declarado en **Data Access**, como se indica en 6.4.
3. Ejecutar nuevamente el asistente solicitando Gmail:

```bash
./.venv/bin/python backend/scripts/google_oauth_setup.py \
  secrets/google-oauth-client.json \
  --with-gmail
```

4. Autorizar Drive, Docs y Gmail con la misma cuenta.
5. Reemplazar en `.env` los tres valores OAuth por los nuevos que imprime el script.
6. Activar la función:

```dotenv
GMAIL_DRAFT_ENABLED=true
GMAIL_USER_ID=me
```

`GMAIL_USER_ID=me` indica que el borrador se crea en la misma cuenta que autorizó OAuth. Cuando la
función está activa, cada informe muestra un check: desmarcado crea solo Doc y PDF; marcado crea
además el borrador con el PDF adjunto. El backend nunca envía el correo automáticamente.

La autorización OAuth de Gmail es diferente del SMTP usado para enviar el código OTP. Habilitar
una no configura la otra.

### 6.9 Reiniciar y comprobar la configuración

Después de cambiar `.env`, recrear el backend para que lea los valores nuevos:

```bash
docker compose up -d --force-recreate backend
```

Comprobar la bandera pública:

```bash
curl http://localhost/api/config
```

Sin Gmail debe responder:

```json
{"gmail_draft_enabled":false}
```

Con Gmail habilitado debe responder:

```json
{"gmail_draft_enabled":true}
```

Después realizar la prueba funcional de la sección 8. El borrador, si se eligió, debe aparecer en
**Borradores** de la cuenta autorizada y no en **Enviados**.

Con una audiencia **External** en estado **Testing**, Google limita la autorización a los usuarios
de prueba y el refresh token puede caducar a los siete días. Esto es aceptable para la prueba
inicial. Para uso continuo hay que revisar el estado de publicación y los requisitos de
verificación de Google.

Referencias oficiales de Google: [pantalla de consentimiento OAuth](https://developers.google.com/workspace/guides/configure-oauth-consent),
[credenciales OAuth](https://developers.google.com/workspace/guides/create-credentials),
[permisos de Drive](https://developers.google.com/workspace/drive/api/guides/api-specific-auth),
[permisos de Gmail](https://developers.google.com/workspace/gmail/api/auth/scopes) y
[ciclo de vida de tokens OAuth](https://developers.google.com/identity/protocols/oauth2).

## 7. Levantar el proyecto completo

Validar primero que Compose entiende el archivo:

```bash
docker compose config --quiet
```

Construir e iniciar:

```bash
docker compose up --build -d
```

Comprobar los cuatro servicios:

```bash
docker compose ps
```

Los servicios `db`, `backend`, `frontend` y `proxy` deben figurar activos; `db` debe aparecer como
`healthy`.

Verificar la API:

```bash
curl http://localhost/api/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

Verificar PostgreSQL y las tablas creadas por FastAPI:

```bash
docker compose exec db psql -U imagen_report -d imagen_report -c '\dt'
```

Deben aparecer las tablas `users`, `otp_challenges` y `auth_sessions`.

Abrir `http://localhost` en Chrome. La documentación técnica queda en
`http://localhost/api/docs`.

## 8. Prueba funcional completa

1. Iniciar sesión con `BOOTSTRAP_ADMIN_USERNAME` y `BOOTSTRAP_ADMIN_PASSWORD`.
2. Usar el código recibido por correo. Mientras `APP_ENV=development`, también aparecerá en la
   pantalla para no bloquear la prueba si SMTP aún no está configurado.
3. Buscar un paciente por nombre o cédula y confirmar que llegan nombre, cédula, médico y, cuando
   existe, correo destinatario desde la Sheet.
4. Permitir el micrófono cuando Chrome lo solicite, dictar un texto y detener el dictado.
5. Corregir manualmente la transcripción y pedir el borrador técnico a Gemini.
6. Editar el borrador final, completar fecha, medidas y enlace de Drive.
7. Marcar la aprobación profesional.
8. Con `GMAIL_DRAFT_ENABLED=false`, confirmar que no aparece el check y que se crean normalmente el
   documento y el PDF.
9. Con `GMAIL_DRAFT_ENABLED=true`, decidir para ese informe si se marca el check. Si se marca,
   confirmar o escribir el correo destinatario.
10. Publicar y comprobar:
    - Google Doc copiado desde la plantilla y con sus marcadores reemplazados.
    - PDF guardado en la carpeta de Drive.
    - Si se eligió, borrador presente en Gmail con el PDF adjunto, sin enviar.

### 8.1 Gestión de usuarios

Al iniciar sesión con un usuario administrador aparece el botón **Usuarios** en la barra superior.
Desde allí se puede:

- crear usuarios internos con nombre, correo para OTP y contraseña inicial;
- otorgar o retirar el rol de administrador;
- activar o desactivar cuentas;
- actualizar el correo autorizado;
- restablecer contraseñas.

No existe una pantalla de registro público. Al desactivar una cuenta o restablecer su contraseña,
la aplicación revoca sus sesiones y códigos OTP pendientes. Un administrador no puede desactivar
su propia cuenta ni quitarse su propio rol, evitando dejar el sistema sin administración.

## 9. Ver logs y detener

Logs de todos los servicios:

```bash
docker compose logs -f
```

Solo FastAPI:

```bash
docker compose logs -f backend
```

Detener sin borrar datos:

```bash
docker compose down
```

Volver a iniciar conserva PostgreSQL porque usa un volumen.

## 10. Ejecutar los tests automatizados

Los tests usan una base SQLite en memoria deliberadamente aislada. Esa excepción existe solo para
que la suite sea rápida y no toca ni sustituye PostgreSQL en la aplicación.

```bash
python3 -m venv .venv
./.venv/bin/pip install -e 'backend[dev]'
./.venv/bin/pytest -q backend/tests
```

Para verificar el frontend fuera de Docker:

```bash
cd frontend
npm install
npm run lint
npm run build
```

## 11. Problemas frecuentes

- **El puerto 5432 está ocupado:** cambiar solo `POSTGRES_EXTERNAL_PORT=5433`. Docker seguirá
  usando internamente el puerto 5432.
- **El backend no conecta a PostgreSQL:** comprobar `docker compose ps`, confirmar que `db` está
  `healthy` y que `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD` no se cambiaron después de
  crear el volumen.
- **La contraseña configurada da “Credenciales inválidas”:** si contiene `$`, encerrarla entre
  comillas simples, recrear el backend y recordar que `BOOTSTRAP_ADMIN_PASSWORD` no cambia la clave
  de un usuario que ya existe. Restablecerla desde **Usuarios** o reiniciar la base local solo si se
  acepta perder todos sus usuarios y sesiones.
- **La Sheet devuelve error:** comprobar el nombre del archivo JSON, el permiso de lector y que el
  rango incluya la fila de encabezados.
- **Google no devuelve refresh token:** revocar el acceso previo de la aplicación en la cuenta de
  Google y volver a ejecutar el script; este solicita consentimiento y acceso offline.
- **Drive o Docs responde sin permiso:** abrir manualmente con la cuenta institucional tanto la
  plantilla como la carpeta y revisar sus permisos.
- **La plantilla da error aunque está en Drive:** confirmar que sea Google Docs nativo y no un
  `.docx`; convertirla y actualizar `GOOGLE_DOCS_TEMPLATE_ID` con el ID del documento nuevo.
- **No aparece la opción Gmail:** comprobar `GMAIL_DRAFT_ENABLED=true`, reiniciar el backend y
  recargar la interfaz.
- **No aparece el borrador de Gmail:** comprobar que el token se generó con `--with-gmail`, que se
  autorizó el alcance `gmail.compose` y que se marcó el check del informe.
- **Chrome no toma el dictado:** autorizar el micrófono para `http://localhost` y utilizar Chrome.

## 12. Reinicio total de la base local

Este comando elimina el volumen local de PostgreSQL, todos los usuarios y todas las sesiones. No
borra archivos de Google Drive, pero es destructivo para los datos locales:

```bash
docker compose down -v
```

Usarlo solo si se desea comenzar desde cero. Al siguiente `docker compose up --build -d`, FastAPI
creará nuevamente las tablas y el usuario administrador configurado en `.env`.

## 13. Cambios mínimos para producción

Antes de exponer el servidor fuera de la red local:

- `APP_ENV=production`
- `COOKIE_SECURE=true`
- `APP_DOMAIN=dominio-real-de-la-institucion`
- `APP_SCHEME=https`
- `FRONTEND_ORIGIN=https://dominio-real-de-la-institucion`
- secretos y contraseñas distintos de los valores de ejemplo
- copias de seguridad cifradas del volumen PostgreSQL
- reglas de firewall que no publiquen PostgreSQL a la red externa

La API se niega a iniciar en producción si detecta los secretos, la contraseña inicial o la
contraseña de PostgreSQL de ejemplo.
