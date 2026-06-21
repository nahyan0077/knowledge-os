"""Unit tests for _normalize_citation_brackets."""
import pytest
from knowledge_os.application.conversations import ConversationService

normalize = ConversationService._normalize_citation_brackets

def test_source_single():
    assert normalize("[Source 1]") == "[1]"

def test_source_lowercase():
    assert normalize("[source 2]") == "[2]"

def test_source_multi():
    result = normalize("[Source 2, 5]")
    assert result == "[2] [5]"

def test_comma_list():
    result = normalize("[5, 6]")
    assert result == "[5] [6]"

def test_three_in_brackets():
    result = normalize("[1, 2, 3]")
    assert result == "[1] [2] [3]"

def test_plain_single_unchanged():
    assert normalize("[1]") == "[1]"

def test_mixed_text():
    text = "Date of birth is 08/06/1978 [5, 6]."
    result = normalize(text)
    assert "[5]" in result
    assert "[6]" in result
    assert "[5, 6]" not in result

def test_source_in_sentence():
    text = "The member details are [Source 2, 5] and [Source 3]."
    result = normalize(text)
    assert "[Source" not in result
    assert "[2]" in result
    assert "[5]" in result
    assert "[3]" in result

def test_no_brackets():
    text = "No citations here."
    assert normalize(text) == text
