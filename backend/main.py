from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os, json, logging, sys, re
from dotenv import load_dotenv
from brave_search import search_partselect
import requests

# ------------------ App & Env ------------------
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/v1")
MODEL_NAME = "deepseek-chat"

# ------------------ Logging ------------------
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "DEBUG").upper()),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("chat_backend")

# ------------------ State ------------------
last_part_number = None

# ------------------ ScraperAPI Compatibility Check ------------------
def check_compatibility_scraperapi(part_number: str, model_number: str) -> dict:
    """
    Use ScraperAPI (simple GET via API key and target URL) to fetch the PartSelect page
    and check if the error message appears indicating incompatibility.
    """
    api_key = "294bc68b68df9e77e055922f37a0cb68"
    target_url = f"https://www.partselect.com/Models/{model_number}/Parts/?SearchTerm={part_number}"
    payload = { 'api_key': api_key, 'url': target_url }

    try:
        resp = requests.get("https://api.scraperapi.com/", params=payload)
        resp.raise_for_status()
        html_text = resp.text.lower()

        logger.debug(f"🔍 ScraperAPI snippet: {html_text[:400]}")

        error_phrases = [
            "sorry, we couldn't find any parts that matched",
            "access denied",
            "you don't have permission to access",
        ]
        if any(err in html_text for err in error_phrases):
            return {
                "compatible": False,
                "source": target_url,
                "snippet": "No parts matched or access denied.",
            }

        return {
            "compatible": True,
            "source": target_url,
            "snippet": "Compatible: page contains part results.",
        }

    except Exception as e:
        logger.warning(f"ScraperAPI error: {e}")
        return {
            "compatible": False,
            "source": target_url,
            "snippet": f"❌ ScraperAPI error: {e}",
        }

        return {
            "compatible": True,
            "source": target_url,
            "snippet": "Compatible: part matched and page loaded successfully.",
        }

    except Exception as e:
        logger.warning(f"ScraperAPI failed: {e}")
        return {
            "compatible": False,
            "source": target_url,
            "snippet": f"❌ ScraperAPI error: {e}",
        }

# ------------------ Chat Endpoint ------------------
@app.post("/api/chat")
async def chat_endpoint(request: Request):
    global last_part_number

    data = await request.json()
    user_msg = data.get("message", "")
    logger.debug(f"USER: {user_msg!r}")

    messages = [{"role": "system", "content": (
        "You are a helpful assistant for PartSelect. You ONLY answer questions about appliance parts, "
        "compatibility, and installation. Politely refuse off-topic queries."
    )}]

    # Step 1: Extract part number
    current_part_match = re.search(r"\b(PS\d{5,})\b", user_msg)
    current_part_number = current_part_match.group(1) if current_part_match else None

    if current_part_number:
        logger.debug(f"📌 Detected part number in current message: {current_part_number}")
        last_part_number = current_part_number

    # Step 2: Compatibility check
    model_match = re.search(r"\b(W[A-Z0-9]{5,})\b", user_msg, re.I)
    wants_compat = re.search(r"\b(is|compatible|fit|works|work with)\b", user_msg.lower())
    refers_to_last = re.search(r"\b(this|it|part|one|item)\b", user_msg.lower())

    part_number_for_check = current_part_number if current_part_number else (last_part_number if refers_to_last and wants_compat else None)

    if model_match and part_number_for_check:
        model_number = model_match.group(1).upper()
        logger.debug(f"🔁 Compatibility check: {part_number_for_check} + {model_number}")

        result = check_compatibility_scraperapi(part_number_for_check, model_number)

        messages.append({
            "role": "system",
            "content": (
                f"[COMPATIBILITY CHECK]\n"
                f"Model: {model_number}\n"
                f"Part: {part_number_for_check}\n"
                f"Compatible: {'✅ YES' if result['compatible'] else '❌ NO'}\n"
                f"URL: {result['source']}\n"
                f"Snippet: {result['snippet']}"
            )
        })

    # Step 3: Part info grounding
    part_info = search_partselect(user_msg)
    if part_info:
        messages.append({
            "role": "system",
            "content": (
                f"[PART INFO FOUND VIA SEARCH]\n"
                f"Title: {part_info['title']}\n"
                f"URL: {part_info['url']}\n"
                f"Snippet: {part_info['snippet']}"
            )
        })

    # Step 4: Final model call
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
