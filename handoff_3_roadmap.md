# Handoff 3: Roadmap - que falta hacer

## Prioridad 1: Seguridad / Critico
- [ ] Cambiar SYNC_API_KEY en Render (test123 es inseguro)
- [ ] Configurar correctamente GitHub Actions con DATABASE_URL de Render
- [ ] Verificar que el sync en produccion funciona con la nueva clave

## Prioridad 2: Calidad y mantenimiento
- [ ] Configurar Alembic para migraciones de base de datos
- [ ] Agregar tests con pytest
- [ ] Limpiar archivos no usados restantes
- [ ] Mejorar README con ejemplos completos
- [ ] Agregar logging mas detallado

## Prioridad 3: Funcionalidad
- [ ] Integrar SofaScore a la base de datos (incidentes, alineaciones, stats)
- [ ] Agregar endpoints: /matches/{id}/events, /matches/{id}/lineups
- [ ] Agregar mapeo robusto ESPN team name ↔ SofaScore team name
- [ ] Agregar cache (Redis o en memoria)
- [ ] Rate limiting
- [ ] Webhooks o notificaciones para partidos en vivo

## Prioridad 4: Datos avanzados
- [ ] Momios/apuestas (complejo, fuentes limitadas)
- [ ] Historico de multiples temporadas
- [ ] Analisis de forma de equipos
- [ ] Comparaciones head-to-head mejoradas

## Notas importantes
- La temporada no ha iniciado (empieza 17 julio 2026), por eso no hay stats ni eventos reales
- La integracion completa de SofaScore esperar a que haya partidos finished
- MatchEvent y MatchLineup ya tienen tablas creadas pero vacias
