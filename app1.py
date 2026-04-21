import os
import json
import requests
import yfinance as yf
import gradio as gr
import plotly.graph_objects as go
from groq import Groq

GROQ_API_KEY = os.environ["GROQ_API_KEY"]

def get_stock_data(symbol: str, period: str = "7d"):
    """Fetch stock price data for a given ticker symbol."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)
    if hist.empty:
        return {"error": f"No data found for {symbol}"}
    
    latest = hist["Close"].iloc[-1]
    prev   = hist["Close"].iloc[0]
    change = ((latest - prev) / prev) * 100
    
    return {
        "symbol": symbol,
        "current_price": round(latest, 2),
        "change_pct": round(change, 2),
        "high": round(hist["Close"].max(), 2),
        "low":  round(hist["Close"].min(), 2),
        "dates": hist.index.strftime("%Y-%m-%d").tolist(),
        "prices": [round(p, 2) for p in hist["Close"].tolist()]
    }

# Test it
print(get_stock_data("AAPL"))


def get_crypto_data(coin_id: str, days: int = 7):
    """Fetch crypto price data. Use coin ids like bitcoin, ethereum, dogecoin."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": days}
    r = requests.get(url, params=params)
    
    if r.status_code != 200:
        return {"error": f"Coin '{coin_id}' not found"}
    
    data = r.json()
    prices = [p[1] for p in data["prices"]]
    dates  = [str(p[0]) for p in data["prices"]]
    
    change = ((prices[-1] - prices[0]) / prices[0]) * 100
    
    return {
        "coin": coin_id,
        "current_price_usd": round(prices[-1], 2),
        "change_pct": round(change, 2),
        "high": round(max(prices), 2),
        "low":  round(min(prices), 2),
        "dates": dates,
        "prices": [round(p, 2) for p in prices]
    }

# Test it
print(get_crypto_data("bitcoin"))


def get_weather_data(city: str):
    """Fetch current weather and forecast using Open-Meteo (no API key needed)."""
    
    # Step 1: Get lat/lon from city name (free geocoding API)
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "en", "format": "json"}
    ).json()
    
    if not geo.get("results"):
        return {"error": f"City '{city}' not found"}
    
    loc  = geo["results"][0]
    lat  = loc["latitude"]
    lon  = loc["longitude"]
    name = loc["name"]
    
    # Step 2: Get weather data
    weather = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude":  lat,
            "longitude": lon,
            "current":   "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "hourly":    "temperature_2m,precipitation_probability",
            "forecast_days": 2,
            "wind_speed_unit": "kmh"
        }
    ).json()
    
    curr    = weather["current"]
    hourly  = weather["hourly"]
    
    forecast = []
    for i in range(8):  # next 8 hours
        forecast.append({
            "time": hourly["time"][i],
            "temp": hourly["temperature_2m"][i],
            "rain_chance": hourly["precipitation_probability"][i]
        })
    
    return {
        "city":           name,
        "temperature_c":  curr["temperature_2m"],
        "humidity_pct":   curr["relative_humidity_2m"],
        "wind_kmh":       curr["wind_speed_10m"],
        "forecast_8h":    forecast,
        "dates":          [f["time"] for f in forecast],
        "prices":         [f["temp"] for f in forecast]  # reuse chart key
    }

# Test it
print(get_weather_data("Mumbai"))

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_data",
            "description": "Get real-time stock price for any company worldwide. For US stocks use ticker like AAPL, TSLA. For Indian NSE stocks add .NS like RELIANCE.NS, TCS.NS, INFY.NS. For Indian BSE stocks add .BO like RELIANCE.BO. For UK use .L, Japan use .T",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol e.g. AAPL"},
                    "period": {"type": "string", "description": "Time period: 1d, 5d, 7d, 1mo", "default": "7d"}
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_data",
            "description": "Get real-time crypto price and trend. Use full names like bitcoin, ethereum, dogecoin, solana.",
            "parameters": {
                "type": "object",
                "properties": {
                    "coin_id": {"type": "string", "description": "CoinGecko coin id e.g. bitcoin"},
                    "days":    {"type": "integer", "description": "Number of days of history", "default": 7}
                },
                "required": ["coin_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_data",
            "description": "Get current weather and forecast for any city. Uses Open-Meteo, no key needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name e.g. Mumbai, London, New York"}
                },
                "required": ["city"]
            }
        }
    }
]



client = Groq(api_key=GROQ_API_KEY)

TOOL_MAP = {
    "get_stock_data":   get_stock_data,
    "get_crypto_data":  get_crypto_data,
    "get_weather_data": get_weather_data
}

def analyze_query(user_question: str):
    messages = [
        {
            "role": "system",
            "content": (
                    "You are DataMind AI, a real-time data analyst. "
                    "Use tools to fetch live data, then give clear analysis with key numbers. "
                    "For Indian stocks always add .NS suffix for NSE (e.g. Reliance → RELIANCE.NS, TCS → TCS.NS, Infosys → INFY.NS, Wipro → WIPRO.NS). "
                    "For US stocks use standard tickers (AAPL, TSLA, GOOGL). "
                    "For crypto use full names (bitcoin, ethereum, solana). "
                    "Always mention percentage changes and what they mean."
            )
        },
        {"role": "user", "content": user_question}
    ]

    # First call — LLM decides which tool to use
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    msg = response.choices[0].message

    # If LLM called a tool
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)

        # Execute the actual function
        tool_result = TOOL_MAP[func_name](**func_args)

        # Send result back to LLM for analysis
        messages.append({"role": "assistant",    "content": None, "tool_calls": msg.tool_calls})
        messages.append({"role": "tool", "tool_call_id": tool_call.id,
                         "content": json.dumps(tool_result)})

        final = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages
        )
        analysis = final.choices[0].message.content
        return analysis, tool_result, func_name

    return msg.content, {}, "none"

# Test it
analysis, data, source = analyze_query("How is Bitcoin doing this week?")
print(analysis)


def make_chart(data: dict, source: str):
    if source == "none" or not data or "error" in data:
        return None

    fig = go.Figure()

    if source in ["get_stock_data", "get_crypto_data"]:
        label = data.get("symbol") or data.get("coin", "")
        color = "#2563eb" if data.get("change_pct", 0) >= 0 else "#dc2626"

        fig.add_trace(go.Scatter(
            x=data["dates"], y=data["prices"],
            mode="lines", name=label,
            line=dict(color=color, width=2),
            fill="tozeroy", fillcolor="rgba(37,99,235,0.08)" if color == "#2563eb" else "rgba(220,38,38,0.08)"
        ))
        title = f"{label} — {data.get('change_pct', 0):+.2f}% change"

    elif source == "get_weather_data":
        forecast = data.get("forecast_8h", [])
        if not forecast:
            return None
        times  = [f["time"] for f in forecast]
        temps  = [f["temp"] for f in forecast]

        fig.add_trace(go.Scatter(
            x=times, y=temps,
            mode="lines+markers", name="Temp °C",
            line=dict(color="#f59e0b", width=2),
            marker=dict(size=6)
        ))
        title = f"{data['city']} — Next 24h Temperature (°C)"

    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
        margin=dict(l=40,r=20,t=50,b=40),
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    )
    return fig


def respond(message, history):
    try:
        analysis, data, source = analyze_query(message)
        chart = make_chart(data, source)
    except Exception as e:
        analysis = f"Error: {str(e)}"
        chart = None

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": analysis})
    return history, chart, ""

with gr.Blocks(title="DataMind AI") as demo:
    gr.Markdown("# DataMind AI\nAsk anything about stocks, crypto, or weather.")

    with gr.Row():
        with gr.Column(scale=1):
            chatbot = gr.Chatbot(height=400)
            msg_box = gr.Textbox(
                placeholder="e.g. How is Tesla stock this week?",
                label="Your question"
            )
            gr.Examples([
                "How is Bitcoin doing today?",
                "Show me Apple stock this week",
                "What is the weather in Mumbai?",
                "Compare Ethereum and Solana",
                "Is it going to rain in Delhi?"
            ], inputs=msg_box)

        with gr.Column(scale=1):
            chart_out = gr.Plot(label="Live Chart")

    msg_box.submit(
        respond,
        inputs=[msg_box, chatbot],
        outputs=[chatbot, chart_out, msg_box]
    )

demo.launch()
