# GoldenTable

App de reservas, fidelidad y billetera digital para casino físico.

GoldenTable centraliza la gestión de reservas de mesas y eventos, el
programa de fidelidad (acumulación y canje de puntos) y la billetera
digital del cliente (recargas y consulta de saldo), reduciendo filas
en caja, errores de conciliación y dándole al cliente visibilidad
total sobre su historial y beneficios.

## Equipo

- [Miguel Gonzalez] 
- [Juan David Rodriguez] 
- [Miguel Salazar] 

## Épicas del proyecto

1. **Gestión de Reservas** — consulta de disponibilidad, reserva y check-in
2. **Programa de Fidelidad** — acumulación y canje de puntos
3. **Billetera Digital** — recarga, consulta de saldo, validación en caja
4. **Notificaciones y Perfil** — notificaciones push, verificación de edad/identidad

El detalle completo de historias de usuario y requisitos está en
[`docs/srs/`](docs/srs/).

## Stack técnico

- **Backend:** Python 3.11+ / FastAPI
- **Base de datos:** (por definir — sugerido PostgreSQL)
- **Testing:** Pytest

## Cómo ejecutar el proyecto localmente

```bash
# 1. Clonar el repositorio
git clone https://github.com/<usuario-u-org>/<nombre-repo>.git
cd <nombre-repo>

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar el servidor de desarrollo
uvicorn src.api.main:app --reload
```

La API quedará disponible en `http://127.0.0.1:8000` y la documentación
interactiva (Swagger) en `http://127.0.0.1:8000/docs`.

## Estructura del repositorio

```
goldentable/
├── docs/
│   ├── srs/            # SRS, versiones del documento de requisitos
│   └── diagrams/        # User Story Map, diagramas de arquitectura
├── src/
│   ├── api/             # Backend / endpoints (FastAPI)
│   ├── mobile/           # Cliente móvil (si aplica)
│   └── admin/            # Panel administrativo (si aplica)
├── tests/                # Pruebas unitarias, integración y E2E
├── .github/
│   ├── workflows/        # Pipelines de CI/CD (ci.yml, cd.yml)
│   └── ISSUE_TEMPLATE/   # Plantillas de issues
├── README.md
└── requirements.txt
```

## Flujo de trabajo (Git)

- `main`: rama protegida, siempre desplegable.
- `feature/*`: una rama por requisito, ej. `feature/req-func-002-reserva-mesa`.
- Commits siguiendo Conventional Commits + ID del requisito:
  `feat(reservas): REQ-FUNC-002 bloquear mesa al confirmar reserva`
- Todo Pull Request debe referenciar un issue (`Closes #X`) y al menos
  un ID de requisito (REQ-FUNC-XXX / REQ-NFUNC-XXX).

## Backlog y tablero

El backlog completo (épicas, historias de usuario y criterios de
aceptación) se gestiona en el tablero de **GitHub Projects** del
repositorio, organizado por Release (R1/R2/R3) según priorización
MoSCoW.
