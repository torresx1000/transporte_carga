import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.permissions import get_current_user, permission_for_route
from app.main import app
from app.models.entities import Client, User
from app.models.roles import AccessRole


class DynamicRolesTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = User(
            id="admin-1",
            email="admin@example.test",
            password_hash="test-hash",
            role="admin",
            active=True,
            data={},
        )
        self.operator_role = AccessRole(
            id="role-operator",
            slug="operador",
            name="Operaciones",
            description="",
            permissions=["cargas.ver"],
            is_system=True,
            data={},
        )
        self.operator = User(
            id="operator-1",
            email="operator@example.test",
            password_hash="test-hash",
            role="operador",
            permission_role=self.operator_role,
            active=True,
            data={},
        )
        self.db.add_all([self.admin, self.operator_role, self.operator])
        self.db.commit()
        self.actor_id = self.admin.id
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.db.get(User, self.actor_id)
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_permission_catalog_maps_routes_to_independent_actions(self):
        self.assertEqual(permission_for_route("/api/v1/cargas", "GET"), "cargas.ver")
        self.assertEqual(permission_for_route("/api/v1/cargas", "POST"), "cargas.crear")
        self.assertEqual(
            permission_for_route("/api/v1/cargas/{load_id}/estado", "POST"),
            "cargas.cambiar_estado",
        )
        catalog = self.client.get("/api/v1/roles/catalog")
        self.assertEqual(catalog.status_code, 200, catalog.text)
        keys = {item["key"] for item in catalog.json()}
        self.assertIn("cargas.ver", keys)
        self.assertIn("cargas.crear", keys)
        self.assertIn("usuarios.asignar_roles", keys)

    def test_role_permissions_are_applied_on_each_request(self):
        self.actor_id = self.operator.id
        self.assertEqual(self.client.get("/api/v1/cargas").status_code, 200)
        denied = self.client.post("/api/v1/gastos", json={"data": {}})
        self.assertEqual(denied.status_code, 403, denied.text)

        self.actor_id = self.admin.id
        update = self.client.patch(
            f"/api/v1/roles/{self.operator_role.id}",
            json={"permissions": []},
        )
        self.assertEqual(update.status_code, 200, update.text)

        self.actor_id = self.operator.id
        revoked = self.client.get("/api/v1/cargas")
        self.assertEqual(revoked.status_code, 403, revoked.text)

    def test_non_admin_cannot_grant_permissions_they_do_not_hold(self):
        manager_role = AccessRole(
            id="role-manager",
            slug="manager",
            name="Gestor",
            description="",
            permissions=[
                "roles.ver",
                "roles.crear",
                "permisos.gestionar",
                "usuarios.asignar_roles",
                "cargas.ver",
            ],
            is_system=False,
            data={},
        )
        manager = User(
            id="manager-1",
            email="manager@example.test",
            password_hash="test-hash",
            role="operador",
            permission_role=manager_role,
            active=True,
            data={},
        )
        self.db.add_all([manager_role, manager])
        self.db.commit()
        self.actor_id = manager.id
        response = self.client.post(
            "/api/v1/roles",
            json={"name": "Carga admin", "permissions": ["cargas.eliminar"]},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(self.client.get("/api/v1/roles/audit").status_code, 200)

    def test_user_creation_cannot_assign_permissions_outside_the_actors_scope(self):
        manager_role = AccessRole(
            id="role-manager-create",
            slug="manager-create",
            name="Gestor de usuarios",
            description="",
            permissions=["usuarios.crear", "usuarios.asignar_roles", "cargas.ver"],
            is_system=False,
            data={},
        )
        restricted_role = AccessRole(
            id="role-restricted",
            slug="restricted",
            name="Restringido",
            description="",
            permissions=["cargas.eliminar"],
            is_system=False,
            data={},
        )
        manager = User(
            id="manager-create-1",
            email="manager-create@example.test",
            password_hash="test-hash",
            role="operador",
            permission_role=manager_role,
            active=True,
            data={},
        )
        self.db.add_all([manager_role, restricted_role, manager])
        self.db.commit()

        self.actor_id = manager.id
        denied = self.client.post(
            "/api/v1/usuarios",
            json={
                "email": "new-user@example.test",
                "password": "StrongPass123",
                "role": "restricted",
            },
        )
        self.assertEqual(denied.status_code, 403, denied.text)

        self.actor_id = self.admin.id
        created = self.client.post(
            "/api/v1/usuarios",
            json={
                "email": "new-user@example.test",
                "password": "StrongPass123",
                "role": "restricted",
                "active": False,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["role"], "restricted")
        self.assertFalse(created.json()["active"])
        audit = self.client.get("/api/v1/roles/audit")
        self.assertEqual(audit.status_code, 200, audit.text)
        self.assertTrue(
            any(entry["action"] == "asignar_rol" for entry in audit.json())
        )

    def test_user_role_and_active_state_can_be_updated_with_scoped_permissions(self):
        manager_role = AccessRole(
            id="role-user-manager",
            slug="user-manager",
            name="Gestor de usuarios",
            description="",
            permissions=["usuarios.editar", "usuarios.asignar_roles", "cargas.ver"],
            is_system=False,
            data={},
        )
        assignable_role = AccessRole(
            id="role-limited",
            slug="limited",
            name="Limitado",
            description="",
            permissions=["cargas.ver"],
            is_system=False,
            data={},
        )
        forbidden_role = AccessRole(
            id="role-privileged",
            slug="privileged",
            name="Privilegiado",
            description="",
            permissions=["cargas.eliminar"],
            is_system=False,
            data={},
        )
        manager = User(
            id="user-manager-1",
            email="user-manager@example.test",
            password_hash="test-hash",
            role="operador",
            permission_role=manager_role,
            active=True,
            data={},
        )
        self.db.add_all([manager_role, assignable_role, forbidden_role, manager])
        self.db.commit()

        self.actor_id = manager.id
        roles = self.client.get("/api/v1/roles/assignable")
        self.assertEqual(roles.status_code, 200, roles.text)
        role_slugs = {role["slug"] for role in roles.json()}
        self.assertIn("limited", role_slugs)
        self.assertNotIn("privileged", role_slugs)
        self.assertNotIn("admin", role_slugs)

        updated = self.client.patch(
            f"/api/v1/usuarios/{self.operator.id}",
            json={"role": "limited", "active": False},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["role"], "limited")
        self.assertEqual(updated.json()["role_name"], "Limitado")
        self.assertFalse(updated.json()["active"])

        self.db.refresh(self.operator)
        self.assertEqual(self.operator.permission_role_id, assignable_role.id)
        self.assertFalse(self.operator.active)

        self.operator.active = True
        self.db.commit()
        denied = self.client.patch(
            f"/api/v1/usuarios/{self.operator.id}",
            json={"role": "privileged"},
        )
        self.assertEqual(denied.status_code, 403, denied.text)

    def test_customer_role_requires_a_client_and_limits_permissions_to_portal(self):
        client = Client(
            id="customer-1",
            name="Cliente Uno",
            status="activo",
            data={},
        )
        customer_role = AccessRole(
            id="role-customer",
            slug="cliente",
            name="Cliente",
            description="",
            permissions=["portal.ver_cargas", "portal.ver_me", "cargas.ver", "usuarios.ver"],
            is_system=True,
            data={},
        )
        customer_user = User(
            id="customer-user-1",
            email="customer-user@example.test",
            password_hash="test-hash",
            role="operador",
            permission_role=self.operator_role,
            active=True,
            data={"name": "Cuenta cliente"},
        )
        self.db.add_all([client, customer_role, customer_user])
        self.db.commit()

        self.actor_id = self.admin.id
        client_options = self.client.get("/api/v1/roles/clients")
        self.assertEqual(client_options.status_code, 200, client_options.text)
        self.assertEqual(client_options.json()[0]["id"], client.id)
        missing_client = self.client.put(
            f"/api/v1/roles/{customer_role.id}/users/{customer_user.id}"
        )
        self.assertEqual(missing_client.status_code, 422, missing_client.text)

        assigned = self.client.put(
            f"/api/v1/roles/{customer_role.id}/users/{customer_user.id}",
            json={"client_id": client.id},
        )
        self.assertEqual(assigned.status_code, 200, assigned.text)
        self.db.refresh(customer_user)
        self.assertEqual(str(customer_user.role), "cliente")
        self.assertEqual(customer_user.data["client_id"], client.id)

        self.actor_id = customer_user.id
        self.assertEqual(self.client.get("/api/v1/cargas").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/usuarios").status_code, 403)
        profile = self.client.get("/api/v1/portal/me")
        self.assertEqual(profile.status_code, 200, profile.text)
        self.assertEqual(profile.json()["cliente_nombre"], client.name)
        self.assertEqual(self.client.get("/api/v1/portal/cargas").json(), [])
        permissions = self.client.get("/api/v1/roles/me")
        self.assertEqual(permissions.status_code, 200, permissions.text)
        self.assertEqual(
            set(permissions.json()["permissions"]),
            {"portal.ver_cargas", "portal.ver_me"},
        )

    def test_creating_client_user_requires_a_valid_client_link(self):
        client = Client(
            id="new-client-1",
            name="Cliente Nuevo",
            status="activo",
            data={},
        )
        self.db.add(client)
        self.db.commit()
        self.actor_id = self.admin.id
        self.client.get("/api/v1/roles/assignable")

        missing = self.client.post(
            "/api/v1/usuarios",
            json={
                "email": "new-client-user@example.test",
                "password": "StrongPass123",
                "role": "cliente",
            },
        )
        self.assertEqual(missing.status_code, 422, missing.text)

        created = self.client.post(
            "/api/v1/usuarios",
            json={
                "email": "new-client-user@example.test",
                "password": "StrongPass123",
                "role": "cliente",
                "client_id": client.id,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["data"]["client_id"], client.id)

    def test_users_cannot_assign_roles_to_themselves_or_change_admin_access(self):
        self.actor_id = self.admin.id
        roles = self.client.get("/api/v1/roles")
        self.assertEqual(roles.status_code, 200, roles.text)
        admin_role = next(item for item in roles.json() if item["slug"] == "admin")
        self.assertEqual(
            self.client.patch(
                f"/api/v1/roles/{admin_role['id']}",
                json={"permissions": []},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.put(
                f"/api/v1/roles/{self.operator_role.id}/users/{self.admin.id}"
            ).status_code,
            403,
        )

        self.actor_id = self.operator.id
        self.assertEqual(
            self.client.put(
                f"/api/v1/roles/{self.operator_role.id}/users/{self.operator.id}"
            ).status_code,
            403,
        )

    def test_unassigning_a_role_keeps_the_user_without_access(self):
        self.actor_id = self.admin.id
        response = self.client.delete(
            f"/api/v1/roles/{self.operator_role.id}/users/{self.operator.id}"
        )
        self.assertEqual(response.status_code, 204, response.text)

        self.actor_id = self.operator.id
        permissions = self.client.get("/api/v1/roles/me")
        self.assertEqual(permissions.status_code, 200, permissions.text)
        self.assertEqual(permissions.json()["role"], "sin-acceso")
        self.assertEqual(permissions.json()["permissions"], [])
        self.assertEqual(self.client.get("/api/v1/cargas").status_code, 403)

    def test_sin_acceso_role_cannot_be_granted_permissions_and_is_repaired(self):
        no_access_role = AccessRole(
            id="role-no-access",
            slug="sin-acceso",
            name="Sin acceso",
            description="Usuario sin permisos de acceso.",
            permissions=["cargas.ver", "conductores.editar"],
            is_system=True,
            data={},
        )
        no_access_user = User(
            id="no-access-user",
            email="no-access@example.test",
            password_hash="test-hash",
            role="operador",
            permission_role=no_access_role,
            active=True,
            data={},
        )
        self.db.add_all([no_access_role, no_access_user])
        self.db.commit()

        self.actor_id = self.admin.id
        denied_update = self.client.patch(
            f"/api/v1/roles/{no_access_role.id}",
            json={"permissions": ["cargas.ver"]},
        )
        self.assertEqual(denied_update.status_code, 403, denied_update.text)
        denied_delete = self.client.delete(f"/api/v1/roles/{no_access_role.id}")
        self.assertEqual(denied_delete.status_code, 403, denied_delete.text)

        self.actor_id = no_access_user.id
        permissions = self.client.get("/api/v1/roles/me")
        self.assertEqual(permissions.status_code, 200, permissions.text)
        self.assertEqual(permissions.json()["permissions"], [])
        self.assertEqual(self.client.get("/api/v1/cargas").status_code, 403)
        self.db.refresh(no_access_role)
        self.assertEqual(no_access_role.permissions, [])

        audit = self.client.get("/api/v1/roles/audit")
        self.assertEqual(audit.status_code, 403)
        self.actor_id = self.admin.id
        audit = self.client.get("/api/v1/roles/audit")
        self.assertTrue(
            any(entry["action"] == "proteger_rol" for entry in audit.json())
        )

    def test_generic_user_update_does_not_change_role_and_rejects_role_edits(self):
        self.actor_id = self.admin.id
        update = self.client.patch(
            f"/api/v1/usuarios/{self.operator.id}",
            json={"name": "Operador actualizado"},
        )
        self.assertEqual(update.status_code, 200, update.text)
        self.assertEqual(update.json()["data"]["name"], "Operador actualizado")

        role_update = self.client.patch(
            f"/api/v1/usuarios/{self.operator.id}",
            json={"role": "admin"},
        )
        self.assertEqual(role_update.status_code, 403, role_update.text)


if __name__ == "__main__":
    unittest.main()
