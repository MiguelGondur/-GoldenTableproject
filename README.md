# GoldenTable

[![CI](https://github.com/MiguelGondur/-GoldenTableproject/actions/workflows/ci.yml/badge.svg)](https://github.com/MiguelGondur/-GoldenTableproject/actions/workflows/ci.yml)

**GoldenTable** es una aplicación web para un casino físico que centraliza las reservas de mesas, el programa de fidelidad (acumulación y canje de puntos), la billetera digital del cliente y las reglas de juego responsable (verificación de edad y documento, límites de gasto y autoexclusión). Reduce las filas en caja y los errores de conciliación, y le da al cliente visibilidad sobre su historial y beneficios. Está construida a partir del documento de requisitos [`GoldenTable.docx`](GoldenTable.docx) (ISO/IEC/IEEE 29148).

- **Tablero (GitHub Projects):** https://github.com/users/MiguelGondur/projects/1

## Equipo

Curso Ingeniería de Software, UPB — equipo **GoldenTable**.

- Miguel Gonzalez
- Juan David Rodriguez
- Miguel Salazar

## Tecnologías (versiones)

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12.7, FastAPI 0.115.0, Pydantic 2.9.2, SQLAlchemy 2.0.36, PyJWT 2.9.0, Uvicorn 0.30.6 |
| Base de datos | PostgreSQL 16.4 (imagen `postgres:16.4-alpine`) |
| Frontend | HTML/CSS/JavaScript propio servido por nginx 1.27.2 (`nginx:1.27.2-alpine`) |
| Contenedores | Docker y Docker Compose v2 |
| Pruebas / CI | Pytest 8.3.3 + pytest-cov (cobertura > 80 %), GitHub Actions |
| Documentación de la API | OpenAPI 3.1 (`openapi.yaml`) |

## Cómo ejecutarlo (Docker, desde un clon limpio)

Único requisito: **Docker** con Compose v2. No hace falta crear ningún `.env`.

```bash
git clone https://github.com/MiguelGondur/-GoldenTableproject.git goldentable
cd goldentable
docker compose up -d --build
```

Espera ~30 segundos a que los tres servicios (`db`, `backend`, `frontend`) queden sanos (`docker compose ps`). Los usuarios y datos de ejemplo se crean solos en el primer arranque.

| Servicio | URL |
|---|---|
| **Frontend (aplicación web)** | http://localhost:8080 |
| **API (backend)** | http://localhost:8000 |
| Documentación interactiva (Swagger) | http://localhost:8000/docs |
| Especificación OpenAPI | archivo [`openapi.yaml`](openapi.yaml) en la raíz (también en http://localhost:8000/openapi.json) |

Para apagar: `docker compose down` (añade `-v` para borrar también los datos).

## Variables de entorno

Todas son opcionales; estos son los valores por defecto (ver [`.env.example`](.env.example)).

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `POSTGRES_USER` | `goldentable` | Usuario de la base de datos |
| `POSTGRES_PASSWORD` | `goldentable` | Contraseña de la base de datos |
| `POSTGRES_DB` | `goldentable` | Nombre de la base de datos |
| `JWT_SECRET` | `goldentable-dev-secret-cambiar-en-produccion` | Clave de firma de los tokens JWT |
| `JWT_EXPIRE_MINUTES` | `60` | Duración de la sesión |
| `CASINO_TZ` | `America/Bogota` | Zona horaria del casino |
| `SEED_DATA` | `true` | Carga los datos de ejemplo al arrancar |
| `BACKEND_PORT` | `8000` | Puerto del API en el host |
| `FRONTEND_PORT` | `8080` | Puerto del frontend en el host |

La base de datos es un servicio de Compose (no hay credenciales en la nube).

## Usuarios de prueba

Contraseña de **todos**: `Casino2026!`

| Usuario | Rol | Qué puede hacer |
|---|---|---|
| `cliente1` | Cliente | Reservar, ver puntos y canjear, billetera, notificaciones, límites y autoexclusión (500 puntos, saldo $150.000) |
| `cliente2` | Cliente | Igual; tiene la reserva de ejemplo `DEMO0001` (120 puntos, saldo $50.000) |
| `anfitrion` | Anfitrión | Ver las reservas del día, hacer check-in, enviar notificaciones y recordatorios |
| `cajero` | Cajero | Validar saldo en caja, registrar consumos (acredita puntos), recargas en caja |
| `gerente` | Gerente | Todo lo anterior más reportes de transacciones (CSV) |

También se pueden crear clientes nuevos desde la pantalla **Crear cuenta** (mayores de 18 años; documento de 6 a 10 dígitos).

## Datos de ejemplo (existen desde el primer arranque)

- **23 mesas** con franjas de 18:00 a 22:00 (ids 1 a 8 históricos y 9 a 23 por franja y capacidad); la mesa 3 aparece reservada y la 5 ocupada a modo de ejemplo.
- **5 usuarios** (tabla anterior), con puntos, billetera e historial de recargas para los clientes.
- **Reserva de ejemplo `DEMO0001`** (cliente2, mesa 4, 19:00, hoy) para practicar el check-in como anfitrión.
- Catálogo de beneficios: `bebida_gratis` (50 pts), `entrada_evento` (150), `cena_vip` (300), `noche_hotel` (500).

## Flujos principales y requisitos que implementan

| Flujo en la app | Requisito (SRS) | Quién |
|---|---|---|
| Consultar mesas por fecha y hora | REQ-FUNC-001 | cliente |
| Reservar una mesa y recibir código de confirmación | REQ-FUNC-002 | cliente |
| Ver las reservas del día y hacer check-in con el código | REQ-FUNC-003 | anfitrión |
| Registrar un consumo y acreditar puntos | REQ-FUNC-004 | cajero |
| Canjear puntos y recibir un cupón | REQ-FUNC-005 | cliente |
| Recargar saldo | REQ-FUNC-006 | cliente / cajero |
| Consultar saldo y últimas 20 transacciones | REQ-FUNC-007 | cliente |
| Validar saldo en caja | REQ-FUNC-008 | cajero |
| Notificaciones push (reserva próxima, promoción, vencimiento) | REQ-FUNC-009 | anfitrión/gerente envían; cliente recibe |
| Registro con verificación de edad y documento | REQ-FUNC-010 | cliente |
| Límite de gasto y autoexclusión | REQ-FUNC-011 | cliente |
| Reporte de transacciones en CSV | REQ-FUNC-012 | gerente |
| Bloqueo de cuenta tras 5 intentos fallidos | REQ-NFUNC-003 | todos |

Trazabilidad completa en [`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md).

## Autenticación (JWT)

`POST /auth/login` devuelve un token; todas las rutas, salvo `/health`, `/auth/login` y `/usuarios/registro`, exigen `Authorization: Bearer <token>` y responden **401** sin él. El frontend guarda el token al iniciar sesión, lo envía en cada petición protegida y lo borra al cerrar sesión (o si el API responde 401). Cinco intentos fallidos bloquean la cuenta 15 minutos (423).

## Pruebas

Las pruebas usan una base PostgreSQL real (nombre con "test"):

```bash
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/goldentable_test
python -m pytest --cov=src --cov-fail-under=80
```

El workflow `.github/workflows/ci.yml` ejecuta en cada push y pull request: (1) las pruebas con cobertura contra PostgreSQL, y (2) `docker compose up -d --build` desde cero, comprueba que no haya servicios caídos, que el frontend y el API respondan, recorre todos los flujos con `scripts/demo.py` y verifica que cada ruta de `openapi.yaml` exista.

Si cambias un endpoint, regenera la especificación: `python scripts/export_openapi.py`.

## Demo por línea de comandos

Con el sistema levantado: `python scripts/demo.py` (necesita `pip install httpx`).

## Estructura del repositorio

```
compose.yaml               Sistema completo (db + backend + frontend)
openapi.yaml               Especificación OpenAPI 3.1
backend/Dockerfile         Imagen del API
frontend/                  Dockerfile, nginx.conf y la aplicación web (public/)
src/api/                   API FastAPI: routers/, orm.py, auth.py, seed.py ...
tests/                     Pruebas (pytest)
scripts/                   export_openapi.py, demo.py, check_openapi_live.py
docs/                      Trazabilidad, diagramas UML, metodología, deuda técnica
.github/workflows/ci.yml   Integración continua
GoldenTable.docx           Documento de requisitos (SRS)
```

## Documentación adicional

- [Diagramas de secuencia UML](docs/DIAGRAMAS_SECUENCIA.md)
- [Metodología ágil y flujo de Git](docs/METODOLOGIA_Y_FLUJO_GIT.md)
- [Trazabilidad requisito → HU → issue → código → pruebas → PR](docs/TRAZABILIDAD.md)
- [Deuda técnica y limitaciones](docs/DEUDA_TECNICA.md)
- [Guion para la defensa](docs/GUION_DEFENSA.md)
