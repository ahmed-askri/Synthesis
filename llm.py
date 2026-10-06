import json
import re

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL_NAME = "openai/gpt-oss-20b"


def ask(system: str, user: str, temperature: float = 0) -> str:
    client = Groq()  # reads GROQ_API_KEY from the environment
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content


def ask_json(system: str, user: str):
    text = ask(system, user + "\n\nReturn ONLY valid JSON, with no extra text.")
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)