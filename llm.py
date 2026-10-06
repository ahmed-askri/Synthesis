import json
import re

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL_NAME = "openai/gpt-oss-20b"


def ask(system: str, user: str, temperature: float = 0, max_tokens: int = 4096) -> str:
    client = Groq()  # reads GROQ_API_KEY from the environment
    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=temperature,
        max_completion_tokens=max_tokens,
        reasoning_effort="low",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    choice = response.choices[0]
    if choice.finish_reason == "length":
        print("warning: model output was cut off (finish_reason=length)")
    return choice.message.content


def ask_json(system: str, user: str, retries: int = 2):
    last_error = None
    for attempt in range(retries + 1):
        # retry with a little randomness, since temperature 0 would repeat the same failure
        text = ask(system, user + "\n\nReturn ONLY valid JSON, with no extra text.",
                   temperature=0 if attempt == 0 else 0.3)
        text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            last_error = e
    raise ValueError(f"Model did not return valid JSON after {retries + 1} tries: {last_error}")