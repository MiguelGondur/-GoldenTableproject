# Metodología ágil y flujo de Git

## Metodología ágil aplicada

- **Marco:** desarrollo iterativo e incremental inspirado en Scrum, con un equipo auto-organizado de tres integrantes (Miguel Gonzalez, Juan David Rodriguez, Miguel Salazar).
- **Requisitos:** el SRS (`GoldenTable.docx`, ISO/IEC/IEEE 29148) define 12 historias de usuario con criterios en Gherkin y prioridad MoSCoW; las historias siguen el formato de calidad QUS.
- **Priorización:** MoSCoW y releases (R1 Must, R2 Should, R3 Could): primero consulta y reserva de mesas, acumulación de puntos, recarga y consulta de saldo, y verificación de edad; después canje, notificaciones y autoexclusión; al final reportes.
- **Planning:** se refinaron las historias a implementar, se asignaron cargas por integrante y se definió el alcance según el tiempo disponible (2 a 3 horas por semana por integrante, iteraciones de dos semanas).
- **Iteraciones:** cada iteración toma historias del backlog y deja el sistema funcionando; el estado se refleja en el tablero.
- **Definición de terminado:** historia implementada, con pruebas que pasan en CI (cobertura > 80 %), revisada en un Pull Request que cierra su issue y movida a *Done* en el tablero.

## Tablero (GitHub Projects)

https://github.com/users/MiguelGondur/projects/1

Columnas: **Todo → In Progress → In Review → Done**. Cada tarjeta es un issue (una historia de usuario, #1 a #12) con sus tareas; el estado final del backlog muestra todas las historias en *Done*. El profesor tiene acceso al repositorio como colaborador (`jpcc1217`).

## Flujo de Git

- **Ramas:** `main` (siempre estable, protegida por convención: nunca se hace commit directo) y ramas de trabajo `feature/hu-XX-nombre`, `fix/...`, `docs/...`, `chore/...`.
- **Commits:** Conventional Commits con el identificador del requisito, p. ej. `feat(reservas): REQ-FUNC-002 reservas y check-in`.
- **Pull Requests:** cada cambio entra a `main` por un PR que referencia sus requisitos y cierra su issue (`Closes #N`); el CI debe estar en verde antes del merge.
- **Integración continua:** `.github/workflows/ci.yml` corre en cada push y PR: pruebas con cobertura contra PostgreSQL y un recorrido completo con `docker compose up -d --build`.
- **Trazabilidad:** [`TRAZABILIDAD.md`](TRAZABILIDAD.md) enlaza requisito → historia → issue → código → pruebas → PR.
