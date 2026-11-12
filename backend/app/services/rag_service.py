"""
Retrieval-Augmented Generation (RAG) Service powered by Google Gemini.
Strictly enforces source-grounded answering, explicit unknown-question fallbacks,
and verifiable citation attribution from retrieved document chunks.
"""
import logging
import re
from typing import List, Optional, Tuple

import httpx
from app.config import settings
from app.database import Session
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.chat import (
    AskQuestionRequest,
    AskQuestionResponse,
    RetrievalMetadata,
    SourceAttribution,
)
from app.services.embedding_service import STOP_WORDS, _normalize_stem
from app.services.retrieval_service import RetrievedChunkResult, retrieval_service

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types

    HAS_GOOGLE_GENAI = True
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]
    HAS_GOOGLE_GENAI = False

FALLBACK_NOT_FOUND_MESSAGE = (
    "I could not find information to answer this question in the uploaded policy documents. "
    "Please verify that the relevant policy document has been uploaded and processed, or rephrase your question."
)


RAG_SYSTEM_PROMPT = """You are PolicyDesk AI, an enterprise policy and document assistant.

Follow these rules strictly:

1. Answer only using facts explicitly supported by the retrieved document context.
2. Answer the exact question asked. Do not include related policies, benefits, rules, or background information unless necessary to answer the question.
3. Prefer the smallest amount of evidence needed to answer accurately.
4. Preserve important conditions, eligibility requirements, limits, exceptions, and units.
5. Never invent facts, figures, dates, policies, or citations.
6. If the context does not contain sufficient evidence, respond exactly:
   "I could not find information to answer this question in the uploaded policy documents."
7. Keep answers concise. For a straightforward factual question, use one or two sentences.
8. Cite the source document and page number for every factual answer, using only names and page numbers provided in the retrieved context.
9. Do not cite a document merely because it was retrieved. Its passage must directly support the claim.
10. Do not combine unrelated facts into a single answer.
11. If multiple conditions are necessary to answer correctly, include all of them.
12. Never use external knowledge or assumptions to fill gaps."""


class RAGService:
    """Orchestrates retrieval, prompt construction, Gemini LLM generation, and conversation persistence."""

    def __init__(self) -> None:
        self.llm_model = settings.GEMINI_LLM_MODEL
        self.api_key = settings.GEMINI_API_KEY
        self.temperature = settings.GEMINI_TEMPERATURE

    def _is_live_api_configured(self) -> bool:
        return bool(
            self.api_key
            and not self.api_key.startswith("replace_with_")
            and self.api_key != "mock"
        )

    def answer_question(
        self,
        db: Session,
        user: User,
        payload: AskQuestionRequest,
    ) -> AskQuestionResponse:
        """
        Execute the full RAG pipeline for a user question:
        1. Resolve or create Conversation owned by `user`.
        2. Save the user's question Message.
        3. Retrieve relevant chunks above `settings.SIMILARITY_THRESHOLD`.
        4. Generate grounded answer (or explicit fallback if no relevant context is found).
        5. Persist assistant Message with actual retrieved source citations.
        """
        conversation = self._get_or_create_conversation(
            db=db,
            user=user,
            conversation_id=payload.conversation_id,
            question=payload.question,
        )

        # Persist user message
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=payload.question,
            sources=[],
        )
        db.add(user_msg)
        db.commit()

        # Perform vector retrieval
        retrieved_chunks, total_evaluated, top_score = (
            retrieval_service.retrieve_relevant_chunks(
                db=db,
                question=payload.question,
                top_k=settings.RETRIEVAL_TOP_K,
                similarity_threshold=settings.SIMILARITY_THRESHOLD,
                document_ids=payload.document_ids,
            )
        )

                # Reject retrieved chunks that do not discuss the question's key terms.
        query_terms = {
            _normalize_stem(w)
            for w in re.findall(r"[a-zA-Z0-9]{2,}", payload.question.lower())
            if w not in STOP_WORDS
            and _normalize_stem(w) not in STOP_WORDS
            and w not in {"company", "employees", "employee", "providing", "provide"}
        }

        if query_terms:
            relevant_chunks = []

            for chunk in retrieved_chunks:
                passage_terms = {
                    _normalize_stem(w)
                    for w in re.findall(
                        r"[a-zA-Z0-9]{2,}",
                        chunk.chunk_text.lower()
                    )
                }

                overlap = query_terms.intersection(passage_terms)

    
                if len(overlap) >= min(2, len(query_terms)):
                    relevant_chunks.append(chunk)

            retrieved_chunks = relevant_chunks

        if not retrieved_chunks:
            answer_text = FALLBACK_NOT_FOUND_MESSAGE
            sources: List[SourceAttribution] = []
            found_in_docs = False
        else:
            answer_text, is_answered = self._generate_grounded_answer(
                question=payload.question,
                chunks=retrieved_chunks,
            )
            if not is_answered:
                sources = []
                found_in_docs = False
            else:
                sources = []

                for c in retrieved_chunks:
                    # Include a source only if its passage supports
                    # at least one sentence in the generated answer.
                    passage_sentences = [
                        sentence.strip().lower()
                        for sentence in re.split(
                            r"(?<=[.!?])\s+|\n+",
                            c.chunk_text
                        )
                    ]

                    answer_sentences = [
                        sentence.strip().lower()
                        for sentence in re.split(
                            r"(?<=[.!?])\s+|\n+",
                            answer_text
                        )
                    ]

                    matched = any(
                        passage_sentence
                        and len(passage_sentence) > 15
                        and (
                            passage_sentence in answer_sentence
                            or answer_sentence in passage_sentence
                        )
                        for passage_sentence in passage_sentences
                        for answer_sentence in answer_sentences
                    )

                    if matched:
                        sources.append(
                            SourceAttribution(
                                chunk_id=c.chunk_id,
                                source_document_id=c.document_id,
                                source_document_name=c.document_name,
                                relevant_passage=c.chunk_text,
                                page_number=c.page_number,
                                chunk_index=c.chunk_index,
                                similarity_score=c.similarity_score,
                            )
                        )

                found_in_docs = bool(sources)

        serialized_sources = [s.dict() for s in sources]
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer_text,
            sources=serialized_sources,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        retrieval_meta = RetrievalMetadata(
            query_embedding_model=settings.GEMINI_EMBEDDING_MODEL,
            llm_model=self.llm_model,
            similarity_threshold=settings.SIMILARITY_THRESHOLD,
            top_k_requested=settings.RETRIEVAL_TOP_K,
            chunks_evaluated=total_evaluated,
            chunks_above_threshold=len(retrieved_chunks),
            top_similarity_score=top_score,
            found_in_documents=found_in_docs,
        )

        return AskQuestionResponse(
            answer=answer_text,
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            sources=sources,
            retrieval_metadata=retrieval_meta,
            created_at=assistant_msg.created_at,
        )

    def _get_or_create_conversation(
        self,
        db: Session,
        user: User,
        conversation_id: Optional[int],
        question: str,
    ) -> Conversation:
        if conversation_id is not None:
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv is None:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {conversation_id} not found.",
                )
            if conv.user_id != user.id:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this conversation.",
                )
            return conv

        title = question.strip()[:80]
        if len(question.strip()) > 80:
            title += "..."
        new_conv = Conversation(user_id=user.id, title=title)
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        return new_conv

    def _generate_grounded_answer(
        self,
        question: str,
        chunks: List[RetrievedChunkResult],
    ) -> Tuple[str, bool]:
        """
        Generate an answer strictly grounded in `chunks`.
        Calls Gemini (`gemini-2.5-flash`) when `GEMINI_API_KEY` is configured,
        or performs deterministic extractive synthesis over retrieved chunks.
        Returns `(answer_text, found_in_documents)`.
        """
        context_blocks = []
        for idx, c in enumerate(chunks, start=1):
            page_label = f"Page {c.page_number}" if c.page_number else "N/A"
            context_blocks.append(
                f"--- SOURCE CHUNK {idx} ---\n"
                f"Document Name: {c.document_name} (ID: {c.document_id})\n"
                f"Location: {page_label}, Chunk #{c.chunk_index}\n"
                f"Passage:\n{c.chunk_text}\n"
            )
        formatted_context = "\n".join(context_blocks)
        user_prompt = (
            f"RETRIEVED DOCUMENT CONTEXT:\n{formatted_context}\n\n"
            f"USER QUESTION:\n{question}\n\n"
            "Provide a concise, accurate answer based strictly on the retrieved document context above."
        )

        if self._is_live_api_configured():
            try:
                llm_text = self._call_gemini_llm(
                    system_instruction=RAG_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )
                if llm_text:
                    lowered = llm_text.lower()
                    if (
                        "could not find information" in lowered
                        or "cannot be found in the uploaded" in lowered
                        or "not mentioned in the uploaded" in lowered
                    ):
                        return llm_text.strip(), False
                    return llm_text.strip(), True
            except Exception as exc:
                logger.warning(
                    "Live Gemini LLM generation failed (%s); using extractive grounded synthesis.",
                    exc,
                )

        return self._extractive_grounded_synthesis(question, chunks)

    def _call_gemini_llm(self, system_instruction: str, user_prompt: str) -> str:
        """Invoke Google Gemini LLM (`gemini-2.5-flash`) via `google-genai` SDK or REST API."""
        if HAS_GOOGLE_GENAI and genai is not None and types is not None:
            client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=30000, retry_options=types.HttpRetryOptions(attempts=1)))
            response = client.models.generate_content(
                model=self.llm_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self.temperature,
                ),
            )
            return response.text or ""

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.llm_model}:generateContent?key={self.api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": self.temperature},
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)
        return ""

    @staticmethod
    
    
    @staticmethod
    def _extractive_grounded_synthesis(
        question: str, chunks: List[RetrievedChunkResult]
    ) -> Tuple[str, bool]:
        """
        Deterministic extractive fallback.
        Requires meaningful lexical overlap and cites selected passages.
        """
        q_words = {
            _normalize_stem(w)
            for w in re.findall(r"[a-zA-Z0-9]{2,}", question.lower())
            if w not in STOP_WORDS
            and _normalize_stem(w) not in STOP_WORDS
        }

        if not q_words:
            return FALLBACK_NOT_FOUND_MESSAGE, False

        scored_sentences = []

        for chunk in chunks:
            raw_sentences = re.split(
                r"(?<=[.!?])\s+|\n+",
                chunk.chunk_text
            )

            for sentence in raw_sentences:
                sentence = sentence.strip()
                # Ignore standalone section headings.
                if sentence.isupper() and any(c.isalpha() for c in sentence):
                    continue

                if len(sentence) < 15:
                    continue

                sentence_words = {
                    _normalize_stem(w)
                    for w in re.findall(
                        r"[a-zA-Z0-9]{2,}",
                        sentence.lower()
                    )
                }

                overlap_words = q_words.intersection(sentence_words)
                overlap_count = len(overlap_words)

                required_overlap = min(2, len(q_words))

                if overlap_count < required_overlap:
                    continue

                overlap_ratio = overlap_count / len(q_words)

                if overlap_ratio < 0.30:
                    continue

                score = (
                    overlap_count * 2.0
                    + overlap_ratio * 3.0
                    + chunk.similarity_score
                )

                # IMPORTANT: Store the matched sentence and its score.
                scored_sentences.append((score, sentence, chunk))

        if not scored_sentences:
            return FALLBACK_NOT_FOUND_MESSAGE, False

        scored_sentences.sort(
            key=lambda item: item[0],
            reverse=True
        )

        selected_lines = []
        seen_texts = set()

        for _, sentence, chunk in scored_sentences:
            normalized = sentence.lower()

            if normalized in seen_texts:
                continue

            seen_texts.add(normalized)

            page_tag = (
                f", Page {chunk.page_number}"
                if chunk.page_number
                else ""
            )

            selected_lines.append(
                f"- {sentence} "
                f"([Source: {chunk.document_name}{page_tag}])"
            )

            if len(selected_lines) >= 3:
                break

        if not selected_lines:
            return FALLBACK_NOT_FOUND_MESSAGE, False

        return (
            "Based on the relevant retrieved policy passages:\n\n"
            + "\n".join(selected_lines),
            True,
        )



    def generate_document_summary(self, filename: str, full_text: str) -> str:
        """
        Bonus feature: Generate a concise executive summary of an uploaded policy document.
        """
        preview_text = full_text[:6000].strip()
        if not preview_text:
            return "No summary available."

        if self._is_live_api_configured():
            try:
                summary_prompt = (
                    f"Summarize the core policy rules, scope, and key requirements of the following "
                    f"document ({filename}) in 2-3 concise sentences based strictly on its text:\n\n"
                    f"{preview_text}"
                )
                res = self._call_gemini_llm(
                    system_instruction="You summarize enterprise policy documents accurately and concisely without inventing facts.",
                    user_prompt=summary_prompt,
                )
                if res and res.strip():
                    return res.strip()
            except Exception as exc:
                logger.warning("Gemini summary generation fallback triggered: %s", exc)

        # Extractive summary from opening sentences
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+|\n\n+", preview_text)
            if len(s.strip()) > 25
        ]
        summary_sents = sentences[:3]
        if not summary_sents:
            return preview_text[:280]
        return " ".join(summary_sents)[:450]


rag_service = RAGService()
