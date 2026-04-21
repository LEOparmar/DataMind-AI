# DataMind-AI

# DataMind AI

> Ask anything about stocks, crypto, or weather — get instant AI analysis with live charts.

[[![HuggingFace](https://huggingface.co/spaces/ManishLeo/DataMind-AI/tree/main)

---

## What it does

Type a question in plain English. The AI figures out what data to fetch,
pulls live information, and gives you an analysis with an interactive chart.

**Example queries:**
- "How is Reliance stock doing this week?"
- "Compare Bitcoin and Ethereum"
- "What is the weather in Mumbai?"
- "Show me TCS vs Infosys"
- "Is it going to rain in Delhi tomorrow?"

---

## How it works

```
User Question → LLM decides which tool to call → Fetches live data → Analysis + Chart
```

The key concept is **LLM Tool Calling** — the model automatically selects
the right API based on what you ask. No hardcoded if/else logic.

---

## Tech Stack

| Component | Tool |
|-----------|------|
| LLM | Groq API (Llama 3.3 70B) |
| Stock data | yfinance (NSE, BSE, NYSE, NASDAQ) |
| Crypto data | CoinGecko API |
| Weather data | Open-Meteo API |
| UI | Gradio |
| Hosting | HuggingFace Spaces |

---

## Run locally

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/DataMind-AI
cd DataMind-AI
pip install -r requirements.txt
export GROQ_API_KEY=your_key_here
python app1.py
```

---

## Project Structure

```
DataMind-AI/
├── app.py              # All code — data functions, LLM tools, UI
└── requirements.txt    # Python dependencies
```

---

Made by Manish Parmar
