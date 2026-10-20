# GoldenTable

[![CI](https://github.com/MiguelGondur/-GoldenTableproject/actions/workflows/ci.yml/badge.svg)](https://github.com/MiguelGondur/-GoldenTableproject/actions/workflows/ci.yml)

App de reservas, fidelidad y billetera digital para casino físico.

GoldenTable centraliza la gestión de reservas de mesas, el programa de
fidelidad (acumulación y canje de puntos), la billetera digital del cliente
y las reglas de juego responsable (verificación de edad, límites y
autoexclusión), reduciendo filas en caja y dando al cliente visibilidad
total sobre su historial y beneficios.

## Equipo

- Miguel Gonzalez
- Juan David Rodriguez
- Miguel Salazar

Curso: Ingeniería de Software — UPB. Equipo **GoldenTable**.

## Épicas y estado

| Épica | Historias | Estado |
|---|---|---|
| Gestión de Reservas | HU-01 disponibilidad, HU-02 reserva, HU-03 check-in | Implementado |
| Programa de Fidelidad | HU-04 acumulación, HU-05 canje | Implementado |
| Billetera Digital | HU-06 recarga, HU-07 validación de saldo, HU-08 reportes CSV, HU-12 historial | Implementado |
| Notificaciones y Perfil | HU-09 notificaciones push, HU-10 verificación de edad/documento, HU-11 límites y autoexclusión | Implementado |

Trazabilidad completa requisito → historia → issue → código → pruebas → PR en
[`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md). Limitaciones conocidas en
[`docs/DEUDA_TECNICA.md`](docs/DEUDA_TECNICA.md). El SRS está en
[`GoldenTable.docx`](GoldenTable.docx).

## Stack técnico

- Python 3.12 / FastAPI / Pydantic v2
- Pytest + pytest-cov (cobertura mínima 80 %, REQ-NFUNC-006)
- GitHub Actions (CI)
- Datos en memoria (placeholder; ver deuda técnica)

## Cómo ejecutar el proyecto

```bash
git clone https://github.com/MiguelGondur/-GoldenTableproject.git goldentable
cd goldentable
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

API en `http://127.0.0.1:8000`, documentación interactiva (Swagger) en
`http://127.0.0.1:8000/docs`.

## Pruebas y cobertura

```bash
python -m pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

El workflow `.github/workflows/ci.yml` ejecuta las pruebas, el smoke test de
`/health` y empaqueta la API en cada push a `main` y cada pull request.

## Demo

Con la API corriendo (o sin ella, en memoria):

```bash
python scripts/demo.py                          # en memoria
python scripts/demo.py --url http://127.0.0.1:8000   # contra el servidor
```

Recorre: registro → recarga → disponibilidad → reserva → recordatorio →
check-in → puntos → canje → límite de gasto → autoexclusión.

## Endpoints

| Método y ruta | Historia |
|---|---|
| `GET /health` | — |
| `GET /disponibilidad?fecha=&hora=` | HU-01 |
| `POST /reservas` · `GET /reservas` · `GET /reservas/{codigo}` | HU-02 |
| `POST /reservas/checkin` | HU-03 |
| `POST /fidelidad/acumular` · `GET /fidelidad/puntos/{cliente}` | HU-04 |
| `GET /fidelidad/beneficios` · `POST /fidelidad/canjear` | HU-05 |
| `POST /billetera/recarga` | HU-06 |
| `GET /billetera/validar` | HU-07 |
| `GET /billetera/reportes` (CSV) | HU-08 |
| `GET /billetera/{cliente_id}` | HU-12 |
| `POST /notificaciones/enviar` · `POST /notificaciones/reservas-proximas` · `GET /notificaciones/{cliente}` | HU-09 |
| `POST /usuarios/registro` · `GET /usuarios/{documento}` | HU-10 |
| `POST /fidelidad/limite` · `POST /fidelidad/gasto` · `POST/GET /fidelidad/autoexclusion` | HU-11 |

## Flujo de trabajo (Git)

- Nunca se hace commit directo a `main`: rama `feature/hu-XX-nombre` → Pull Request con `Closes #N`.
- Commits con Conventional Commits y el ID del requisito: `feat(reservas): REQ-FUNC-002 ...`.

## Estructura

```
.github/workflows/ci.yml
docs/            # SRS, trazabilidad, deuda técnica
scripts/demo.py
src/api/         # main.py, models.py, store.py, seguridad.py, routers/
tests/
```
