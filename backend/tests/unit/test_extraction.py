from typing import Any
from unittest.mock import MagicMock

import pytest
from pypdf.errors import PdfReadError

from knowledge_os.application.services.extraction import (
    PdfTextExtractor,
    TextChunker,
    TextExtractor,
    TokenCounter,
)


def test_token_counter_basic() -> None:
    counter = TokenCounter(model_name="text-embedding-3-small")
    assert counter.count_tokens("") == 0
    assert counter.count_tokens(None) == 0

    text = "Hello world! This is a simple test."
    tokens = counter.count_tokens(text)
    assert tokens > 0
    # "Hello world! This is a simple test." in cl100k_base is 9 tokens:
    # ['Hello', ' world', '!', ' This', ' is', ' a', ' simple', ' test', '.']
    assert tokens == 9


def test_token_counter_configurable() -> None:
    counter_default = TokenCounter()
    counter_gpt4 = TokenCounter(model_name="gpt-4")

    text = "Tiktoken tokenization check."
    assert counter_default.count_tokens(text) == counter_gpt4.count_tokens(text)


def test_pdf_extractor_success(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_reader = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 Content"
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Page 2 Content"
    mock_reader.pages = [mock_page1, mock_page2]

    monkeypatch.setattr("pypdf.PdfReader", lambda stream: mock_reader)

    extractor = PdfTextExtractor()
    result = extractor.extract(b"dummy pdf bytes")

    assert result.page_count == 2
    assert result.text == "Page 1 Content\nPage 2 Content"
    assert result.extracted_characters == len(result.text)


def test_pdf_extractor_empty_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_reader = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 Content"
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = None
    mock_page3 = MagicMock()
    mock_page3.extract_text.return_value = ""
    mock_reader.pages = [mock_page1, mock_page2, mock_page3]

    monkeypatch.setattr("pypdf.PdfReader", lambda stream: mock_reader)

    extractor = PdfTextExtractor()
    result = extractor.extract(b"dummy pdf bytes")

    assert result.page_count == 3
    assert result.text == "Page 1 Content\n\n"
    assert result.extracted_characters == len(result.text)


def test_pdf_extractor_malformed_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_read_error(stream: Any) -> None:
        raise PdfReadError("File is not a PDF")

    monkeypatch.setattr("pypdf.PdfReader", raise_read_error)

    extractor = PdfTextExtractor()
    result = extractor.extract(b"malformed binary bytes")

    assert result.page_count == 0
    assert result.text == ""
    assert result.extracted_characters == 0


def test_pdf_extractor_with_real_empty_pdf() -> None:
    import io

    import pypdf

    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_blank_page(width=100, height=100)

    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    extractor = PdfTextExtractor()
    result = extractor.extract(pdf_bytes)

    assert result.page_count == 2
    assert result.text == "\n"
    assert result.extracted_characters == 1


def test_text_extractor_delegation(monkeypatch: pytest.MonkeyPatch) -> None:
    extractor = TextExtractor()

    # Plain text
    result_txt = extractor.extract_text_with_metadata(b"Plain text file", "text/plain")
    assert result_txt.page_count is None
    assert result_txt.text == "Plain text file"
    assert result_txt.extracted_characters == 15

    # PDF delegation
    mock_pdf_result = MagicMock()
    mock_pdf_result.text = "Mock PDF Content"
    mock_pdf_result.page_count = 5
    mock_pdf_result.extracted_characters = 16

    monkeypatch.setattr(PdfTextExtractor, "extract", lambda self, data: mock_pdf_result)

    result_pdf = extractor.extract_text_with_metadata(b"dummy bytes", "application/pdf")
    assert result_pdf.page_count == 5
    assert result_pdf.text == "Mock PDF Content"
    assert result_pdf.extracted_characters == 16


def test_text_chunker_metadata() -> None:
    chunker = TextChunker(chunk_size=20, chunk_overlap=5)
    text = "Hello world! This is a longer string that will be chunked."

    chunks = chunker.chunk_text(text)
    assert len(chunks) > 0
    for chunk in chunks:
        assert "token_count" in chunk
        assert "char_count" in chunk
        assert chunk["char_count"] == len(chunk["content"])
        assert chunk["token_count"] > 0
