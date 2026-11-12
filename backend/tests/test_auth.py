"""
Authentication & Role Assignment Automated Tests:
- Successful registration
- Successful login
- Incorrect password rejection
- New accounts always receive normal user role
- Privilege escalation via role field in registration is rejected
- Admin-only API rejection for normal users
"""
import unittest
from tests.conftest import (
    create_test_users,
    get_test_client,
    reset_test_database,
)


class TestAuthentication(unittest.TestCase):
    def setUp(self) -> None:
        reset_test_database()
        self.client = get_test_client()

    def test_successful_registration_assigns_normal_user_role(self) -> None:
        resp = self.client.post(
            "/api/auth/register",
            json={
                "name": "Priya Nair",
                "email": "priya.nair@example.com",
                "password": "StrongPassword_2026!",
            },
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["email"], "priya.nair@example.com")
        self.assertEqual(data["user"]["role"], "user")

    def test_registration_rejects_privilege_escalation_role_field(self) -> None:
        """Users must never be able to assign themselves the admin role during registration."""
        resp = self.client.post(
            "/api/auth/register",
            json={
                "name": "Attacker",
                "email": "attacker@example.com",
                "password": "StrongPassword_2026!",
                "role": "admin",
            },
        )
        # Pydantic extra="forbid" rejects unexpected `role` attribute with 422
        self.assertEqual(resp.status_code, 422)

    def test_successful_login_and_me_endpoint(self) -> None:
        create_test_users()
        resp = self.client.post(
            "/api/auth/login",
            json={
                "email": "employee@policydesk.io",
                "password": "EmployeeTestPass_2026!",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        token = resp.json()["access_token"]

        me_resp = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["email"], "employee@policydesk.io")
        self.assertEqual(me_resp.json()["role"], "user")

    def test_incorrect_password_rejection(self) -> None:
        create_test_users()
        resp = self.client.post(
            "/api/auth/login",
            json={
                "email": "employee@policydesk.io",
                "password": "WrongPassword999!",
            },
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid email or password", resp.json()["detail"])

    def test_admin_only_api_rejection_for_normal_users(self) -> None:
        _, user_headers = create_test_users()
        resp = self.client.get("/api/admin/users", headers=user_headers)
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
