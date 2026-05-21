# wensday_core/config.py

import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


def get_openai_client():
    """
    Create and return an OpenAI client.
    Requires OPENAI_API_KEY to be set in the environment.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your OpenAI API key."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "The openai package is not installed. Run: pip install -r requirements.txt"
        ) from exc

    return OpenAI(api_key=api_key)


def get_model_name():
    """
    Which model should Wednesday use for thinking?
    You can change this later.
    """
    return os.getenv("OPENAI_MODEL", "gpt-5.1")
