import unittest
import numpy as np
import pandas as pd
from src.utils import clean_text, prepare_text

class TestUtils(unittest.TestCase):

    def test_clean_text_removes_urls_mentions_hashtags(self):
        raw_text = "Check this out http://example.com @user #awesome"
        cleaned = clean_text(raw_text)
        self.assertEqual(cleaned, "check this out")

    def test_clean_text_removes_punctuation_and_lowercases(self):
        raw_text = "Hello, WORLD!!! How's it going?"
        cleaned = clean_text(raw_text)
        self.assertEqual(cleaned, "hello world hows it going")

    def test_clean_text_strips_whitespace(self):
        raw_text = "    Text with spaces\t\n"
        cleaned = clean_text(raw_text)
        self.assertEqual(cleaned, "text with spaces")

    def test_prepare_text_with_mock_vectorizer(self):
        class DummyVectorizer:
            def fit_transform(self, data):
                class DummyMatrix:
                    def toarray(self):
                        return np.array([[len(s)] for s in data])
                return DummyMatrix()

        text_series = pd.Series(["hello", "world"])
        vec = DummyVectorizer()
        result = prepare_text(text_series, vec)
        expected = np.array([[5], [5]])
        np.testing.assert_array_equal(result, expected)

if __name__ == "__main__":
    unittest.main()