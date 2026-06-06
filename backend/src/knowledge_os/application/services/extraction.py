import io
import logging
from dataclasses import dataclass
from typing import Any

import pypdf
import tiktoken


@dataclass(slots=True)
class ExtractionResult:
    text: str
    page_count: int | None
    extracted_characters: int


class PdfTextExtractor:
    def extract(self, content_bytes: bytes) -> ExtractionResult:
        """
        Extracts plain text page-by-page from a binary PDF.
        Preserves page ordering and handles empty pages and malformed PDFs gracefully.
        """
        try:
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            pages_text = []
            page_count = len(reader.pages)
            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)
                    else:
                        pages_text.append("")
                except Exception as e:
                    # Handle page extraction errors gracefully
                    logging.getLogger(__name__).warning(f"Failed to extract page: {e}")
                    pages_text.append("")

            full_text = "\n".join(pages_text)
            return ExtractionResult(
                text=full_text,
                page_count=page_count,
                extracted_characters=len(full_text),
            )
        except Exception as e:
            logging.getLogger(__name__).warning(f"Malformed PDF extraction failure: {e}")
            return ExtractionResult(
                text="",
                page_count=0,
                extracted_characters=0,
            )


class TextExtractor:
    def extract_text(self, content_bytes: bytes, mime_type: str) -> str:
        """
        Extracts plain text from document version binary contents.
        Delegates to PdfTextExtractor for PDFs.
        """
        result = self.extract_text_with_metadata(content_bytes, mime_type)
        return result.text

    def extract_text_with_metadata(self, content_bytes: bytes, mime_type: str) -> ExtractionResult:
        """
        Extracts plain text and records metadata like page counts and character counts.
        """
        if mime_type == "application/pdf":
            return PdfTextExtractor().extract(content_bytes)

        if mime_type == "text/plain":
            try:
                text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = content_bytes.decode("utf-8", errors="replace")
        else:
            try:
                text = content_bytes.decode("utf-8")
            except Exception:
                text = f"[Extracted Text for {mime_type} - Size: {len(content_bytes)} bytes]"

        return ExtractionResult(
            text=text,
            page_count=None,
            extracted_characters=len(text),
        )


class TokenCounter:
    def __init__(self, model_name: str = "text-embedding-3-small") -> None:
        self.model_name = model_name
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base if model not recognized directly by tiktoken
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self.encoding.encode(text))


class TextChunker:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        model_name: str = "text-embedding-3-small",
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.token_counter = TokenCounter(model_name)

    def chunk_text(self, text: str) -> list[dict[str, Any]]:
        """
        Splits text into chunks of chunk_size characters with chunk_overlap overlap,
        aligning splits with word boundaries when possible.
        """
        if not text:
            return []

        chunks = []
        text_len = len(text)
        start = 0
        chunk_index = 0

        while start < text_len:
            end = min(start + self.chunk_size, text_len)

            # Avoid cutting words in half if not at the absolute end of the text
            if end < text_len:
                last_space = text.rfind(" ", max(start, end - 50), end)
                if last_space != -1:
                    end = last_space

            content = text[start:end].strip()
            if content:
                token_count = self.token_counter.count_tokens(content)
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "content": content,
                        "char_offset": start,
                        "token_count": token_count,
                        "char_count": len(content),
                    }
                )
                chunk_index += 1

            start = end - self.chunk_overlap
            if start >= text_len or end == text_len:
                break
            if start < 0:
                start = 0

        return chunks
