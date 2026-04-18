import unittest
from unittest.mock import Mock, patch


class TestAgentRuntimeCreation(unittest.TestCase):
    @patch("myopenclaw.core.runtime.get_provider")
    @patch("myopenclaw.core.runtime.load_dynamic_skills")
    @patch("myopenclaw.core.runtime.BUILTIN_TOOLS", [])
    def test_create_agent_app(self, mock_load_skills, mock_get_provider):
        from myopenclaw.core.agent import create_agent_app

        mock_provider = Mock()
        mock_provider.bind_tools.return_value = Mock()
        mock_get_provider.return_value = mock_provider
        mock_load_skills.return_value = []

        app = create_agent_app(provider_name="openai", model_name="gpt-4o-mini")
        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()
