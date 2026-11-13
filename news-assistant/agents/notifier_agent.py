from llm import get_llm
from state import NewsState


def notifier_agent(state: NewsState) -> dict:
    print("\n[Notifier Agent] Writing the email notification...")

    summary = state.get("summary")
    if not summary:
        return {"error": "No summary available to send."}

    prompt = f"""Write a professional email to all employees about the latest updates on "{state['topic']}".
Include a subject line, a short introduction, the 5 key points below with their source links,
and a polite closing signed "AI News Desk". Plain text only, no markdown.

Key points:
{summary}"""

    try:
        email = get_llm().invoke(prompt).content
        with open("notification.txt", "w", encoding="utf-8") as file:
            file.write(email)
    except Exception as e:
        return {"error": f"Notification failed: {e}"}

    print("[Notifier Agent] Email saved to notification.txt")
    return {"email": email}
