# Progreso del Bloque 1 — Backend completo del Lote 2

## Preparación
- [x] Registrar decisiones aprobadas en `docs/DECISIONES.md`.
- [x] Crear checklist de trabajo en este archivo antes de cambios de implementación.
- [x] Revisar `docs/DECISIONES.md`, `docs/PROGRESO.md` y `docs/BASE_DE_DATOS.md` al comenzar la Etapa 1 (al inicio `BASE_DE_DATOS.md` no existía; se creó y se releerá al iniciar etapas 2 y 3).

## Etapa 1 — Base de datos y modelos
- [x] Actualizar modelos de cargas, viajes y cotizaciones al esquema final.
- [x] Eliminar usos de `viajes.load_id` del código de producción; usar `cargas.trip_id`.
- [x] Archivar revisiones legacy 0001–0007 sin borrarlas en `backend/migrations/archive_legacy/`.
- [x] Generar contra base vacía y revisar una baseline explícita 0001 con tablas, FKs, índices y unicidades; sin `Base.metadata.create_all`.
- [x] Implementar downgrade completo y comprobar que `env.py` importa el registro de todos los modelos.
- [x] Respaldar `transporte_frutas`, recrear solo esa base bajo protección de entorno/confirmación, aplicar `upgrade head`, sembrar y validar `current`/`check`.
- [x] En `transporte_frutas_tmp_migraciones`, probar `upgrade head → downgrade base → upgrade head`, dejar la base sin borrarla y comparar esquema; desarrollo y temporal coinciden.
- [x] Crear `docs/BASE_DE_DATOS.md` desde modelos e introspección de la base.

Estado de etapa: **completa**. Verificado en MySQL: desarrollo y temporal tienen 17 tablas idénticas; ambas están en `0001_baseline` y `alembic check` no detecta cambios. El downgrade del baseline se corrigió para quitar tablas en orden de dependencia y el ciclo temporal completo pasó.

## Etapa 2 — Cargas y viajes
- [x] Crear esquemas estrictos create/update/response y migrar cargas/viajes a la fábrica.
- [x] Aplicar referencias activas, estados, asignaciones, capacidad y montos.
- [x] Aplicar transiciones, solapamientos con bloqueo, disponibilidad calculada y restricciones de baja.
- [x] Aplicar reglas de edición de cargas según estado del viaje.
- [x] Adaptar el portal al viaje multi-carga sin fuga entre clientes.
- [x] Añadir pruebas de validaciones, referencias, transiciones, limitación de concurrencia SQLite/MySQL, bajas, disponibilidad, capacidad, asignación, permisos y aislamiento.
- [x] Regenerar OpenAPI y tipos frontend.

Estado de etapa: **completa**. Backend: 73 pruebas aprobadas (incluida prueba de cláusula `FOR UPDATE` para MySQL); en memoria SQLite no se puede simular contención de bloqueos, documentado en `DECISIONES.md`. `alembic current` sigue en `0001_baseline`; `alembic check` limpio; OpenAPI y tipos regenerados.

## Etapa 3 — Cotizaciones
- [x] Crear esquemas estrictos de cotización y líneas, fechas y estados válidos.
- [x] Calcular subtotal, descuento, impuesto y total con Decimal/ROUND_HALF_UP en céntimos PEN.
- [x] Migrar cotizaciones a la fábrica.
- [x] Añadir pruebas de cálculos, redondeos, validaciones, estados y permisos.
- [x] Regenerar OpenAPI y tipos frontend.

Estado de etapa: **completa**. Cotizaciones recibe líneas estrictas con cantidad y orden, estado manual, referencias activas y cálculos sin `float`; impuesto por defecto 0 bps. Se corrigió el serializador común de errores 422 para convertir detalles de Pydantic a JSON.

## Cierre
- [x] Actualizar `docs/PLAYBOOK_MODULO.md`.
- [x] Backend tests (74), Vitest (35), `tsc --noEmit`, Ruff, lint, `alembic current` (`0001_baseline`) y `alembic check` (limpio).
- [x] Informar decisiones predeterminadas, parciales y nombre exacto de la base temporal.

Estado final: todas las tareas de backend del bloque completadas. OpenAPI y tipos generados. La raíz/backend no pertenecen a un repositorio Git; `frontend/` es un repo separado con modificaciones sin relación con el alcance y no se creó un commit parcial. La base de desarrollo y `transporte_frutas_tmp_migraciones` se mantienen intactas; esquema de ambas idéntico.

## Limpieza posterior solicitada

- [x] Retirar los archivos fuente de prueba backend/frontend y la configuración de Vitest.
- [x] Retirar la dependencia/comando Vitest del frontend y dependencias de test Python del runtime.
- [x] Formatear el código Python de `backend/app` con Ruff y ordenar los archivos principales de navegación/API del frontend.
- [ ] Limpiar artefactos compilados/caché de pytest: los directorios contienen archivos bloqueados por el entorno y no se pudieron retirar con la operación de archivos.

La última verificación funcional registrada antes de borrar las suites fue backend 74 y Vitest 35. Ya no hay suites para volver a ejecutar; lint y type-check se vuelven a verificar tras la limpieza.

## Órdenes de mantenimiento vehicular — 24 de octubre de 2026

- [x] Selector de vehículos por placa/código con carga de todas las páginas y estados de error/vacío.
- [x] Catálogo de cinco tipos de servicio del PDF de referencia.
- [x] Duración estimada en horas, ingreso al taller, inicio/fin y duración real calculada por el servidor.
- [x] Kilometraje, prioridad, motivo, diagnóstico, trabajo realizado y observaciones.
- [x] Alta y edición con validación de referencias, fechas, duración y costo; conservación de registros anteriores.
- [x] Tabla con placa, servicio, duración estimada/real y fecha programada.
- [x] TypeScript, ESLint, Ruff y pruebas HTTP aisladas en SQLite: alta, edición, filtro por vehículo, baja lógica y entradas inválidas.

Se conserva la FK existente `mantenimiento.vehicle_id`; los campos adicionales se guardan en `data`, sin migrar ni recrear la base. Se mantienen los cuatro estados operativos actuales. El catálogo de servicios es fijo; la normalización en tablas de tareas, repuestos, proveedores e historial del PDF queda fuera de este cambio. Las fechas con hora se envían como ISO con zona horaria y la duración real se recalcula al guardar.

Compilación de producción Next.js completada correctamente (47 rutas).

## Rutas con ciudades y paradas — 24 de octubre de 2026

- [x] Ciudades reutilizables, FKs de origen/destino y paradas relacionales ordenadas con espera.
- [x] Formulario con alta de ciudades, selectores, añadir/quitar/reordenar paradas y vista previa del recorrido.
- [x] Conservación de IDs de rutas, bajas/reactivación y restricciones por viajes activos.
- [x] Pruebas HTTP aisladas de CRUD, validación y reordenación; migración upgrade/downgrade/upgrade con datos legacy en SQLite temporal.
- [x] Respaldo y aplicación de revisión 0002 en desarrollo; `alembic check` sin cambios pendientes.
- [x] Compilación de producción, TypeScript, ESLint, Ruff y actualización de OpenAPI/tipos.

Desarrollo tenía cero rutas al migrar. No se recreó la base ni se insertaron datos demostrativos.

## Cargas y viajes por etapas — 24 de octubre de 2026

- [x] Registro único de carga con identificación, producto, cantidades, pesos, contactos, ubicación, condiciones y archivos.
- [x] Tabla detalle_carga_viajes con orden, FKs de ciudades/viaje/carga y fechas reales.
- [x] Programación de viajes con selectores y asignación directa opcional; plan multi-viaje desde el detalle de la carga.
- [x] Validación de ruta/sentido, continuidad, horario, cliente activo y capacidad por segmento.
- [x] Seguimiento real de etapas, estado global calculado y protección de historial iniciado.
- [x] Archivos en servidor con metadatos, límite de tamaño y autorización de descarga.
- [x] Portal consulta todos los viajes de las cargas propias sin filtrar por el antiguo puntero único.
- [x] Migración probada en SQLite temporal con asignación legacy y ciclo upgrade/downgrade/upgrade.
- [x] Respaldo y migración 0003 aplicados en desarrollo; alembic check limpio.
- [x] Siete pruebas de integración HTTP aisladas aprobadas, incluyendo tres transbordos, capacidad por segmento, continuidad/horarios, estados, archivos y aislamiento por cliente.

Comando de pruebas: `backend/venv/Scripts/python.exe -m unittest discover -s backend/tests -p test_transport_stages.py -v` desde una ubicación con backend en PYTHONPATH, o ejecutar desde backend con `venv/Scripts/python.exe -m unittest discover -s tests -p test_transport_stages.py -v`. No se realizaron pruebas de contención concurrente real en MySQL.

Validación final del bloque: siete pruebas HTTP aprobadas, Ruff y ESLint limpios, OpenAPI y tipos actualizados; compilación de producción Next.js y TypeScript correctos.

## Cortes de saldo de jabas por cliente

- [x] Reinicio individual con confirmación; conserva el historial sin borrar cargas ni retornos.
- [x] Registro auditable del corte con cantidades previas, fecha, cliente y usuario que lo ejecutó.
- [x] Las cargas y retornos nuevos quedan asociados al periodo vigente; el saldo comienza nuevamente en cero.
- [x] Las cargas anteriores al corte dejan de aparecer para registrar retornos y la API también impide asociarles nuevos retornos.
- [x] Historial de cortes visible; reinicio restringido al rol administrador.
- [x] Migración 0006 y pruebas de integración para corte, actividad posterior, restricción de cargas antiguas y permisos.

## Biblioteca centralizada de documentos

- [x] Vista de archivos con búsqueda, filtros por carpeta y descarga.
- [x] Carpetas de vehículos y viajes muestran adjuntos directos y documentos de registros relacionados como cargas, gastos, combustible y mantenimiento.
- [x] Carga directa de archivos a la carpeta de un vehículo o viaje, con límite de 10 MB y formatos permitidos.
- [x] Archivos existentes permanecen en sus ubicaciones actuales; la biblioteca los indexa sin copiarlos.
- [x] Pruebas HTTP de agrupación, carga y descarga; Ruff, ESLint y TypeScript.
