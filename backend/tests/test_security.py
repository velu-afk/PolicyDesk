"""
Security & Role-Based Access Control (RBAC) Automated Tests:
- Normal users cannot upload documents (HTTP 403)
- Normal users cannot delete documents (HTTP 403)
- Normal users cannot access admin user-management endpoints (HTTP 403)
- Unauthenticated requests receive HTTP 401
- Users cannot access or delete conversations belonging to other users (HTTP 403)
"""
import unittest
from tests.conftest import (
    create_test_users,
    get_test_client,
    reset_test_database,
)


class TestSecurityAndRBAC(unittest.TestCase):
    def setUp(self) -> None:
        reset_test_database()
        self.client = get_test_client()
        self.admin_headers, self.user_headers = create_test_users()

    def test_unauthenticated_requests_return_401(self) -> None:
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client.get("/api/documents").status_code, 401)
        self.assertEqual(self.client.get("/api/admin/documents").status_code, 401)
        self.assertEqual(
            self.client.post("/api/chat/ask", json={"question": "Hello?"}).status_code,
            401,
        )

    def test_normal_users_cannot_upload_documents(self) -> None:
        resp = self.client.post(
            "/api/admin/documents/upload",
            headers=self.user_headers,
            files={"file": ("unauthorized.txt", b"Some policy content", "text/plain")},
        )
        self.assertEqual(resp.status_code, 403)

    def test_normal_users_cannot_delete_documents(self) -> None:
        upload = self.client.post(
            "/api/admin/documents/upload",
            headers=self.admin_headers,
            files={
                "file": (
                    "official_policy.txt",
                    b"Official policy document content for testing.",
                    "text/plain",
                )
            },
        )
        self.assertEqual(upload.status_code, 201)
        doc_id = upload.json()["id"]

        del_attempt = self.client.delete(
            f"/api/admin/documents/{doc_id}",
            headers=self.user_headers,
        )
        self.assertEqual(del_attempt.status_code, 403)

    def test_normal_users_cannot_access_admin_user_management(self) -> None:
        self.assertEqual(
            self.client.get("/api/admin/users", headers=self.user_headers).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                "/api/admin/users/1",
                headers=self.user_headers,
                json={"role": "admin"},
            ).status_code,
            403,
        )

    def test_users_cannot_access_or_delete_other_users_conversations(self) -> None:
        # User 1 (normal user) creates a conversation
        self.client.post(
            "/api/admin/documents/upload",
            headers=self.admin_headers,
            files={
                "file": (
                    "pto.txt",
                    b"Full-time employees receive 22 days of PTO per year.",
                    "text/plain",
                )
            },
        )
        ask_resp = self.client.post(
            "/api/chat/ask",
            headers=self.user_headers,
            json={"question": "How many days of PTO do employees receive?"},
        )
        self.assertEqual(ask_resp.status_code, 200)
        conv_id = ask_resp.json()["conversation_id"]

        # Register a second user
        reg_resp = self.client.post(
            "/api/auth/register",
            json={
                "name": "Second User",
                "email": "second.user@policydesk.io",
                "password": "SecondUserPass_2026!",
            },
        )
        user2_token = reg_resp.json()["access_token"]
        user2_headers = {"Authorization": f"Bearer {user2_token}"}

        # Second user attempts to read User 1's conversation -> HTTP 403
        read_attempt = self.client.get(
            f"/api/chat/conversations/{conv_id}",
            headers=user2_headers,
        )
        self.assertEqual(read_attempt.status_code, 403)

        # Second user attempts to post into User 1's conversation -> HTTP 403
        post_attempt = self.client.post(
            "/api/chat/ask",
            headers=user2_headers,
            json={"question": "Follow up?", "conversation_id": conv_id},
        )
        self.assertEqual(post_attempt.status_code, 403)

        # Second user attempts to delete User 1's conversation -> HTTP 403
        del_attempt = self.client.delete(
            f"/api/chat/conversations/{conv_id}",
            headers=user2_headers,
        )
        self.assertEqual(del_attempt.status_code, 403)


if __name__ == "__main__":
    unittest.main()
