# wednesday_core/config.py

import os
from openai import OpenAI

def get_openai_client():
    """
    Create and return an OpenAI client.
    Assumes OPENAI_API_KEY is set in the environment.
    """
    return OpenAI()


def get_model_name():
    """
    Which model should Wednesday use for thinking?
    You can change this later.
    """
    # gpt-5.1 is a strong general model. You could also use "gpt-5-mini" to save money.
    return "gpt-5.1"
