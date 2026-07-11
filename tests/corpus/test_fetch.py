"""Tests for Planalto byte-decoding (latin-1 vs UTF-16 BOM detection)."""

from direito_dados.corpus.fetch import decode_planalto


def test_decodes_latin1_without_bom():
    content = "Art. 1º Não há crime sem lei anterior; ação típica.".encode("latin-1")
    assert decode_planalto(content) == "Art. 1º Não há crime sem lei anterior; ação típica."


def test_decodes_utf16_le_with_bom():
    # Lei Maria da Penha and other FrontPage pages are served as UTF-16LE.
    text = "Art. 1º Cria mecanismos."
    content = b"\xff\xfe" + text.encode("utf-16-le")
    assert decode_planalto(content) == text


def test_decodes_utf16_be_with_bom():
    text = "Art. 2º Toda mulher."
    content = b"\xfe\xff" + text.encode("utf-16-be")
    assert decode_planalto(content) == text


def test_decodes_utf8_with_bom():
    text = "Art. 3º Proteção."
    content = text.encode("utf-8-sig")
    assert decode_planalto(content) == text
