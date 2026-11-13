import os

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


def get_llm():
    return ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=0.3,
    )
