"""Quick test that the AI provider works. Run: python check_ai.py"""
import time

from lesson_tool.config import get_settings
from lesson_tool.llm import make_llm

s = get_settings()
print("provider:", s.provider, "| groq key:", bool(s.groq_api_key), "| gemini key:", bool(s.gemini_api_key))
t = time.time()
print(make_llm(s).generate_json('Return JSON {"ok": true, "word": "hello"}', task="check"))
print(f"works - {time.time() - t:.1f}s")
