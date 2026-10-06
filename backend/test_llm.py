"""Quick check: is Ollama running and does the model answer?"""
from llm_service import MODEL, ask_llm, ollama_status

up, ready = ollama_status()
print(f"Ollama running: {up} | model '{MODEL}' pulled: {ready}")
if up and ready:
    print(ask_llm("Reply with one short sentence: what is a Python function?"))
