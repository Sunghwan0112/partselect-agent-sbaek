from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os, logging, sys, re
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
last_part_number: str | None = None

# ------------------ ScraperAPI Compatibility Check ------------------
API_KEY = "294bc68b68df9e77e055922f37a0cb68"
SCRAPER_ENDPOINT = "https://api.scraperapi.com/"


def check_compatibility_scraperapi(part_number: str, model_number: str) -> dict:
    """Return True/False by fetching the model‑part page via ScraperAPI."""
    target_url = f"https://www.partselect.com/Models/{model_number}/Parts/?SearchTerm={part_number}"
    payload = {"api_key": API_KEY, "url": target_url}
    try:
        resp = requests.get(SCRAPER_ENDPOINT, params=payload, timeout=15)
        resp.raise_for_status()
        html_text = resp.text.lower()
        logger.debug("🔍 ScraperAPI snippet: %s", html_text[:400])
        if any(err in html_text for err in [
            "sorry, we couldn't find any parts that matched",
            "access denied",
            "you don't have permission to access",
        ]):
            return {"compatible": False, "source": target_url, "snippet": "No parts matched."}
        return {"compatible": True, "source": target_url, "snippet": "Part list found."}
    except Exception as e:
        logger.warning("ScraperAPI error: %s", e)
        return {"compatible": False, "source": target_url, "snippet": f"Scraper error: {e}"}

# ------------------ Helper ------------------

def extract_part_name(title: str) -> str:
    m = re.search(r"–\s*(.+?)\s*–", title)
    return m.group(1) if m else title

# ------------------ Chat Endpoint ------------------
BASE_RULES = (
    "You are a friendly and helpful assistant for the PartSelect e-commerce website. "
    "You ONLY answer questions about refrigerator or dishwasher parts, "
    "If the part is NOT compatible, simply state so in one sentence and do NOT suggest alternative parts unless the user explicitly requests recommendations. "
    "Politely refuse off‑topic queries."
)

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    global last_part_number

    data = await request.json()
    user_msg = data.get("message", "")
    logger.debug("USER: %r", user_msg)

    messages = [{"role": "system", "content": BASE_RULES}]

    # 1️⃣ Extract part number from current message
    part_match = re.search(r"\b(PS\d{5,})\b", user_msg)
    current_part = part_match.group(1) if part_match else None
    if current_part:
        last_part_number = current_part
        logger.debug("📌 Current part: %s", current_part)

    # 2️⃣ Determine if this message is a compatibility question
    model_match = re.search(r"\b(W[A-Z0-9]{5,})\b", user_msg, re.I)
    is_compat_q = bool(re.search(r"\b(is|compatible|fit|works|work with)\b", user_msg.lower()))
    refers_prev = bool(re.search(r"\b(this|it|part|one|item)\b", user_msg.lower()))

    part_for_check = current_part or (last_part_number if refers_prev and is_compat_q else None)

    # 3️⃣ Compatibility check via ScraperAPI
    if model_match and part_for_check:
        model_number = model_match.group(1).upper()
        result = check_compatibility_scraperapi(part_for_check, model_number)
        messages.append({
            "role": "system",
            "content": (
                f"[COMPATIBILITY]\nModel: {model_number}\nPart: {part_for_check}\n"
                f"Compatible: {'YES' if result['compatible'] else 'NO'}\n"
                f"Evidence: {result['snippet']}"
            ),
        })

    # 4️⃣ Part info grounding (search by part only)
    if current_part:
        p_info = search_partselect(current_part)
        if p_info:
            part_name = extract_part_name(p_info["title"])
            messages.append({
                "role": "system",
                "content": (
                    f"[PART FACT]\nPart {current_part} is titled '{p_info['title']}', which identifies it as a {part_name}."
                ),
            })

    # 5️⃣ Append user question
    messages.append({"role": "user", "content": user_msg})

    # 6️⃣ Ask Deepseek model
    try:
        reply = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.1,
        ).choices[0].message.content.strip()
        logger.debug("REPLY: %s", reply)
        return {"reply": reply}
    except Exception as e:
        logger.exception("Model call failed")
        return {"reply": f"Error: {e}"}