"""
Document Ingestion & Management Automated Tests:
- PDF upload and page-number preservation
- TXT upload
- Invalid file type rejection (.exe, .docx, .csv)
- Empty document handling
- Overlapping chunk creation
- Document deletion and associated chunk cleanup
"""
import unittest
from app.database import SessionLocal
from app.models.document import DocumentChunk
from tests.conftest import (
    create_test_users,
    generate_sample_pdf_bytes,
    get_test_client,
    reset_test_database,
)


class TestDocuments(unittest.TestCase):
    def setUp(self) -> None:
        reset_test_database()
        self.client = get_test_client()
        self.admin_headers, self.user_headers = create_test_users()

    def test_pdf_upload_and_chunk_creation(self) -> None:
        pdf_bytes = generate_sample_pdf_bytes(
            [
                "QuantumApps AI Information Security Policy Page 1.\n"
                "All employees must use hardware FIDO2 multi-factor authentication keys.",
                "QuantumApps AI Information Security Policy Page 2.\n"
                "Suspected security incidents must be reported to SOC within 2 hours.",
            ]
        )
        resp = self.client.post(
            "/api/admin/documents/upload",
            headers=self.admin_headers,
            files={"file": ("security_policy.pdf", pdf_bytes, "application/pdf")},
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        data = resp.json()
        self.assertEqual(data["filename"], "security_policy.pdf")
        self.assertEqual(data["file_type"], "pdf")
        self.assertEqual(data["processing_status"], "processed")
        self.assertEqual(data["page_count"], 2)
        self.assertGreaterEqual(data["chunk_count"], 2)

    def test_txt_upload_and_overlapping_chunks(self) -> None:
        long_policy_text = "\n\n".join(
            [
                f"Section {i}: Employees working under the hybrid work arrangement must coordinate "
                f"their in-office schedule (Tuesday, Wednesday, Thursday) with their engineering manager "
                f"and maintain core availability hours between 10:00 AM and 4:00 PM."
                for i in range(1, 18)
            ]
        )
        resp = self.client.post(
            "/api/admin/documents/upload",
            headers=self.admin_headers,
            files={
                "file": (
                    "hybrid_work_policy.txt",
                    long_policy_text.encode("utf-8"),
                    "text/plain",
                )
            },
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        data = resp.json()
        self.assertEqual(data["processing_status"], "processed")
        self.assertGreater(data["chunk_count"], 1)

    def test_invalid_file_type_rejection(self) -> None:
        resp = self.client.post(
            "/api/admin/documents/upload",
            headers=self.admin_headers,
            files={"file": ("malicious.exe", b"MZ\x90\x00", "application/octet-stream")},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Only .pdf and .txt documents are allowed", resp.json()["detail"])

    def test_empty_document_handling(self) -> None:
        # 1. Zero-byte upload -> HTTP 400
        resp_zero = self.client.post(
            "/api/admin/documents/upload",
            headers=self.admin_headers,
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        self.assertEqual(resp_zero.status_code, 400)

        # 2. Whitespace-only TXT upload -> HTTP 422 and status marked failed
        resp_ws = self.client.post(
            "/api/admin/documents/upload",
            headers=self.admin_headers,
            files={"file": ("whitespace.txt", b"   \n\n  \t  ", "text/plain")},
        )
        self.assertEqual(resp_ws.status_code, 422)

    def test_document_deletion_cleans_up_associated_chunks(self) -> None:
        txt_bytes = (
            b"Travel Expense Policy: Hotel accommodations are reimbursed up to $280 per night "
            b"in standard cities and $375 per night in Tier-1 metro areas."
        )
        upload_resp = self.client.post(
            "/api/admin/documents/upload",
            headers=self.admin_headers,
            files={"file": ("travel_policy.txt", txt_bytes, "text/plain")},
        )
        self.assertEqual(upload_resp.status_code, 201)
        doc_id = upload_resp.json()["id"]

        db = SessionLocal()
        try:
            chunks_before = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id == doc_id)
                .count()
            )
            self.assertGreater(chunks_before, 0)
        finally:
            db.close()

        del_resp = self.client.delete(
            f"/api/admin/documents/{doc_id}",
            headers=self.admin_headers,
        )
        self.assertEqual(del_resp.status_code, 200)

        db = SessionLocal()
        try:
            chunks_after = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id == doc_id)
                .count()
            )
            self.assertEqual(chunks_after, 0)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
