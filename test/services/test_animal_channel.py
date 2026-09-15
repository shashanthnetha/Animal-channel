import unittest
from unittest.mock import MagicMock, patch

from app.services import animal_channel


class TestAnimalChannel(unittest.TestCase):
    def test_content_pillars_structure(self):
        pillars = animal_channel.CONTENT_PILLARS
        self.assertEqual(len(pillars), 10)
        for pillar in pillars:
            self.assertIn("id", pillar)
            self.assertIn("name", pillar)
            self.assertIn("description", pillar)
            self.assertTrue(len(pillar["examples"]) >= 3)

    def test_get_random_pillar(self):
        pillar = animal_channel.get_random_pillar()
        self.assertIn("id", pillar)
        self.assertIn("name", pillar)

    @patch("app.services.llm._generate_response")
    def test_generate_curiosity_topic_success(self, mock_generate):
        mock_generate.return_value = """
        {
            "subject": "Wood Frog Freeze Survival",
            "hook_angle": "How it stops its heart and freezes solid",
            "target_animal": "Alaskan Wood Frog",
            "short_title": "This Frog Can Freeze Solid 🐸"
        }
        """
        topic = animal_channel.generate_curiosity_topic(pillar_id="superpowers")
        self.assertEqual(topic["subject"], "Wood Frog Freeze Survival")
        self.assertIn("🐸", topic["short_title"])

    @patch("app.services.llm._generate_response")
    def test_generate_curiosity_topic_fallback(self, mock_generate):
        mock_generate.side_effect = RuntimeError("API error")
        topic = animal_channel.generate_curiosity_topic()
        self.assertIn("subject", topic)
        self.assertIn("short_title", topic)

    @patch("app.services.llm.generate_script")
    def test_generate_animal_script(self, mock_gen_script):
        mock_gen_script.return_value = "This frog can freeze solid in winter and wake up alive in spring."
        script = animal_channel.generate_animal_script("Wood Frog Freeze", "heart stops")
        self.assertIn("freeze solid", script)

    @patch("app.services.llm._generate_response")
    def test_extract_animal_visual_terms_llm(self, mock_generate):
        mock_generate.return_value = '["wood frog frozen macro", "ice thawing close up"]'
        terms = animal_channel.extract_animal_visual_terms("Some script", "Wood frog")
        self.assertEqual(terms, ["wood frog frozen macro", "ice thawing close up"])

    @patch("app.services.llm._generate_response")
    def test_generate_youtube_shorts_metadata(self, mock_generate):
        mock_generate.return_value = """
        {
            "title": "This Frog Freezes Solid! 🐸 #Shorts",
            "description": "Meet the Alaskan wood frog! #Shorts #Nature",
            "tags": ["wood frog", "nature", "shorts"],
            "hashtags": ["#Shorts", "#Animals", "#Nature"]
        }
        """
        metadata = animal_channel.generate_youtube_shorts_metadata("Wood Frog", "Script here")
        self.assertIn("#Shorts", metadata["title"])
        self.assertTrue(len(metadata["tags"]) > 0)
        self.assertIn("#Shorts", metadata["description"])


if __name__ == "__main__":
    unittest.main()
