# PolicyDesk — Enterprise RAG Document Assistant

**PolicyDesk** is a full-stack Retrieval-Augmented Generation (RAG) web application designed to help organizations manage and access internal policy documentation. Administrators upload corporate PDF and plain-text policy documents into a managed knowledge base, and authenticated users ask natural-language questions through a conversational AI interface. Every answer is grounded in retrieved document chunks, includes verifiable source attributions (document name, document ID, page number, chunk index, cosine similarity score, and verbatim passage), and explicitly states when requested information cannot be found in the uploaded documents.

## 1. Project Choice & Overview

- **Selected Track**: Project A — **PolicyDesk: RAG Document Assistant**
- **Core Objective**: Provide grounded, source-attributed policy Q&A with strict role-based access control (`admin` vs. `user`), persistent vector embeddings in PostgreSQL ([pgvector](https://github.com/pgvector/pgvector)), and a modern SaaS user interface built with [React](https://react.dev), [TypeScript](https://www.typescriptlang.org), and [Tailwind CSS](https://tailwindcss.com).

## 2. Main Features

### Mandatory Features Implemented
- **Role-Based Access Control (RBAC)**:
  - **Administrators (`admin`)**: Log in, view the Admin Control Center dashboard (total documents, processed documents, failed documents, indexed vector chunks, total users, recent uploads), upload `.pdf` and `.txt` documents via drag-and-drop, inspect extracted chunks, delete documents (with cascading chunk and embedding cleanup), and manage registered user roles and active status.
  - **Normal Users (`user`)**: Self-register (strictly assigned the `user` role with backend privilege-escalation guards), log in, browse active policy summaries on the User Dashboard, ask questions in the AI Policy Assistant, inspect expandable verbatim source passages with page numbers, and manage personal conversation history.
- **End-to-End RAG Ingestion & Retrieval Pipeline**:
  - Multi-page PDF extraction via [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`, with automatic fallback to `pypdf`) preserving exact page numbers, plus UTF-8/Latin-1 `.txt` extraction.
  - Structural whitespace normalization and configurable paragraph/sentence-aware overlapping chunking (`CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`).
  - Semantic embedding generation (`768` dimensions) using the [Google GenAI Python SDK](https://github.com/googleapis/python-genai) (`google-genai`) and the [`gemini-embedding-001`](https://aistudio.google.com/api-reference/embeddings/embed-content) model.
  - Cosine similarity vector search powered by [pgvector for Python & SQLAlchemy](https://github.com/pgvector/pgvector-python) (`<=>` cosine distance with HNSW indexing on PostgreSQL) and configurable threshold filtering (`SIMILARITY_THRESHOLD=0.35`) so unrelated chunks are never returned just to fill `top_k`.
  - Grounded answer synthesis via [`gemini-3.8-flash`](https://aistudio.google.com/docs/migrate) governed by a strict system prompt that forbids outside knowledge or fabricated citations.

### Bonus Features Implemented
1. **Persistent Multi-Turn Chat History**: Full conversation and message persistence with per-user ownership isolation.
2. **Expandable Verbatim Source Passages**: Interactive citation cards displaying exact chunk text, document ID, page number, chunk index, and cosine match percentage.
3. **Automated Executive Document Summarization**: Generates a concise 2–3 sentence summary of each policy document upon ingestion.
4. **Helpful / Not Helpful Answer Feedback**: Users can rate assistant responses (`PATCH /api/chat/messages/{message_id}/feedback`), persisted on the `messages` table.
5. **Real-Time Processing Status & Chunk Inspector**: Visual status badges (`processing`, `processed`, `failed`) and an admin modal to inspect individual chunks and page boundaries.
6. **Knowledge Scope Filtering**: Users can filter RAG retrieval to specific policy documents directly inside the chat sidebar.

## 3. Architecture Overview

```
+-----------------------------------------------------------------------------------+
|                        FRONTEND (Vercel — React + Vite + TS)                      |
|  +-----------------+  +--------------------+  +----------------+  +------------+  |
|  | Auth & RBAC     |  | Admin Control Ctr  |  | User Dashboard |  | RAG Chat & |  |
|  | (Login/Register)|  | (Upload/Docs/Users)|  | & Doc Browser  |  | Citations  |  |
|  +--------+--------+  +---------+----------+  +-------+--------+  +-----+------+  |
+-----------|---------------------|---------------------|-----------------|---------+
            | HTTPS + Bearer JWT  | Multipart Upload    | REST JSON       |
            v                     v                     v                 v
+-----------------------------------------------------------------------------------+
|                      BACKEND API (Render — FastAPI + Pydantic)                    |
|  +-----------------------------------------------------------------------------+  |
|  | Security Layer: JWT Verification (HTTP 401) & Role Guards (HTTP 403)        |  |
|  +-----------------------------------------------------------------------------+  |
|  | Services Layer:                                                             |  |
|  |  - AuthService (Argon2 / Bcrypt / Scrypt KDF + JWT HS256)                   |  |
|  |  - DocumentService (Validation -> PyMuPDF Extraction -> Overlapping Chunks) |  |
|  |  - EmbeddingService (google-genai SDK -> gemini-embedding-001 [768-dim])    |  |
|  |  - RetrievalService (pgvector Cosine Distance <=> + Similarity Threshold)   |  |
|  |  - RAGService (Strict System Prompt -> gemini-3.8-flash + Source Grounding) |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------|-----------------------------------------+
                                          | SQLAlchemy 2.0 ORM + Alembic Migrations
                                          v
+-----------------------------------------------------------------------------------+
|                DATABASE (Neon Serverless PostgreSQL + pgvector)                   |
|  [users] 1---* [documents] 1---*(CASCADE)*--- [document_chunks (vector(768))]     |
|  [users] 1---*(CASCADE)*--- [conversations] 1---*(CASCADE)*--- [messages]         |
+-----------------------------------------------------------------------------------+
```

## 4. Technology Stack & Architectural Rationale

| Layer | Technology | Selection Rationale & Documentation |
| :--- | :--- | :--- |
| **Frontend UI** | [React 18](https://react.dev) + [TypeScript](https://www.typescriptlang.org) + [Vite](https://intlayer.org/doc/environment/vite-and-react) + [Tailwind CSS](https://tailwindcss.com) | Component-based SPA architecture with strict static typing for API payloads, fast ES module bundling, and utility-first enterprise styling. |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) + [Pydantic](https://docs.pydantic.dev/) | High-throughput ASGI routing, automatic OpenAPI (`/docs`) schema generation, and strict request/response validation (`extra="forbid"` on registration). |
| **ORM & Migrations** | [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/core/metadata.html) + Alembic | Normalized relational mapping with declarative foreign keys, cascading deletes, and repeatable schema migrations. |
| **Database & Vector Store** | [Neon PostgreSQL](https://neon.com/faqs/best-backend-python-django-fastapi) + [pgvector](https://github.com/pgvector/pgvector) | Stores relational metadata (`users`, `documents`, `conversations`) and `768`-dimensional embeddings in a single ACID-compliant database using HNSW cosine indexes. |
| **AI & Embeddings** | [Google GenAI SDK (`google-genai`)](https://github.com/googleapis/python-genai) | Official unified SDK supporting [`gemini-3.8-flash`](https://aistudio.google.com/docs/migrate) for low-latency grounded generation and [`gemini-embedding-001`](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/embeddings/get-text-embeddings) for semantic vectors. |
| **Document Parsing** | [PyMuPDF (`fitz`)](https://pymupdf.readthedocs.io/) | High-speed native PDF text extraction with exact 1-indexed page attribution (`page.get_text("text")`). |
| **Authentication** | [JWT + Argon2 / Bcrypt](https://neon.com/guides/fastapi-jwt) | Stateless RFC 7519 HS256 bearer tokens paired with salted memory-hard password hashing and per-route RBAC dependencies. |

## 5. RAG Pipeline Explanation

1. **Ingestion & Validation (`DocumentService.ingest_document`)**:
   - Validates file extension (`.pdf` or `.txt` only) and enforces `MAX_UPLOAD_SIZE_MB` (default `20 MB`). Rejects 0-byte, binary-masquerading, encrypted, or corrupted files with `HTTP 400` or `HTTP 422`.
   - Extracts text page-by-page using [PyMuPDF](https://pymupdf.readthedocs.io/) so every chunk retains its exact `page_number`.
   - Applies `clean_extracted_text()` to strip null bytes and collapse horizontal whitespace while preserving double-newline paragraph breaks.
   - Splits text into overlapping chunks (`CHUNK_SIZE=1000` characters, `CHUNK_OVERLAP=200` characters), snapping to natural paragraph or sentence boundaries when possible.
   - Generates `768`-dimensional normalized embeddings via [`gemini-embedding-001`](https://aistudio.google.com/api-reference/embeddings/embed-content) (`task_type="RETRIEVAL_DOCUMENT"`) and persists all chunks and metadata directly in PostgreSQL—avoiding ephemeral local disk storage on Render.
2. **Vector Similarity Retrieval (`RetrievalService.retrieve_relevant_chunks`)**:
   - Embeds the user's question using the identical [`gemini-embedding-001`](https://aistudio.google.com/api-reference/embeddings/embed-content) model (`task_type="RETRIEVAL_QUERY"`).
   - Computes cosine similarity (`1 - cosine_distance`) across chunks belonging to `processed` documents using [pgvector](https://github.com/pgvector/pgvector-python).
   - Filters results by `SIMILARITY_THRESHOLD=0.35`. Chunks scoring below the threshold are discarded so unrelated passages are never passed to the LLM.
3. **Grounded Answer Generation (`RAGService.answer_question`)**:
   - If zero chunks meet the similarity threshold, immediately returns the honest fallback message with an empty `sources: []` array.
   - Otherwise, formats the retrieved chunks with their document names, IDs, and page numbers into the prompt context and invokes [`gemini-3.8-flash`](https://aistudio.google.com/docs/migrate) at `temperature=0.1`.
   - Attaches the exact `SourceAttribution` objects from the retrieved database chunks so frontend citations are 100% verifiable.

## 6. Authentication & Role-Based Access Control (RBAC)

- **Password Security**: Passwords are hashed before storage using Argon2id (`argon2-cffi`), `bcrypt`, or RFC 7914 `hashlib.scrypt` with cryptographic salts and verified via constant-time comparison (`hmac.compare_digest`).
- **Privilege Escalation Prevention**:
  - `RegisterRequest` uses `extra = "forbid"` and omits `role`. Any request attempting to pass `{"role": "admin"}` during registration is rejected with `HTTP 422`, and `AuthService.register_user` hardcodes `role="user"`.
  - Every protected endpoint resolves the user record from the database via `get_current_user` (`HTTP 401` if missing/invalid/expired JWT) and checks `require_admin` (`HTTP 403` if `current_user.role != "admin"`).
  - Conversation endpoints (`GET` / `POST` / `DELETE /api/chat/conversations/{id}`) verify `conversation.user_id == current_user.id`, returning `HTTP 403` on cross-user access attempts.

## 7. Normalized Database Schema

| Table | Primary Key | Foreign Keys & Cascade Behavior | Key Columns & Indexes |
| :--- | :--- | :--- | :--- |
| **`users`** | `id` (PK) | — | `name`, `email` (`UNIQUE`, indexed), `hashed_password`, `role` (indexed), `is_active`, `created_at` |
| **`documents`** | `id` (PK) | `uploaded_by -> users.id (ON DELETE SET NULL)` | `filename` (indexed), `file_type`, `file_size`, `page_count`, `chunk_count`, `summary`, `error_message`, `upload_timestamp`, `processing_status` (indexed) |
| **`document_chunks`** | `id` (PK) | `document_id -> documents.id (ON DELETE CASCADE)` | `chunk_text`, `embedding` (`Vector(768)` + HNSW `vector_cosine_ops` index), `page_number`, `chunk_index`, `chunk_metadata` (`JSON`) |
| **`conversations`** | `id` (PK) | `user_id -> users.id (ON DELETE CASCADE)` | `title`, `created_at`, `user_id` (indexed) |
| **`messages`** | `id` (PK) | `conversation_id -> conversations.id (ON DELETE CASCADE)` | `role` (`user`/`assistant`), `content`, `sources` (`JSON`), `feedback`, `created_at` |

## 8. REST API Endpoint Documentation

Interactive Swagger documentation is served automatically at `/docs` and OpenAPI JSON at `/openapi.json`.

| Method & Endpoint | Access Role | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET /health` | Public | Database connectivity, `pgvector` status, and active Gemini model config | `200` |
| `POST /api/auth/register` | Public | Register a new normal user (`role="user"`) and return JWT | `201`, `400`, `422` |
| `POST /api/auth/login` | Public | Authenticate email/password and return Bearer JWT token | `200`, `401`, `403` |
| `GET /api/auth/me` | Authenticated | Return current authenticated user's profile and verified role | `200`, `401` |
| `GET /api/admin/stats` | Admin Only | Return Admin Dashboard KPIs and recent document uploads | `200`, `401`, `403` |
| `POST /api/admin/documents/upload` | Admin Only | Upload `.pdf` or `.txt`, extract text, chunk, embed, and persist | `201`, `400`, `401`, `403`, `413`, `422` |
| `GET /api/admin/documents` | Admin Only | List all documents (including `processing` and `failed`) | `200`, `401`, `403` |
| `GET /api/admin/documents/{id}` | Admin Only | Inspect document metadata and all extracted text chunks | `200`, `401`, `403`, `404` |
| `DELETE /api/admin/documents/{id}` | Admin Only | Delete document and cascade-delete all associated chunks & embeddings | `200`, `401`, `403`, `404` |
| `GET /api/admin/users` | Admin Only | List all registered user accounts | `200`, `401`, `403` |
| `PATCH /api/admin/users/{id}` | Admin Only | Promote/demote user role or activate/deactivate account | `200`, `400`, `401`, `403`, `404` |
| `GET /api/documents` | Authenticated | List all `processed` documents available for Q&A | `200`, `401` |
| `GET /api/documents/{id}` | Authenticated | View processed document details and chunk previews | `200`, `401`, `404` |
| `POST /api/chat/ask` | Authenticated | Execute RAG retrieval + Gemini generation and return cited answer | `200`, `401`, `403`, `422` |
| `GET /api/chat/conversations` | Authenticated | List conversations belonging to the current user | `200`, `401` |
| `GET /api/chat/conversations/{id}` | Authenticated | Retrieve full message history and citations for a conversation | `200`, `401`, `403`, `404` |
| `DELETE /api/chat/conversations/{id}` | Authenticated | Delete a conversation owned by the current user | `200`, `401`, `403`, `404` |
| `PATCH /api/chat/messages/{id}/feedback` | Authenticated | Record `helpful` or `not_helpful` feedback on an AI response | `200`, `401`, `403`, `404` |

## 9. Local Installation & Execution Instructions

### Prerequisites
- Python `3.11+`
- Node.js `18+` and `npm`
- PostgreSQL `15+` with `pgvector` (or [Neon Serverless PostgreSQL](https://neon.com/guides/fastapi-jwt); SQLite is also supported out-of-the-box for rapid local testing)

### Step 1: Backend Setup, Migrations & Admin Seeding
```bash
cd PolicyDesk/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy environment template and configure your GEMINI_API_KEY and DATABASE_URL
cp .env.example .env

# Run Alembic migrations (when connected to PostgreSQL / Neon)
alembic upgrade head

# Seed initial Admin account, Demo User account, and sample policy documents
INITIAL_ADMIN_PASSWORD="<your-secure-admin-password>" \
INITIAL_USER_PASSWORD="<your-secure-user-password>" \
SEED_SAMPLE_DOCS="true" \
python3 -m app.seed

# Start FastAPI server (Swagger UI at http://localhost:8000/docs)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Frontend Setup & Local Dev Server
```bash
cd PolicyDesk/frontend
cp .env.example .env
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

## 10. Environment Variables Reference

### Backend (`backend/.env`)
| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | Neon PostgreSQL connection string (`postgresql+psycopg2://...`) | `sqlite:///./policydesk.db` (local fallback) |
| `GEMINI_API_KEY` | Google AI Studio API key for Gemini LLM & Embeddings | Required for live Gemini calls |
| `GEMINI_LLM_MODEL` | Configurable Gemini generation model | `gemini-3.8-flash` |
| `GEMINI_EMBEDDING_MODEL` | Configurable Gemini embedding model | `gemini-embedding-001` |
| `GEMINI_EMBEDDING_DIMENSIONS` | Vector embedding dimensionality | `768` |
| `JWT_SECRET_KEY` | 64-byte cryptographic secret for signing HS256 JWTs | Required in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token validity window in minutes | `480` (8 hours) |
| `INITIAL_ADMIN_EMAIL` | Email used by `python -m app.seed` | `admin@policydesk.io` |
| `INITIAL_ADMIN_PASSWORD` | Password read by `python -m app.seed` (never hardcoded) | Set via environment variable |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Character chunk size and overlap window | `1000` / `200` |
| `RETRIEVAL_TOP_K` | Maximum chunks retrieved per query | `5` |
| `SIMILARITY_THRESHOLD` | Minimum cosine similarity (`0.0–1.0`) required to include a chunk | `0.35` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `http://localhost:5173,https://policydesk-inky.vercel.app` |

### Frontend (`frontend/.env`)
| Variable | Description | Example |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base URL of the FastAPI backend | `http://localhost:8000` or `https://policydesk-backend.onrender.com` |

## 11. Demo Credentials (Seeded via Environment Variables)

The seed script creates the following demo accounts when the corresponding environment variables are configured:
- **Administrator Account**:
  - **Email**: `admin@policydesk.io`
  - **Password**: Configured through the corresponding environment variable. Not published in this repository.
- **Normal User Account**:
  - **Email**: `user@policydesk.io`
 - **Password**: Configured through the corresponding environment variable. Not published in this repository.

## 12. Automated Testing Instructions

Run the complete automated test suite covering Authentication, Document Ingestion (PDF/TXT/Invalid/Empty/Cascading Delete), RAG Retrieval & Grounding, Honest Fallback on Unknown Questions, and RBAC Security:

```bash
cd PolicyDesk/backend
python -m pytest -q
```

## 13. Live Deployment

PolicyDesk is deployed using the following cloud services:

| Component | Platform | URL |
|---|---|---|
| Frontend | Vercel | https://policydesk-inky.vercel.app |
| Backend API | Render | https://policydesk-backend-5cye.onrender.com |
| API Documentation | FastAPI Swagger UI | https://policydesk-backend-5cye.onrender.com/docs |
| Database | Neon PostgreSQL | Hosted PostgreSQL with pgvector |

### Production Configuration

- **Frontend:** React, TypeScript and Vite, deployed on Vercel.
- **Backend:** FastAPI application deployed as a Render Web Service.
- **Database:** Neon PostgreSQL with the pgvector extension for persistent vector storage.
- **AI Services:** Google Gemini for document embeddings and grounded answer generation.
- **Authentication:** JWT-based authentication with backend-enforced role-based access control.

### Deployment Verification

The production application has been tested for:
- User and administrator authentication.
- Role-based access restrictions.
- PDF and TXT document ingestion.
- Persistent document chunks and vector embeddings.
- Grounded question answering with source citations.
- Honest fallback responses when relevant information is unavailable.

The backend health endpoint is available at `/health`, and interactive API documentation is available at `/docs`.

## 14. Known Limitations & Future Improvements

- **OCR for Scanned Image-Only PDFs:** The current PDF extraction pipeline uses PyMuPDF to extract embedded text. Scanned PDFs without a text layer are rejected rather than silently indexed with empty content. Future versions could integrate OCR for scanned documents.
- **Synchronous Document Ingestion:** Document extraction, chunking, and embedding generation run during the upload request. A background worker system could improve responsiveness for large documents and higher upload volumes.
- **LLM API Quotas:** Gemini API usage is subject to the configured account's rate limits and quotas. Temporary quota exhaustion can affect answer generation. The application includes a grounded fallback mechanism when generation is unavailable.