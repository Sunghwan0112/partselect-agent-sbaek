# PartSelect AI Assistant 🤖

This is a React + FastAPI based AI chatbot for assisting customers with refrigerator and dishwasher part questions from the [PartSelect](https://www.partselect.com) website. It includes product compatibility checking, repair guide suggestions, and common customer service options.

---

## 🧠 Features

- Natural language understanding using LLM (DeepSeek Chat API)
- Answers only relevant refrigerator and dishwasher part queries
- Rejects off-topic or unsupported requests
- Checks part compatibility with a given model via [PartSelect](https://www.partselect.com)
- Suggests official repair pages when relevant
- First-time UI with quick-start buttons and animated robot thinking state
- Markdown rendering (hyperlinks, formatting)
- Chat interface auto-scrolls to latest message

---

## 🖼️ Demo Preview

Include a screenshot like `screenshot.png` here if available.

---

## 📦 Tech Stack

| Layer         | Tech             |
|---------------|------------------|
| Frontend      | React (CRA), CSS |
| UI Components | Ant Design       |
| Backend       | FastAPI (Python) |
| LLM API       | DeepSeek Chat    |
| Data Source   | PartSelect.com   |
| Search        | Brave Search API |
| Hosting       | GitHub Pages (Frontend Only) |

---

## 🛠️ Local Development Setup

### 1. Clone the Repo

```bash
git clone https://github.com/your-username/partselect-chat-agent.git
cd partselect-chat-agent
```

### 2. Install React Dependencies

```bash
npm install
```

### 3. Set Up Backend

Make sure you have Python + FastAPI environment ready:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

It runs on `http://localhost:8000`.

### 4. Run React Frontend

```bash
npm start
```

It runs on `http://localhost:3000`.

---

## 🚀 Production Build

To build the React app:

```bash
npm run build
```

Then deploy `build/` to any static site host (e.g., GitHub Pages, Vercel).  
Note: The backend must also be deployed separately.

---

## 🔐 Deployment Notes

- GitHub Pages can host the **frontend only**.
- The backend must be hosted on a public server (e.g., Render, Fly.io, or self-hosted).

---

## 🧪 Testing Tips

- Try part numbers like `PS3406971`
- Try model numbers like `FFTR2021TS0`
- Ask questions like:
  - "Is this part compatible with FFTR2021TS0?"
  - "My Whirlpool fridge is leaking water"
- Off-topic questions are rejected politely

---

## 📁 Environment Variables

Create a `.env` file in your backend directory:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
BRAVE_API_KEY=your_brave_api_key
```

In your frontend, set `REACT_APP_API_URL=http://localhost:8000` for development.

---

## 🙋‍♂️ Maintainer

Built by Sunghwan Baek @ Carnegie Mellon University  
For contributions or issues, open a GitHub Issue or PR.

