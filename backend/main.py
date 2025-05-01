from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Initialize the OpenAI-compatible client with Deepseek settings
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),                  # Load your Deepseek API key
    base_url="https://api.deepseek.com/v1"                  # Base URL must end with /v1 for Deepseek
)

MODEL_NAME = "deepseek-chat"                                # Chat model name provided by Deepseek

# Create the FastAPI app instance
app = FastAPI()

# Enable CORS to allow frontend (e.g., localhost:3000) to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow all origins (safe for local development)
    allow_credentials=True,
    allow_methods=["*"],       # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],       # Allow all headers
)

# Prompt used to instruct the model on its role and constraints
SYSTEM_PROMPT = (
    "You are a helpful assistant for the PartSelect e-commerce website. "
    "You ONLY answer questions about refrigerator or dishwasher parts, "
    "installation, and order issues. Politely refuse other topics."
)

# Define a POST API endpoint to handle chat messages from the frontend
@app.post("/api/chat")
async def chat_endpoint(request: Request):
    # Parse JSON request body
    data = await request.json()
    user_msg = data.get("message", "")

    try:
        # Call Deepseek's ChatCompletion API
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.2,
        )
        reply = response.choices[0].message.content.strip()
        return {"reply": reply}    # Return the generated assistant response
    except Exception as e:
        return {"reply": f"⚠️ Error: {str(e)}"}  # Handle any errors gracefully
