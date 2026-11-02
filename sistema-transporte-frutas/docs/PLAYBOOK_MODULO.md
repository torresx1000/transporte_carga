# Playbook para integrar un módulo

Este procedimiento documenta el piloto de `clientes` para repetirlo gradualmente en los demás módulos.

## Pasos aplicados en clientes

1. **Inspeccionar contrato y almacenamiento existente.** Se revisaron las columnas y el JSON del modelo antes de decidir. Para este piloto se usan las columnas existentes `name`, `document`, `status` y el JSON `data`; no se añadieron columnas ni migraciones.
2. **Definir entrada estricta.** Crear esquemas Pydantic de creación y actualización con `extra="forbid"`, validaciones de formato, longitud y valores permitidos. El esquema de actualización hace opcionales los campos; en el servicio se fusiona el JSON recibido con el JSON existente.
3. **Centralizar reglas de negocio.** El servicio valida documento duplicado antes de escribir, distingue un documento de cliente activo de uno archivado y convierte conflictos de integridad concurrentes en HTTP 409. Los clientes archivados permanecen ocultos en listados y detalle.
4. **Mantener el repositorio como dueño de consulta.** Implementar búsqueda, filtros y paginación sobre el repositorio; evitar filtrar solo en el navegador. En JSON se debe comprobar la expresión de consulta en el dialecto real antes de asumir compatibilidad.
5. **Publicar contrato OpenAPI.** Asignar esquemas de respuesta explícitos, exportar `backend/openapi.json` con el script existente y ejecutar `npm run gen:api` en `frontend/`.
6. **Usar tipos generados en el frontend.** Importar tipos de `frontend/types/api/schema.d.ts`; conservar tipos manuales solo para adaptaciones específicas de presentación, no para duplicar el contrato HTTP.
7. **Conectar servicio y React Query.** Crear o actualizar el servicio HTTP, hooks de listado/detalle/mutación, invalidación de caché y estados de carga, error y vacío. El detalle debe obtenerse por ID desde su endpoint.
8. **Enviar paginación y filtros a la API.** Incluir `page`, `page_size` y filtros en la petición, reiniciar la página al cambiar filtros y representar `total`/`pages` devueltos por el servidor.
9. **No simular persistencia de archivos.** Si el backend aún no almacena archivos, deshabilitar la selección y mostrar “Disponible próximamente” hasta implementar carga real.
10. **Probar reglas y pantallas.** Backend: validación, campos desconocidos, conflicto duplicado y concurrente, registros archivados, filtros, paginación y roles. Frontend: parámetros enviados, detalle por ID y errores asociados a campos.
11. **Verificar el contrato y las tablas.** Ejecutar `alembic check`, tests backend, Vitest, `npx tsc --noEmit`, Ruff y regeneración de OpenAPI/tipos. Si el siguiente módulo necesita una columna, proponer una migración reversible antes de tocar el esquema.

## Orden sugerido para conectar los demás módulos

1. **Pagos** — importes, moneda, fecha, estado, método, referencia y cliente/viaje como columnas consultables.
2. **Gastos** — importe, moneda, categoría, fecha, vehículo/viaje y proveedor como columnas.
3. **Viajes** — código, cliente, carga, vehículo, conductor, ruta, fechas y estado como columnas.
4. **Cargas** — cliente, producto, cantidad/peso, origen, destino y estado.
5. **Combustible y mantenimiento** — vehículo, fechas, kilometraje, cantidad, costo, proveedor y estado.
6. **Documentos y retornos** — propietario/recurso relacionado, tipo, vigencia y cantidades; conservar índices útiles para consulta.
7. **Conductores, vehículos, rutas y cotizaciones** — priorizar columnas para identificadores, relaciones, estados y métricas usadas en reportes.
8. **Reportes y portal** — conectar después de estabilizar los recursos y sus permisos; el portal siempre filtra por identidad autenticada en servicio/repositorio.

Los valores usados por filtros, joins, permisos, paginación y agregaciones de reportes conviene mantenerlos en columnas reales. El JSON queda para atributos complementarios con menor necesidad de consulta. Antes de migrar datos existentes, documentar valores inválidos, estrategia de backfill e instrucciones de reversión.

## Migrar un módulo a la fábrica CRUD basada en esquemas

La fábrica nueva se activa pasando un `ResourceContract` a `build_resource_router`. Los módulos que todavía llaman `build_resource_router("modulo")` conservan las rutas y el contrato legado `{ "data": {...} }`.

### Configuración

1. Crear esquemas Pydantic separados para creación, actualización parcial y respuesta. Los esquemas de entrada deben usar `ConfigDict(extra="forbid")`.
2. Configurar en `ResourceContract`:
   - `create_schema`, `update_schema` y `response_schema`.
   - `search_fields` con columnas reales (`name`) o rutas JSON (`data.contacto`).
   - `filters` como mapa del parámetro de consulta al campo (`{"estado": "status"}`).
   - `unique_fields` como mapa del dato de entrada a la columna única (`{"codigo": "code"}`).
   - `permissions` por acción (`list`, `read`, `create`, `update`, `delete`; `reactivate` si aplica).
   - `service_factory` cuando el recurso tenga reglas de negocio que deban conservarse; el servicio implementa `list(page, page_size, q, **filtros)`, `create(payload, user_id)`, `get(id)`, `update(id, payload)` y `delete(id)`.
3. Activar `allow_reactivate` solo cuando el servicio implemente una reactivación segura. La fábrica aplica el contrato de respuesta y permiso admin configurado.
4. Para recursos simples, omitir `service_factory`: la fábrica usa `RecordRepository`, guarda el cuerpo directo en JSON, fusiona ediciones parciales, aplica baja lógica y valida los campos únicos declarados.

### Checklist de pruebas

- [ ] Entrada directa; campos desconocidos rechazados con 422.
- [ ] Respuestas de lista y detalle validadas por el esquema declarado.
- [ ] Búsqueda y filtros configurados; `page`, `page_size`, `total` y `pages` coherentes.
- [ ] Creación y actualización sincronizan las columnas indicadas y conservan el JSON no editado.
- [ ] Duplicado detectado antes de escribir y conflicto de integridad traducido a 409.
- [ ] Baja lógica oculta el registro de listado y detalle.
- [ ] Cada operación prueba roles permitidos y rechazados.
- [ ] Si hay reactivación, probar rol, registro no archivado, conflicto único y retorno del mismo ID.
- [ ] Frontend cambia a tipos generados, cuerpo directo, filtros/paginación de servidor y estados de carga/error/vacío; agregar hook para detalle y mutaciones.
- [ ] Regenerar OpenAPI y tipos; ejecutar `alembic check`, pytest, Vitest, `npx tsc --noEmit` y Ruff.
- [ ] No migrar columnas hasta aprobar el backfill, índices, riesgos y reversión.

## Plan propuesto de lotes pendientes

Este plan es solo para revisión; no se migraron estos módulos en la Fase 5B.

1. **Lote 1 — Maestros:** conductores, vehículos y rutas. Son los catálogos que otros recursos referencian. Acordar primero identificadores, estados y unicidad; validar consistencia con la relación usuario-conductor pendiente.
2. **Lote 2 — Operación:** cargas → viajes → cotizaciones. Cargas debe validar que cliente exista; viajes debe validar carga, cliente, conductor, vehículo y ruta; cotizaciones valida cliente. Rechazar referencias inexistentes o dadas de baja antes de persistir. El orden permite que viajes use las relaciones ya normalizadas de cargas y maestros.
3. **Lote 3 — Dinero y costos:** pagos, gastos, combustible y mantenimiento. Conviene columnas tipadas para `monto_centimos`/moneda, fecha, estado, cliente/viaje/vehículo relacionados; en combustible también litros y odómetro, y en mantenimiento tipo de servicio y kilometraje. Esos campos alimentan filtros y reportes financieros/operativos. Riesgos: JSON histórico con monedas o unidades mezcladas, fechas inválidas, montos decimales redondeados de forma distinta y referencias a registros archivados. Hacer inventario, backfill validado, reporte de filas rechazadas y migración reversible; no agregar `NOT NULL` hasta corregir datos heredados.
4. **Lote 4 — Retornos y documentos:** retornos valida carga, viaje y propietario de cada asignación; documentos se migra después de implementar almacenamiento y ciclo de vida de archivos. Campos útiles de documentos: tipo, propietario, vencimiento, estado y metadatos del objeto almacenado. El riesgo principal es perder vínculos o vigencias durante backfill; para archivos, guardar referencias estables al almacenamiento, no el binario en JSON.

Cada lote se revisa y aprueba antes de comenzar el siguiente. Los campos de negocio mencionados son una propuesta de columnas; su migración requiere inspección de datos reales y aprobación específica.

## Semillas de desarrollo

`backend/seed_demo_users.py` crea cuentas de demostración de admin, operador, chofer y cliente. Exige `APP_ENV=development` (también acepta `dev`, `local` o `test`) y debe usarse únicamente en bases locales de desarrollo. Las credenciales están documentadas en `backend/README.md`; cámbialas si se comparten fuera del equipo.

## Lote 1 aplicado: conductores, vehículos y rutas

1. **Inventariar primero.** Consultar solo lectura las filas, nulos, duplicados, formatos y valores de estado/tipo. Revisar también unidades de distancia/duración y moneda en la base y en la pantalla. No decidir una moneda a partir solo del formato visual.
2. **Crear una migración reversible por recurso.** Mantener las columnas nuevas nullable y únicas cuando aplique. Copiar los valores legados del JSON a columnas sin modificar ni borrar el JSON original. Antes de agregar una unicidad, comprobar conflictos; fallar antes de alterar tablas si un backfill no se puede resolver sin ambigüedad.
3. **Preservar los datos al revertir.** Antes de quitar columnas nuevas, escribir sus valores actuales de vuelta al JSON. La limpieza del JSON legado queda pendiente hasta completar una migración futura y validada.
4. **Formalizar contratos.** Declarar esquemas Pydantic de create, update parcial y response con `extra="forbid"`; normalizar identificadores; definir listas explícitas de tipos y estados. El selector manual no ofrece `en_viaje`, que se automatizará cuando migremos viajes en el Lote 2.
5. **Configurar la fábrica compartida.** Pasar a `ResourceContract` los esquemas, campos de búsqueda, filtros permitidos, campos únicos, mapeo de columnas y permisos. Mantener el cuerpo plano, la fusión de PATCH, paginación, 409 por duplicados y baja lógica. Habilitar reactivación solo para admin.
6. **Proponer códigos sin reutilizarlos.** Vehículos usan `V-NN`/`V-NNN`; rutas usan `R-NNN`. Se validan al crear/editar. El endpoint de sugerencia toma el máximo existente incluyendo filas dadas de baja; la unicidad en base de datos resuelve carreras.
7. **Conectar la interfaz con el contrato generado.** Exportar OpenAPI y ejecutar `npm run gen:api`. La lista envía búsqueda, filtros y paginación al servidor; el detalle consulta `GET /{id}`; el formulario envía el contrato directo y muestra errores 409/422 por campo. Formatos y estados se presentan con selectores. Los controles de carga de fotos/archivos no se ofrecen hasta implementar almacenamiento.
8. **Eliminar contenido de demostración del detalle.** Mostrar solo campos recibidos de la API. Quitar identificadores de documentos, asignaciones, experiencia o “último uso” cuando no hay una fuente persistida para esos valores.
9. **Probar cada módulo.** Cubrir formatos, campos extra, listas permitidas, unicidad activa/archivada, sugerencia que no reutiliza códigos, edición parcial, filtros, paginación, detalle oculto tras baja, reactivación y matriz de roles. Ejecutar backend, Vitest, `tsc`, Ruff y `alembic check`.

### Campos y límites actuales

- Conductores: documento y número de licencia son únicos; categoría y vencimientos de licencia/examen médico quedan tipados. Estado manual: `disponible`, `descanso`, `inactivo`.
- Vehículos: placa y VIN existentes, más código de flota único, tipo y capacidad. Tipo permitido: `Camión`, `Furgón`, `Camioneta`, `Tráiler`. Estado manual: `disponible`, `mantenimiento`, `inactivo`.
- Rutas: código único, estado, distancia en km, duración en minutos, peajes y tarifa como enteros en unidad mínima, y moneda obligatoria. En esta implementación solo se admite PEN; cada ruta guarda `PEN`.
- Los valores de columna y el JSON legado coexisten. La migración de limpieza del JSON sigue pendiente.
- En el Lote 1 esas bajas quedaron temporalmente pendientes porque viajes todavía no se había migrado. El Lote 2 ya añade la validación en servicio y pruebas para vehículo, conductor y ruta con viajes activos.

## Lote 2 aplicado: cargas, viajes y cotizaciones (backend)

1. **Relación normalizada.** `cargas.trip_id` es nullable y FK a viajes; un viaje puede tener cargas de clientes distintos. No se usa `viajes.load_id`. Las migraciones iniciales archivadas se sustituyeron por una baseline explícita; no usar `Base.metadata.create_all` dentro de migraciones.
2. **Contratos estrictos.** Cargas, viajes y cotizaciones usan modelos Pydantic separados para creación, edición parcial y respuesta con `extra="forbid"`. Los endpoints directos reciben el body del recurso, sin `{data: ...}`. Los filtros y la paginación llegan al servicio y repositorio.
3. **Cargas y capacidad.** Guardar los pesos totales en kg. Para validar capacidad, sumar peso bruto; usar neto cuando falte bruto y devolver `peso_incompleto` para advertencia. Si falta todo peso o se excede capacidad, rechazar asignación con 409. No exigir monto antes de entrega; cobrar una carga sin importe debe rechazarse cuando se implemente el módulo de pagos.
4. **Viajes.** Validar cliente/carga/conductor/vehículo/ruta existentes y activos; bloquear filas del vehículo y conductor con `SELECT FOR UPDATE` antes de comprobar solapamientos. El viaje admite varias cargas. Al cancelar uno programado, liberar las cargas y devolverlas a `pendiente`. Entregar cargas individualmente; el viaje se completa al cerrar todas.
5. **Estados y auditoría.** Validar transiciones de viaje en servicio. Los cambios de cargas son libres mientras el viaje esté programado; durante viaje en curso/incidencia solo admin con motivo guardado; después de entrega/cancelación quedan bloqueados. `en_viaje` de conductor/vehículo se deriva del viaje y no se persiste como estado manual.
6. **Portal multi-cliente.** Derivar los viajes desde las cargas del `client_id` autenticado. El viaje del portal expone estado, fechas y ruta; omitir `cargas_ids`, otros clientes, conductor, vehículo e importes incluso si el viaje comparte camión.
7. **Cotizaciones y dinero.** Almacenar precios y totales en céntimos PEN. Cada línea acepta cantidad decimal positiva, precio unitario en céntimos no negativo y orden único. Calcular con `Decimal` y `ROUND_HALF_UP`; descuento sobre subtotal, impuesto sobre importe tras descuento y tasa explícita en puntos base (0 por defecto). Los estados son editables manualmente; no convertir una cotización en carga en este lote.
8. **Concurrencia revisada.** SQLite en memoria no ejecuta bloqueos de fila y no puede demostrar una carrera de dos transacciones. Antes de retirar las suites por solicitud del proyecto, se validó que el SQL compila con `FOR UPDATE` para MySQL y se probaron solapamientos secuenciales; una carrera concurrente real debe ejecutarse en integración MySQL antes de producción.
9. **Suite mínima.** Probar referencias inactivas, exceso de capacidad, carga sin peso, asignación/desasignación multi-carga, transiciones, cancelación, bajas bloqueadas, status derivado, permisos, portal con dos clientes en un viaje, validación de líneas y redondeos de 0/positivo impuesto. Regenerar OpenAPI y tipos después de cambiar esquemas o respuestas.
