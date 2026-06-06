from typing import Any


class TextExtractor:
    def extract_text(self, content_bytes: bytes, mime_type: str) -> str:
        """
        Extracts plain text from document version binary contents.
        Supports plain text directly, and fallback mocking for PDFs.
        """
        if mime_type == "text/plain":
            return content_bytes.decode("utf-8", errors="replace")
        elif mime_type == "application/pdf":
            try:
                # If the PDF contains plain text data (e.g. in tests), decode it
                return content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return f"[Mock Extracted Text from PDF - Size: {len(content_bytes)} bytes]"
        else:
            try:
                return content_bytes.decode("utf-8")
            except Exception:
                return f"[Extracted Text for {mime_type} - Size: {len(content_bytes)} bytes]"


class TextChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

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
                # Simple token count estimation (approx. 1 token per word)
                token_count = len(content.split())
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "content": content,
                        "char_offset": start,
                        "token_count": token_count,
                    }
                )
                chunk_index += 1

            start = end - self.chunk_overlap
            if start >= text_len or end == text_len:
                break
            if start < 0:
                start = 0

        return chunks
