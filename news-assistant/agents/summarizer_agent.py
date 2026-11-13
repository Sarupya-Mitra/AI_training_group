from llm import get_llm
from state import NewsState


def summarizer_agent(state: NewsState) -> dict:
    print("\n[Summarizer Agent] Creating a 5-point summary...")

    findings = state.get("findings")
    if not findings:
        return {"error": "No research findings to summarize."}

    prompt = f"""Summarize the research below about "{state['topic']}" into exactly 5 key points.
Number the points 1 to 5. Under each point add one line: "Source: <url>".
Only use URLs that appear in the research. Plain text only, no markdown.

Research:
{findings}"""

    try:
        summary = get_llm().invoke(prompt).content
    except Exception as e:
        return {"error": f"Summarization failed: {e}"}

    print(summary)
    return {"summary": summary}
