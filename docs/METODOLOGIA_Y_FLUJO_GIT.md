# Metodología ágil y flujo de Git

## Metodología ágil aplicada

- **Marco:** desarrollo iterativo e incremental con un equipo auto-organizado de tres integrantes (Miguel Gonzalez, Juan David Rodriguez, Miguel Salazar). **No se asignaron roles formales de Scrum** (Product Owner / Scrum Master); cada integrante se hizo responsable de una épica: reservas, fidelidad y billetera, con notificaciones y verificación de edad compartidas.
- **Requisitos:** el SRS (`GoldenTable.docx`, ISO/IEC/IEEE 29148) define 12 historias de usuario con criterios en Gherkin y prioridad MoSCoW; las historias siguen el formato de calidad QUS.
- **Priorización:** según el **tiempo disponible del equipo** (pocas horas por semana por integrante) y las dependencias entre historias: primero lo que desbloqueaba lo demás (disponibilidad, recarga, verificación de edad), después fidelidad y billetera, y al final reservas completas, check-in y notificaciones.
- **Iteraciones (según el historial de GitHub):** el backlog de 12 historias se creó el 17-ago-2026 y se entregó de forma incremental en tres tandas: ~15-sep (HU-01, HU-06, HU-10; etiquetadas `SP1`), 30-sep (HU-04, 05, 07, 08, 11, 12) y 20-oct (HU-02, 03, 09 e integración), más la entrega final (PR #25). Solo la primera tanda quedó etiquetada.
- **Eventos ágiles:** el equipo realizó **retrospectiva**. No se hicieron dailies formales ni review/demo por iteración.
- **Mejoras identificadas:** etiquetar todas las iteraciones, reuniones cortas periódicas, revisión cruzada obligatoria de cada PR y PRs más pequeños.
- **Definición de terminado:** historia implementada, con pruebas que pasan en CI (cobertura > 80 %), integrada mediante un Pull Request que cierra su issue y movida a *Done* en el tablero.

## Tablero (GitHub Projects)

https://github.com/users/MiguelGondur/projects/1

Columnas: **Todo → In Progress → In Review → Done**. Cada tarjeta es un issue (una historia de usuario, #1 a #12) con sus tareas; el estado final del backlog muestra todas las historias en *Done*. El repositorio es público.

## Flujo de Git

- **Ramas:** `main` (siempre estable, protegida por convención: nunca se hace commit directo) y ramas de trabajo `feature/hu-XX-nombre`, `fix/...`, `docs/...`, `chore/...`.
- **Commits:** Conventional Commits con el identificador del requisito, p. ej. `feat(reservas): REQ-FUNC-002 reservas y check-in`.
- **Pull Requests:** cada cambio entra a `main` por un PR que referencia sus requisitos y cierra su issue (`Closes #N`); el CI debe estar en verde antes del merge.
- **Integración continua:** `.github/workflows/ci.yml` corre en cada push y PR: pruebas con cobertura contra PostgreSQL y un recorrido completo con `docker compose up -d --build`.
- **Trazabilidad:** [`TRAZABILIDAD.md`](TRAZABILIDAD.md) enlaza requisito → historia → issue → código → pruebas → PR.
