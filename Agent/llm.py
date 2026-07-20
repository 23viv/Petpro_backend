from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from pathlib import Path
import os

# Load shared .env
env_path = Path(__file__).parent.parent / "env" / ".env"
load_dotenv(env_path)


def get_llm(
    model: str = "mistralai/mistral-7b-instruct:free",
    temperature: float = 0.4,
    max_tokens: int = 1024,
) -> ChatOpenAI:
    """
    Returns a LangChain ChatOpenAI instance pointed at OpenRouter.

    Change `model` to any model slug from https://openrouter.ai/models
    e.g.  "openai/gpt-4o-mini"
          "google/gemini-flash-1.5"
          "anthropic/claude-3-haiku"
          "mistralai/mistral-7b-instruct:free"  ← free tier
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY is not set in env/.env")

    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=temperature,
        max_tokens=max_tokens,
        default_headers={
            # OpenRouter recommends these for better routing / analytics
            "HTTP-Referer": "https://petpro.app",
            "X-Title": "PetPro Vet Agent",
        },
    )
