# 🍽️ AI-Powered Restaurant Recommendation System

An intelligent restaurant recommendation service inspired by Zomato. It ingests a real-world restaurant dataset, accepts user preferences, filters and ranks restaurants using an LLM (Groq), and presents personalized, explainable recommendations.

---

## ✨ Features

- **Real-World Data** — Uses the [Zomato Restaurant Dataset](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) from Hugging Face
- **Smart Filtering** — Multi-stage filtering by location, budget, cuisine, and rating
- **LLM-Powered Ranking** — Groq API (LLaMA 3 / Mixtral) ranks and explains recommendations
- **REST API** — FastAPI backend with auto-generated OpenAPI docs
- **Web UI** — Streamlit-based frontend for interactive exploration
- **Caching** — Reduces redundant LLM calls for identical queries

---

## 🏗️ Project Structure

```
Zomato Milestone/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration & environment variables
│   ├── data/
│   │   ├── loader.py           # Dataset download & ingestion
│   │   └── preprocessor.py     # Data cleaning & normalization
│   ├── models/
│   │   ├── schemas.py          # Pydantic models (request/response)
│   │   └── restaurant.py       # Restaurant data model
│   ├── services/
│   │   ├── filter_engine.py    # Preference-based filtering logic
│   │   ├── prompt_builder.py   # LLM prompt construction
│   │   └── llm_client.py       # Groq API integration
│   ├── api/
│   │   └── routes.py           # FastAPI route definitions
│   └── ui/
│       └── app.py              # Streamlit frontend
├── tests/
│   ├── test_filter_engine.py
│   ├── test_prompt_builder.py
│   └── test_llm_client.py
├── .env.example                # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md                   # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A [Groq API key](https://console.groq.com/keys)

### 1. Clone & Navigate

```bash
git clone <repository-url>
cd "Zomato Milestone"
```

### 2. Create Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Open `.env` and set your Groq API key:

```env
GROQ_API_KEY=gsk_your_actual_key_here
```

### 5. Run the API Server

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

### 6. Run the Streamlit UI (optional)

```bash
streamlit run src/ui/app.py
```

---

## 📡 API Usage

### `POST /recommend`

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Delhi",
    "budget": "medium",
    "cuisine": "Italian",
    "min_rating": 4.0,
    "additional_preferences": "family-friendly with outdoor seating"
  }'
```

### Response

```json
{
  "status": "success",
  "count": 5,
  "recommendations": [
    {
      "restaurant_name": "Olive Bar & Kitchen",
      "cuisine": "Italian, Continental",
      "rating": 4.5,
      "estimated_cost": "₹1200 for two",
      "explanation": "Top-rated Italian restaurant in Delhi with outdoor seating..."
    }
  ],
  "metadata": {
    "total_candidates_evaluated": 18,
    "filters_applied": ["location", "budget", "cuisine", "min_rating"],
    "llm_model": "llama-3.3-70b-versatile",
    "response_time_ms": 2340
  }
}
```

---

## ⚙️ Environment Variables

| Variable             | Default                                      | Description                         |
| -------------------- | -------------------------------------------- | ----------------------------------- |
| `GROQ_API_KEY`       | *(required)*                                 | Your Groq API key                   |
| `LLM_MODEL`          | `llama-3.3-70b-versatile`                    | Groq model identifier               |
| `LLM_TEMPERATURE`    | `0.7`                                        | Sampling temperature                 |
| `LLM_MAX_TOKENS`     | `1024`                                       | Max response tokens                  |
| `LLM_TIMEOUT`        | `30`                                         | API request timeout (seconds)        |
| `LLM_MAX_RETRIES`    | `3`                                          | Max retry attempts                   |
| `CACHE_TTL_SECONDS`  | `3600`                                       | Cache time-to-live (seconds)         |
| `MAX_CANDIDATES`     | `20`                                         | Max restaurants sent to LLM          |
| `APP_HOST`           | `127.0.0.1`                                  | Server host                          |
| `APP_PORT`           | `8000`                                       | Server port                          |
| `APP_DEBUG`          | `False`                                      | Debug mode                           |
| `DATASET_ID`         | `ManikaSaini/zomato-restaurant-recommendation` | Hugging Face dataset ID           |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📚 Documentation

- [Problem Statement](ProblemStatement.txt) — Original project brief
- [Context](context.md) — Project requirements and workflow
- [Architecture](architecture.md) — System design and component details
- [Implementation Plan](implementation-plan.md) — Phase-wise development roadmap
- [Edge Cases](edge-cases.md) — Corner scenarios and expected behavior

---

## 🛡️ Security Notes

- **Never commit `.env`** — It's excluded via `.gitignore`
- **Input sanitization** — All user inputs are validated via Pydantic and sanitized before prompt assembly
- **Rate limiting** — API endpoints are rate-limited to prevent abuse
- **CORS** — Restricted to trusted frontend origins

---

*Built with ❤️ using FastAPI, Groq, and Pandas*
