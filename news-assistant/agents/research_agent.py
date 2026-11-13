from langchain_tavily import TavilySearch

from state import NewsState


def research_agent(state: NewsState) -> dict:
    topic = state.get("topic", "")
    print(f"\n[Research Agent] Searching the web for: {topic}")

    try:
        search = TavilySearch(max_results=5, topic="news")
        response = search.invoke({"query": topic})
        results = response.get("results", [])
    except Exception as e:
        return {"error": f"Search failed: {e}"}

    if not results:
        return {"error": "No search results found for this topic."}

    findings = "\n\n".join(
        f"Title: {r['title']}\nURL: {r['url']}\nContent: {r['content']}" for r in results
    )
    sources = [r["url"] for r in results]

    print(f"[Research Agent] Found {len(results)} articles:")
    for url in sources:
        print(f"  - {url}")

    return {"findings": findings, "sources": sources}
