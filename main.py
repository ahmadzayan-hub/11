"""Entry point for the Agentic OS application.

Loads the configuration, creates the Agent, and runs the interactive
command-line loop until the user enters /exit.
"""

import sys

from agent import Agent
from utils import load_config

CONFIG_FILE = "config.json"


def main():
    try:
        config = load_config(CONFIG_FILE)
    except FileNotFoundError as error:
        print(f"Error: {error}")
        print("Create config.json in the project folder and try again.")
        return 1
    except ValueError as error:
        print(f"Error: {error}")
        print("Fix the JSON syntax in config.json and try again.")
        return 1

    agent = Agent(config)
    print(agent.get_welcome_message())

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAgent: Session closed. Goodbye.")
            break

        if not user_input:
            print("Agent: Please enter a command or question.")
            continue
        if user_input.split()[0].lower() == "/exit":
            print("Agent: Session closed. Goodbye.")
            break

        response = agent.process_input(user_input)
        print(f"Agent: {response}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
