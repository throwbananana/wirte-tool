import unittest

from writer_app.ui.editor import (
    split_text_into_clause_offsets,
    split_text_into_paragraph_offsets,
    split_text_into_sentence_offsets,
)


class TestEditorFocusHelpers(unittest.TestCase):
    def test_split_text_into_sentence_offsets_keeps_sentence_boundaries(self):
        text = "第一句。 第二句！\n第三句？"
        spans = split_text_into_sentence_offsets(text)
        parts = [text[start:end] for start, end in spans]
        self.assertEqual(parts, ["第一句。", "第二句！", "第三句？"])

    def test_split_text_into_sentence_offsets_keeps_trailing_text_without_punctuation(self):
        text = "一句完整。还有半句"
        spans = split_text_into_sentence_offsets(text)
        parts = [text[start:end] for start, end in spans]
        self.assertEqual(parts, ["一句完整。", "还有半句"])

    def test_split_text_into_sentence_offsets_ignores_whitespace_only_segments(self):
        text = "  第一段。   \n\n  第二段。  "
        spans = split_text_into_sentence_offsets(text)
        parts = [text[start:end] for start, end in spans]
        self.assertEqual(parts, ["第一段。", "第二段。"])

    def test_split_text_into_clause_offsets_splits_on_commas_and_enumeration_commas(self):
        text = "第一句，第二句、第三句。"
        spans = split_text_into_clause_offsets(text)
        parts = [text[start:end] for start, end in spans]
        self.assertEqual(parts, ["第一句，", "第二句、", "第三句。"])

    def test_split_text_into_clause_offsets_keeps_trailing_clause_without_punctuation(self):
        text = "前半句，后半句"
        spans = split_text_into_clause_offsets(text)
        parts = [text[start:end] for start, end in spans]
        self.assertEqual(parts, ["前半句，", "后半句"])

    def test_split_text_into_paragraph_offsets_uses_blank_lines_as_separators(self):
        text = "第一段首行\n第二行\n\n第三段\n\n\n第四段"
        spans = split_text_into_paragraph_offsets(text)
        parts = [text[start:end] for start, end in spans]
        self.assertEqual(parts, ["第一段首行\n第二行", "第三段", "第四段"])

    def test_split_text_into_paragraph_offsets_keeps_indented_content(self):
        text = "    第一段\n  仍在第一段\n\n  第二段"
        spans = split_text_into_paragraph_offsets(text)
        parts = [text[start:end] for start, end in spans]
        self.assertEqual(parts, ["    第一段\n  仍在第一段", "  第二段"])


if __name__ == "__main__":
    unittest.main()
