import unittest
from writer_app.utils.ai_client import AIClient

class TestAIClient(unittest.TestCase):
    def test_extract_json_simple(self):
        text = '{"key": "value"}'
        result = AIClient.extract_json_from_text(text)
        self.assertEqual(result, {"key": "value"})

    def test_extract_json_markdown(self):
        text = 'Here is the json:\n```json\n{"key": "value"}\n```'
        result = AIClient.extract_json_from_text(text)
        self.assertEqual(result, {"key": "value"})

    def test_extract_json_trailing_comma(self):
        text = '{"key": "value",}'
        result = AIClient.extract_json_from_text(text)
        self.assertEqual(result, {"key": "value"})

    def test_extract_json_trailing_comma_list(self):
        text = '{"list": [1, 2,]}'
        result = AIClient.extract_json_from_text(text)
        self.assertEqual(result, {"list": [1, 2]})

    def test_extract_json_conversational(self):
        text = 'Sure, here is the data: {"key": "value"} Hope this helps.'
        result = AIClient.extract_json_from_text(text)
        self.assertEqual(result, {"key": "value"})

    def test_extract_json_markdown_no_lang(self):
        text = '```\n{"key": "value"}\n```'
        result = AIClient.extract_json_from_text(text)
        self.assertEqual(result, {"key": "value"})

