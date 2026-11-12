"""
RAG Pipeline Automated Tests:
- Correct document retrieval
- Relevant source attribution (document name, document ID, passage, page number)
- Accurate answers based on document context
- Unknown questions result in an honest fallback
- No fabricated source citations on unknown questions
"""
import unittest
from tests.conftest import (
    create_test_users,
    generate_sample_pdf_bytes,
    get_test_client,
    reset_test_database,
)


class TestRAGPipeline(unittest.TestCase):
    def setUp(self) -> None:
        reset_test_database()
        self.client = get_test_client()
        self.admin_headers, self.user_headers = create_test_users()

        # Ingest a 2-page PDF policy and a TXT policy
        pdf_bytes = generate_sample_pdf_bytes(
            [
                "QUANTUMAPPS REMOTE WORK POLICY (PAGE 1)\n"
                "Full-time employees must work from their regional office at least 3 days per week "
                "(Tuesday, Wednesday, and Thursday). Employees may work remotely up to 2 days per week.",
                "QUANTUMAPPS HOME OFFICE STIPEND POLICY (PAGE 2)\n"
                "Newly hired full-time employees receive a one-time ergonomic home office setup stipend "
                "of $750 USD and a monthly high-speed internet reimbursement of $60 USD.",
            ]
        )
        self.client.post(
            "/api/admin/documents/upload",
            headers=self.admin_headers,
            files={"file": ("Remote_Work_Handbook.pdf", pdf_bytes, "application/pdf")},
        )

        leave_txt = (
            "PARENTAL LEAVE AND PTO POLICY\n"
            "Full-time employees accrue 22 days of Paid Time Off (PTO) per calendar year. "
            "Eligible caregivers receive 16 weeks of 100% paid parental leave."
        ).encode("utf-8")
        self.client.post(
            "/api/admin/documents/upload",
            headers=self.admin_headers,
            files={"file": ("Leave_and_Benefits_Policy.txt", leave_txt, "text/plain")},
        )

    def test_grounded_answer_and_source_attribution(self) -> None:
        resp = self.client.post(
            "/api/chat/ask",
            headers=self.user_headers,
            json={
                "question": "What is the ergonomic home office setup stipend and monthly internet reimbursement?"
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()

        self.assertIn("$750", data["answer"])
        self.assertIn("$60", data["answer"])
        self.assertTrue(data["retrieval_metadata"]["found_in_documents"])
        self.assertGreaterEqual(len(data["sources"]), 1)

        top_source = data["sources"][0]
        self.assertEqual(top_source["source_document_name"], "Remote_Work_Handbook.pdf")
        self.assertEqual(top_source["page_number"], 2)
        self.assertIn("$750", top_source["relevant_passage"])


    def test_unknown_question_returns_honest_fallback_without_fabricated_sources(self) -> None:
        resp = self.client.post(
            "/api/chat/ask",
            headers=self.user_headers,
            json={
                "question": "What is the propulsion thrust of the Saturn V rocket stage on Mars?"
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()

        self.assertIn(
            "could not find information to answer this question in the uploaded policy documents",
            data["answer"].lower(),
        )
        self.assertFalse(data["retrieval_metadata"]["found_in_documents"])
        self.assertEqual(data["sources"], [])


if __name__ == "__main__":
    unittest.main()
