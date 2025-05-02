import os
import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
# --- Configuration ---
REPAIR_PAGES = {
    "refrigerator": {
        "not making ice": "https://www.partselect.com/Repair/Refrigerator/Not-Making-Ice/",
        "leaking": "https://www.partselect.com/Repair/Refrigerator/Leaking/",
        "noisy": "https://www.partselect.com/Repair/Refrigerator/Noisy/",
        "will not start": "https://www.partselect.com/Repair/Refrigerator/Will-Not-Start/",
        "refrigerator too warm": "https://www.partselect.com/Repair/Refrigerator/Refrigerator-Too-Warm/",
        "not dispensing water": "https://www.partselect.com/Repair/Refrigerator/Not-Dispensing-Water/",
        "refrigerator freezer too warm": "https://www.partselect.com/Repair/Refrigerator/Refrigerator-Freezer-Too-Warm/",
        "door sweating": "https://www.partselect.com/Repair/Refrigerator/Door-Sweating/",
        "light not working": "https://www.partselect.com/Repair/Refrigerator/Light-Not-Working/",
        "refrigerator too cold": "https://www.partselect.com/Repair/Refrigerator/Refrigerator-Too-Cold/",
        "running too long": "https://www.partselect.com/Repair/Refrigerator/Running-Too-Long/",
        "freezer too cold": "https://www.partselect.com/Repair/Refrigerator/Freezer-Too-Cold/",
    },
    "dishwasher": {
        "noisy": "https://www.partselect.com/Repair/Dishwasher/Noisy/",
        "leaking": "https://www.partselect.com/Repair/Dishwasher/Leaking/",
        "will not start": "https://www.partselect.com/Repair/Dishwasher/Will-Not-Start/",
        "door latch failure": "https://www.partselect.com/Repair/Dishwasher/Door-Latch-Failure/",
        "not cleaning properly": "https://www.partselect.com/Repair/Dishwasher/Not-Cleaning-Properly/",
        "not draining": "https://www.partselect.com/Repair/Dishwasher/Not-Draining/",
        "will not fill water": "https://www.partselect.com/Repair/Dishwasher/Will-Not-Fill-Water/",
        "will not dispense detergent": "https://www.partselect.com/Repair/Dishwasher/Will-Not-Dispense-Detergent/",
        "not drying properly": "https://www.partselect.com/Repair/Dishwasher/Not-Drying-Properly/",
    }
}

SCRAPER_ENDPOINT = "https://api.scraperapi.com/"
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com/v1")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
CACHE_DIR = "cache_pages"
SUMMARY_DIR = "cache_summaries"
META_PATH = "cache_log.json"

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(SUMMARY_DIR, exist_ok=True)

def sanitize_filename(text: str) -> str:
    return text.lower().replace(" ", "_").replace("/", "_")

def summarize_with_deepseek(text: str) -> str:
    prompt = [
        {"role": "system", "content": "Summarize this appliance repair guide into clear, helpful steps for customers. Focus only on the fix instructions."},
        {"role": "user", "content": text[:5000]}
    ]
    try:
        result = client.chat.completions.create(model="deepseek-chat", messages=prompt, temperature=0.2)
        return result.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Failed to summarize: {e}"

def fetch_and_summarize(url: str, category: str, symptom: str) -> dict:
    filename = sanitize_filename(f"{category}_{symptom}")
    html_path = os.path.join(CACHE_DIR, f"{filename}.html")
    summary_path = os.path.join(SUMMARY_DIR, f"{filename}.txt")

    try:
        # 1. Fetch HTML if not cached
        if not os.path.exists(html_path):
            resp = requests.get(SCRAPER_ENDPOINT, params={"api_key": SCRAPER_API_KEY, "url": url})
            resp.raise_for_status()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(resp.text)

        # 2. Parse & clean text
        with open(html_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            clean_text = soup.get_text("\n", strip=True)

        # 3. Summarize with DeepSeek
        summary = summarize_with_deepseek(clean_text)

        # 4. Save summary
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)

        return {
            "category": category,
            "symptom": symptom,
            "url": url,
            "html_path": html_path,
            "summary_path": summary_path,
            "summary_snippet": summary[:400],
            "status": "✅"
        }

    except Exception as e:
        return {
            "category": category,
            "symptom": symptom,
            "url": url,
            "status": f"❌ Error: {e}"
        }

def main():
    log = []
    for category, items in REPAIR_PAGES.items():
        for symptom, url in items.items():
            print(f"🔎 Processing: {category} - {symptom}")
            result = fetch_and_summarize(url, category, symptom)
            log.append(result)

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    print(f"✅ Finished summarizing. Metadata saved to {META_PATH}")

if __name__ == "__main__":
    main()
