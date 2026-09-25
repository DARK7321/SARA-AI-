import os

from packages.personal_ai.assistant import PersonalAssistant


def test_personal_assistant_routes_open_app_command():
    assistant = PersonalAssistant(permission_policy="ask")
    result = assistant.run("Open Notepad")

    assert result["status"] == "approval_required"
    assert result["command"] == "open_app"
    assert result["target"] == "notepad"


def test_personal_assistant_routes_write_document_command():
    assistant = PersonalAssistant(permission_policy="allow")
    result = assistant.run("Write an essay about AI into My Document")

    assert result["status"] == "ready"
    assert result["command"] == "write_text"
    assert "essay" in result["text"].lower()
    assert "My Document" in result["target"] or "document" in result["target"].lower()


def test_personal_assistant_answers_general_questions():
    assistant = PersonalAssistant(permission_policy="allow")
    result = assistant.run("What is AI?")

    assert result["status"] == "ready"
    assert result["command"] == "answer"
    assert "AI" in result["text"]


def test_personal_assistant_uses_env_allowed_roots():
    previous = os.environ.get("OMNIBRAIN_HOST_ALLOWED_ROOTS")
    os.environ["OMNIBRAIN_HOST_ALLOWED_ROOTS"] = "/tmp;/var/tmp"
    try:
        assistant = PersonalAssistant(permission_policy="allow")
        assert str(assistant.allowed_roots[0]).endswith("tmp")
    finally:
        if previous is None:
            os.environ.pop("OMNIBRAIN_HOST_ALLOWED_ROOTS", None)
        else:
            os.environ["OMNIBRAIN_HOST_ALLOWED_ROOTS"] = previous


def test_personal_assistant_rejects_unsafe_paths():
    assistant = PersonalAssistant(permission_policy="allow")

    try:
        assistant.parse("Write a report to C:/Windows/System32/evil.txt")
        assert False, "Expected path validation to reject an unsafe path"
    except ValueError:
        pass
