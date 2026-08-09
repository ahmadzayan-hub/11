"""Unit tests for the Agent class."""

import unittest

from agent import Agent


def make_agent(**overrides):
    config = {
        "agent_name": "Test Agent",
        "preferences": {"tone": "concise"},
    }
    config.update(overrides)
    return Agent(config)


class TestAgentSetup(unittest.TestCase):
    def setUp(self):
        self.agent = make_agent()

    def test_agent_name_is_loaded(self):
        self.assertEqual(self.agent.name, "Test Agent")

    def test_default_name_when_missing(self):
        agent = Agent({})
        self.assertEqual(agent.name, "Agentic OS")

    def test_welcome_message_mentions_help(self):
        message = self.agent.get_welcome_message()
        self.assertIn("Test Agent", message)
        self.assertIn("/help", message)

    def test_configured_preferences_merge_with_defaults(self):
        self.assertEqual(self.agent.preferences["tone"], "concise")
        self.assertEqual(self.agent.preferences["language"], "English")

    def test_invalid_maximum_history_items_falls_back_to_default(self):
        agent = make_agent(maximum_history_items="many")
        self.assertEqual(agent.max_history_items, 50)


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.agent = make_agent()

    def test_help_command(self):
        response = self.agent.process_input("/help")
        self.assertIn("/exit", response)
        self.assertIn("/remember", response)

    def test_unknown_command(self):
        response = self.agent.process_input("/fly")
        self.assertIn("Unknown command", response)
        self.assertIn("/help", response)

    def test_empty_input(self):
        response = self.agent.process_input("   ")
        self.assertEqual(response, "Please enter a command or question.")
        self.assertEqual(self.agent.history, [])

    def test_non_string_input(self):
        response = self.agent.process_input(None)
        self.assertEqual(response, "Please enter a command or question.")

    def test_exit_command_is_recognized_by_the_agent(self):
        response = self.agent.process_input("/exit")
        self.assertEqual(response, "Session closed. Goodbye.")


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.agent = make_agent()

    def test_remember_command(self):
        response = self.agent.process_input("/remember My language is English")
        self.assertEqual(response, "Information saved.")
        self.assertIn("My language is English", self.agent.memory.values())

    def test_empty_memory_request(self):
        response = self.agent.process_input("/remember ")
        self.assertEqual(response, "Please provide information to remember.")
        self.assertEqual(self.agent.memory, {})

    def test_recall_lists_saved_information(self):
        self.agent.process_input("/remember Coffee at 8am")
        response = self.agent.process_input("/recall")
        self.assertIn("Coffee at 8am", response)

    def test_recall_with_empty_memory(self):
        response = self.agent.process_input("/recall")
        self.assertEqual(response, "No information has been saved yet.")

    def test_forget_removes_one_entry(self):
        self.agent.process_input("/remember First fact")
        self.agent.process_input("/remember Second fact")
        response = self.agent.process_input("/forget memory_1")
        self.assertEqual(response, "Removed memory_1.")
        self.assertNotIn("memory_1", self.agent.memory)
        self.assertIn("memory_2", self.agent.memory)

    def test_forget_all_clears_memory(self):
        self.agent.process_input("/remember A fact")
        response = self.agent.process_input("/forget all")
        self.assertEqual(response, "All saved information has been removed.")
        self.assertEqual(self.agent.memory, {})

    def test_forget_unknown_key(self):
        response = self.agent.process_input("/forget memory_9")
        self.assertIn("No saved information found", response)

    def test_unusual_memory_keys_do_not_break_key_generation(self):
        self.agent.memory["memory_²"] = "hand-edited entry"
        response = self.agent.process_input("/remember A normal fact")
        self.assertEqual(response, "Information saved.")
        self.assertIn("memory_1", self.agent.memory)

    def test_memory_keys_stay_unique_after_deletion(self):
        self.agent.process_input("/remember First")
        self.agent.process_input("/remember Second")
        self.agent.process_input("/forget memory_1")
        self.agent.process_input("/remember Third")
        self.assertIn("memory_3", self.agent.memory)
        self.assertEqual(self.agent.memory["memory_2"], "Second")


class TestPreferences(unittest.TestCase):
    def setUp(self):
        self.agent = make_agent()

    def test_set_updates_a_preference(self):
        response = self.agent.process_input("/set tone formal")
        self.assertEqual(response, "Preference updated: tone = formal.")
        self.assertEqual(self.agent.preferences["tone"], "formal")

    def test_set_requires_a_value(self):
        response = self.agent.process_input("/set tone")
        self.assertIn("Usage: /set", response)

    def test_set_converts_booleans(self):
        self.agent.process_input("/set save_history false")
        self.assertIs(self.agent.preferences["save_history"], False)

    def test_preferences_command_lists_settings(self):
        response = self.agent.process_input("/preferences")
        self.assertIn("tone: concise", response)
        self.assertIn("language: English", response)

    def test_tone_changes_the_response_style(self):
        self.agent.process_input("/set tone formal")
        response = self.agent.process_input("Hello there")
        self.assertIn("has been received", response)

    def test_unknown_tone_falls_back_to_friendly(self):
        self.agent.process_input("/set tone sarcastic")
        response = self.agent.process_input("Hello there")
        self.assertIn("Happy to help", response)


class TestHistory(unittest.TestCase):
    def setUp(self):
        self.agent = make_agent()

    def test_history_records_requests(self):
        self.agent.process_input("Hello")
        self.agent.process_input("/help")
        self.assertEqual(self.agent.history, ["Hello", "/help"])

    def test_history_command_is_not_recorded_in_history(self):
        self.agent.process_input("Hello")
        response = self.agent.process_input("/history")
        self.assertEqual(response, "Hello")
        self.assertEqual(self.agent.history, ["Hello"])

    def test_history_command_with_no_entries(self):
        agent = make_agent(preferences={"save_history": False})
        response = agent.process_input("/history")
        self.assertEqual(response, "No conversation history is available.")

    def test_clear_command(self):
        self.agent.process_input("Hello")
        response = self.agent.process_input("/clear")
        self.assertEqual(response, "Conversation history cleared.")
        self.assertEqual(self.agent.history, [])

    def test_history_is_trimmed_to_the_maximum(self):
        agent = make_agent(maximum_history_items=3)
        for number in range(5):
            agent.process_input(f"message {number}")
        self.assertEqual(
            agent.history, ["message 2", "message 3", "message 4"]
        )

    def test_save_history_false_disables_recording(self):
        agent = make_agent(preferences={"save_history": False})
        agent.process_input("Hello")
        self.assertEqual(agent.history, [])


if __name__ == "__main__":
    unittest.main()
