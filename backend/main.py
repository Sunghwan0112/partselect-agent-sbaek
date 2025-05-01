from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import re
import json
import logging, sys

from duckduckgo_search import DDGS

# ------------------ Logging Setup ------------------
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "DEBUG").upper()),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("chat_backend")

# ------------------ Env & Client -------------------
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)
MODEL_NAME = "deepseek-chat"

# ------------------ FastAPI App --------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Prompt -------------------------
SYSTEM_PROMPT = (
    "You are a helpful assistant for the PartSelect e-commerce website. "
    "You ONLY answer questions about refrigerator or dishwasher parts, "
    "installation, and order issues. Politely refuse other topics."
)

# ------------------ Utility: DuckDuckGo Search ------------------
def search_partselect(query: str) -> dict | None:
    search_query = f"{query} site:partselect.com"
    logger.debug(f"🔍 SEARCH: {search_query}")
    try:
        with DDGS() as ddgs:
            results = ddgs.text(search_query, max_results=5)
            for result in results:
                url = result.get("href", "")
                title = result.get("title", "")
                snippet = result.get("body", "")
                if "partselect.com" in url and re.search(r"PS\d{3,}", url):
                    logger.debug(f"✅ Found: {url}")
                    return {
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                    }
    except Exception as e:
        logger.warning(f"Search failed: {e}")
    return None

# ------------------ Chat Endpoint ------------------
@app.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_msg = data.get("message", "")
    logger.debug(f"USER: {user_msg!r}")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Try to search based on user message
    part_info = search_partselect(user_msg)
    if part_info:
        grounding = (
            f"[PART INFO FOUND VIA SEARCH]\n"
            f"Title: {part_info['title']}\n"
            f"URL: {part_info['url']}\n"
            f"Snippet: {part_info['snippet']}\n"
        )
        messages.append({"role": "system", "content": grounding})
    else:
        logger.warning("⚠️ No part info found from DuckDuckGo.")

    messages.append({"role": "user", "content": user_msg})

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2,
        )
        reply = response.choices[0].message.content.strip()
        logger.debug("FINAL REPLY: %s", reply)
        return {"reply": reply}

    except Exception as e:
        logger.exception("🔥 Exception during model call")
        return {"reply": f"⚠️ Error: {str(e)}"}
