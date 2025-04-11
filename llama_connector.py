# llama_connector.py
import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

def query_llama(prompt: str, model="mistral:latest"):
    response = requests.post(OLLAMA_URL, json={
        "model": model,
        "prompt": prompt,
        "stream": False
    })

    response.raise_for_status()
    return response.json()["response"]
