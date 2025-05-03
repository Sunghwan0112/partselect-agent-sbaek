from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os, logging, sys, re, json
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

# ------------------ Repair Guides Knowledge ------------------
def load_repair_guides() -> str:
    base_dir = os.path.dirname(__file__)
    summary_dir = os.path.abspath(os.path.join(base_dir, "..", "cache_summaries"))
    if not os.path.exists(summary_dir):
        return ""

    summaries = []
    for fname in os.listdir(summary_dir):
        if fname.endswith(".txt"):
            path = os.path.join(summary_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                lines = content.splitlines()
                category = "Refrigerator" if "refrigerator" in fname else "Dishwasher"
                summaries.append(f"[REPAIR GUIDE] {fname.replace('.txt', '').replace('_', ' ').title()} ({category})\n")

    summaries.append("\nFor full repair guides, visit:")
    summaries.append("- Refrigerator: https://www.partselect.com/Repair/Refrigerator/")
    summaries.append("- Dishwasher: https://www.partselect.com/Repair/Dishwasher/")
    return "\n".join(summaries)

# ------------------ ScraperAPI Compatibility Check ------------------
SCRAPER_KEY = os.getenv("SCRAPER_API_KEY")
SCRAPER_ENDPOINT = "https://api.scraperapi.com/"

def check_compatibility_scraperapi(part_number: str, model_number: str) -> dict:
    target_url = f"https://www.partselect.com/Models/{model_number}/Parts/?SearchTerm={part_number}"
    payload = {"api_key": SCRAPER_KEY, "url": target_url}
    try:
        resp = requests.get(SCRAPER_ENDPOINT, params=payload)
        resp.raise_for_status()
        html_text = resp.text.lower()
        logger.debug("🔍 ScraperAPI snippet: %s", html_text[:400])
        if any(err in html_text for err in [
            "sorry, we couldn't find any parts that matched",
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

def extract_model_number(text: str) -> str | None:
    candidates = re.findall(r"\b(?!PS)[A-Z]{2,4}\d{3,6}[A-Z0-9]*\b", text, re.I)
    for model in candidates:
        if len(model) >= 6 and any(c.isdigit() for c in model):
            return model.upper()
    return None

# ------------------ Chat Endpoint ------------------
BASE_RULES = (
        "You are a friendly and helpful assistant for the PartSelect e-commerce website. "
        "You ONLY answer questions about refrigerator or dishwasher parts. "
        "If the part is NOT compatible, simply state so and do NOT suggest alternative parts unless the user explicitly asks. "
        "Politely refuse off‑topic queries.\n\n"

        "When answering questions about appliance problems, do NOT guess or invent URLs. "
        "Instead, guide users to these official repair pages depending on the appliance type:\n"
        "- Refrigerator: https://www.partselect.com/Repair/Refrigerator/\n"
        "- Dishwasher: https://www.partselect.com/Repair/Dishwasher/\n\n"

        "When asked about order-related topics like 'Check Order Status', 'Return an Order', or 'Cancel an Order', respond as if the user is authenticated. "
        "Generate a realistic but fictional order number (e.g., #PS123456789) and confirm the action in a helpful tone. "
        "Do not prompt for personal information or imply real backend integration.\n\n"

        "If the user asks about returning a part or mentions a return, always provide this official return policy page:\n"
        "https://www.partselect.com/365-Day-Returns.htm\n\n"

        + load_repair_guides()
)


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    global last_part_number
    data = await request.json()
    user_msg = data.get("message", "")
    logger.debug("USER: %r", user_msg)

    messages = [{"role": "system", "content": BASE_RULES}]

    part_match = re.search(r"\bPS\d{5,}\b", user_msg, re.I)
    current_part = part_match.group(0).upper() if part_match else None
    if current_part:
        last_part_number = current_part
        logger.debug("📌 Current part: %s", current_part)

    model_number = extract_model_number(user_msg)
    is_compat_q = bool(re.search(r"\b(is|compatible|fit|works|work with)\b", user_msg.lower()))
    refers_prev = bool(re.search(r"\b(this|it|part|one|item)\b", user_msg.lower()))

    part_for_check = current_part or (last_part_number if refers_prev and is_compat_q else None)

    if model_number and part_for_check:
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

