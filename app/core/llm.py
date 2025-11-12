
from __future__ import annotations
import os, requests
from dotenv import load_dotenv
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY","")
OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY","")

def groq_chat(prompt: str, model: str="llama-3.1-8b-instant")->str:
    if not GROQ_API_KEY: return "Configura GROQ_API_KEY no .env"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"}
    body = {"model": model,"messages":[{"role":"system","content":"Responde em português europeu, sucinto."},{"role":"user","content":prompt}],"temperature":0.2,"max_tokens":256}
    r = requests.post(url, headers=headers, json=body, timeout=30); r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def openrouter_chat(prompt: str, model: str="meta-llama/llama-3.1-70b-instruct")->str:
    if not OPEN_ROUTER_API_KEY: return "Configura OPEN_ROUTER_API_KEY no .env"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPEN_ROUTER_API_KEY}","Content-Type":"application/json"}
    body = {"model": model,"messages":[{"role":"system","content":"Responde em português europeu, sucinto."},{"role":"user","content":prompt}],"temperature":0.2,"max_tokens":256}
    r = requests.post(url, headers=headers, json=body, timeout=45); r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
