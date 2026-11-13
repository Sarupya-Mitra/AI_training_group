import os

from dotenv import load_dotenv

from graph import build_graph

load_dotenv()


def main():
    if not os.getenv("OPENROUTER_API_KEY") or not os.getenv("TAVILY_API_KEY"):
        print("Error: please set OPENROUTER_API_KEY and TAVILY_API_KEY in the .env file.")
        return

    topic = input("Enter a topic: ").strip()
    if not topic:
        print("Error: topic cannot be empty.")
        return

    app = build_graph()
    result = app.invoke({"topic": topic})

    if result.get("error"):
        print(f"\nError: {result['error']}")
    else:
        print("\n========== EMAIL NOTIFICATION ==========\n")
        print(result["email"])


if __name__ == "__main__":
    main()
