# Sistema de Gestión de Cargas y Retornos — Backend

API FastAPI con SQLAlchemy 2, Pydantic 2, Alembic, JWT y bcrypt. Todos los endpoints de negocio requieren un token Bearer y usan respuestas JSON; las excepciones de dominio se envían con mensajes en español.

## Requisitos y configuración

Python 3.11 o superior. Instala dependencias en un entorno virtual con `pip install -r requirements.txt`. Copia `.env.example` a `.env` y configura `DATABASE_URL` y un `SECRET_KEY` aleatorio. La conexión original del proyecto usa MySQL/PyMySQL y se conserva; PostgreSQL se puede seleccionar con `postgresql+psycopg://...` si el servidor y la base ya están provisionados. SQLite es compatible para desarrollo y pruebas.

## Iniciar

Desde `backend/`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
$env:ADMIN_EMAIL = "admin@ejemplo.pe"
$env:ADMIN_PASSWORD = "cambia-esta-clave"
python seed_admin.py
uvicorn app.main:app --reload
```

Documentación interactiva: `http://localhost:8000/docs`. Health check: `http://localhost:8000/health`. CORS permite por defecto `http://localhost:3000`; ajusta `CORS_ORIGINS` para varios orígenes separados por coma.

### Cuentas de demostración (solo desarrollo)

El script `seed_demo_users.py` se niega a ejecutarse salvo que `APP_ENV` sea `development`, `dev`, `local` o `test`. En tu `.env` de desarrollo define `APP_ENV=development` y ejecuta `python seed_demo_users.py` después de aplicar las migraciones. Si `ADMIN_EMAIL` y `ADMIN_PASSWORD` están definidos juntos en el entorno o en `.env`, se usan para el admin; si ambos faltan, se usan las credenciales locales documentadas abajo. Estas credenciales son solo para desarrollo; no las uses en producción.

| Rol | Correo | Contraseña |
|---|---|---|
| admin | `admin.demo@transfrutas.local` | `DemoAdmin2026!` |
| operador | `operador.demo@transfrutas.local` | `DemoOperador2026!` |
| chofer | `chofer.demo@transfrutas.local` | `DemoChofer2026!` |
| cliente | `cliente.demo@transfrutas.local` | `DemoCliente2026!` |

La cuenta de cliente queda vinculada al cliente de demostración. La cuenta de chofer solo permite probar el rol: aún no existe vínculo usuario-conductor para asignarle operaciones.

## Cómo recrear o restaurar la base de desarrollo

La base local se limita intencionalmente a `localhost:3306/transporte_frutas`. Los scripts comprueban `APP_ENV=development`, leen las credenciales desde `DATABASE_URL` sin mostrarlas y no ejecutan `DROP` ni borrados.

Para crear un respaldo antes de migrar:

```powershell
.\scripts\db_backup\backup.ps1
```

El archivo SQL se guarda en `backend/backups/` con fecha y hora. La carpeta está excluida de Git. Crea un respaldo nuevo antes de cada migración, tanto al subir como al probar un downgrade.

Para recrear el esquema de desarrollo después de que la base haya sido eliminada accidentalmente:

```powershell
$env:APP_ENV = "development"
alembic upgrade head
python seed_demo_users.py
```

Para restaurar un respaldo, el destino debe existir y no tener tablas. El script se niega a sobrescribir bases con tablas y exige la confirmación escrita exacta:

```powershell
.\scripts\db_backup\restore.ps1 -BackupFile .\backups\transporte_frutas_YYYYMMDD_HHMMSS_fff.sql -Confirmation "RESTAURAR transporte_frutas"
```

La restauración tampoco elimina tablas o datos. Verifica `alembic current` y ejecuta `alembic upgrade head` solo cuando el contenido del respaldo corresponda al entorno de desarrollo.

## Áreas y rutas

Las rutas comienzan en `/api/v1`: `auth`, `usuarios`, `roles`, `clientes`, `conductores`, `vehiculos`, `rutas`, `cargas`, `viajes`, `cotizaciones`, `retornos`, `documentos`, `gastos`, `combustible`, `mantenimiento`, `pagos` y `configuracion`. Las listas aceptan `page`, `page_size`, `estado`, `cliente_id`, `vehiculo_id`, `conductor_id` y búsqueda `q`. El piloto `/clientes` recibe sus campos directamente según `ClienteCreate` y `ClienteUpdate`; los otros recursos conservan `{ "data": { ...campos del módulo... } }`. Las bajas son lógicas.

Autenticación: `POST /api/v1/auth/login` recibe formulario OAuth2 (`username` es el correo, más `password`) y emite access/refresh JWT. `POST /api/v1/auth/refresh` recibe `{ "refresh_token": "..." }`. El registro público siempre crea rol cliente; la creación de usuarios requiere `usuarios.crear`.

La pantalla Administración → Roles y permisos usa el catálogo dinámico de `GET /api/v1/roles/catalog`; los roles y sus miembros se administran en `/api/v1/roles`. Los permisos se evalúan en cada solicitud y los cambios de asignación o configuración quedan en `/api/v1/roles/audit`. Separa consulta (`roles.ver`), creación, edición, eliminación, gestión de permisos (`permisos.gestionar`) y asignación a usuarios (`usuarios.asignar_roles`). Aplica las migraciones con `alembic upgrade head` antes de usar esta funcionalidad.

El rol cliente solo tiene acceso a `/api/v1/portal/*`; asocia su usuario a un cliente mediante `client_id` al crearlo desde administración. Endpoints especiales: `/retornos/saldos-por-cliente`, `/clientes/{id}/estado-jabas`, `/documentos/por-vencer`, `/reportes/dashboard`, `/reportes/rentabilidad-viaje/{id}`, `/reportes/consumo-combustible` y `/reportes/jabas-pendientes`.

La biblioteca centralizada de archivos está en `/api/v1/documentos/biblioteca`: acepta `carpeta=todos|vehiculo|viaje`, búsqueda `q` y `propietario_id` para ver la carpeta de un vehículo o viaje con sus archivos relacionados. La carga directa admite vehículos y viajes mediante multipart (`propietario_tipo`, `propietario_id`, `archivo`); descarga por documento en `/api/v1/documentos/biblioteca/{document_id}/archivo`. Los archivos previamente asociados a cargas, gastos, combustible y otros recursos conservan su ubicación y se muestran en las carpetas relacionadas cuando corresponde.

El saldo de jabas se puede reiniciar por cliente desde la interfaz de Retornos. Cada corte se conserva en `/retornos/historial-cortes`; solo administradores pueden crear uno mediante `/retornos/clientes/{id}/reiniciar-saldo`. Las cargas y retornos posteriores se contabilizan en un periodo nuevo, sin borrar el historial anterior.

## Organización del código por módulo

Cada recurso de negocio tiene un paquete propio y archivos con el mismo nombre en las capas correspondientes. Por ejemplo, cargas usa `app/models/cargas/cargas.py`, `app/schemas/cargas/cargas.py`, `app/repositories/cargas/cargas.py`, `app/services/cargas/cargas.py` y `app/api/v1/endpoints/cargas/cargas.py`. Clientes, conductores, vehículos, rutas, viajes, cotizaciones, retornos, documentos, gastos, combustible, mantenimiento, pagos, usuarios y configuración siguen el mismo patrón. Los modelos asociados a desglose de retornos e ítems de cotización viven en paquetes separados.

`models/entities.py` registra los modelos para SQLAlchemy y Alembic; `schemas/common.py`, `repositories/records.py` y `services/records.py` contienen las piezas compartidas de paginación y CRUD. Las reglas comunes de autenticación, permisos y base de datos permanecen en `core/`. Los reportes y el portal son endpoints de consulta que operan sobre los módulos de negocio existentes.

## Calidad de código

Ejecuta Ruff con `python -m ruff check app tests` y las pruebas backend con `python -m pytest`.

## Nota de esquema

La migración inicial consolidada crea las tablas de todos los módulos. Las columnas e índices estables están tipados; los campos de formulario que están evolucionando se conservan en `data` JSON. Los importes se guardan en céntimos, pesos recibidos en toneladas se normalizan a kg y el Kardex de retornos admite un desglose de jabas por cliente. Antes de producción, conviene convertir a columnas tipadas los campos de negocio ya definitivos y revisar índices/constraints según el volumen esperado.
