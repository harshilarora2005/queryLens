"""Provider-agnostic LLM client. Returns plain text completion."""
from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv("config/.env")

PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()


def call_llm(system: str, user: str, temperature: float = 0.0) -> str:
    if PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""

    if PROVIDER == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(
            os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            system_instruction=system,
        )
        resp = model.generate_content(
            user,
            generation_config={"temperature": temperature},
        )
        return resp.text or ""

    raise ValueError(f"Unknown provider: {PROVIDER}")
