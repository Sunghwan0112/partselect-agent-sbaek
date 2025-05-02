from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os, logging, sys, re, json
from dotenv import load_dotenv
from brave_search import search_partselect
import requests
from bs4 import BeautifulSoup

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

# ------------------ Repair Guides Knowledge ------------------
def load_repair_guides() -> str:
    base_dir = os.path.dirname(__file__)
    json_path = os.path.abspath(os.path.join(base_dir, "..", "data", "repair_guides.json"))
    with open(json_path, "r") as f:
        guides = json.load(f)
    parts = ["You also have access to official repair guides from PartSelect for common appliance symptoms:"]
    for category, items in guides.items():
        for symptom, url in items.items():
            parts.append(f"- For {category} issues like '{symptom}', refer to: {url}")
    return "\n".join(parts)

# ------------------ ScraperAPI Compatibility Check ------------------
API_KEY = "294bc68b68df9e77e055922f37a0cb68"
SCRAPER_ENDPOINT = "https://api.scraperapi.com/"

def check_compatibility_scraperapi(part_number: str, model_number: str) -> dict:
    target_url = f"https://www.partselect.com/Models/{model_number}/Parts/?SearchTerm={part_number}"
    payload = {"api_key": API_KEY, "url": target_url}
    try:
        resp = requests.get(SCRAPER_ENDPOINT, params=payload, timeout=15)
        resp.raise_for_status()
        html_text = resp.text.lower()
        logger.debug("\U0001f50d ScraperAPI snippet: %s", html_text[:400])
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
    "You ONLY answer questions about refrigerator or dishwasher parts. "
    "If the part is NOT compatible, simply state so and do NOT suggest alternative parts unless the user explicitly asks. "
    "Politely refuse off‑topic queries. "
    + load_repair_guides()
)

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    global last_part_number
    data = await request.json()
    user_msg = data.get("message", "")
    logger.debug("USER: %r", user_msg)

    messages = [{"role": "system", "content": BASE_RULES}]

    part_match = re.search(r"\b(PS\d{5,})\b", user_msg)
    current_part = part_match.group(1) if part_match else None
    if current_part:
        last_part_number = current_part
        logger.debug("\ud83d\udccc Current part: %s", current_part)

    model_match = re.search(r"\b(W[A-Z0-9]{5,})\b", user_msg, re.I)
    is_compat_q = bool(re.search(r"\b(is|compatible|fit|works|work with)\b", user_msg.lower()))
    refers_prev = bool(re.search(r"\b(this|it|part|one|item)\b", user_msg.lower()))

    part_for_check = current_part or (last_part_number if refers_prev and is_compat_q else None)

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

    messages.append({"role": "user", "content": user_msg})

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

# ------------------ Page Summarization Endpoint ------------------
@app.get("/api/summarize")
def summarize_page(url: str):
    try:
        html = requests.get(SCRAPER_ENDPOINT, params={"api_key": API_KEY, "url": url}, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")
        clean = soup.get_text("\n", strip=True)
        logger.debug("\U0001f9fc Clean text len: %d", len(clean))
        prompt = [
            {"role": "system", "content": "Summarize this PartSelect repair page for a customer in plain language."},
            {"role": "user", "content": clean[:5000]}
        ]
        summary = client.chat.completions.create(model=MODEL_NAME, messages=prompt, temperature=0.2)
        return {"summary": summary.choices[0].message.content.strip()}
    except Exception as e:
        logger.exception("Summarization failed")
        return {"summary": f"❌ Error: {e}"}
