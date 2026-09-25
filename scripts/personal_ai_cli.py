"""Command-line shell for the local personal assistant.

Usage:
    python scripts/personal_ai_cli.py
"""

from __future__ import annotations

from packages.personal_ai.assistant import PersonalAssistant


def main() -> None:
    assistant = PersonalAssistant(permission_policy="ask")
    print("OmniBrain Personal AI ready. Type 'exit' to quit.")
    while True:
        command = input("You> ")
        if command.strip().lower() in {"exit", "quit", "bye"}:
            print("Goodbye.")
            break
        try:
            result = assistant.run(command)
            print(result)
        except ValueError as exc:
            print(f"Assistant: {exc}")


if __name__ == "__main__":
    main()
