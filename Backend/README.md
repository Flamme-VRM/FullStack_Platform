# AsylBILIM v2 📚 - UNT Preparation Assistant for Kazakh Students

AsylBILIM is a specialized AI-powered Telegram bot designed exclusively for **UNT (Unified National Testing)** preparation for Kazakhstani students. Built on Google's advanced Gemini 3.0 Flash Preview LLM with RAG (Retrieval-Augmented Generation) capabilities, AsylBILIM provides instant, accurate, and localized assistance for UNT exam preparation, all in the Kazakh language.

## ✨ Why AsylBILIM?

Preparing for UNT can be challenging. AsylBILIM streamlines your UNT preparation by offering:

* **100% Kazakh Language Support:** Get answers and explanations exclusively in Kazakh, ensuring clarity and cultural relevance.
* **UNT-Focused Assistance:** Specialized AI trained specifically for UNT exam preparation and question types.
* **Semantic RAG System:** Access to a deep knowledge base of UNT study materials using advanced vector search.
* **Smart Rate Limiting:** Fair usage system (15 messages per 24 hours) to ensure quality service for all students.
* **Specialized Voice Input:** High-accuracy Kazakh speech recognition powered by specialized Whisper models.
* **Intelligent Context Awareness:** The bot remembers your conversation history for more coherent learning sessions.

**AsylBILIM is your dedicated UNT preparation AI tutor, available 24/7 to help you excel!**

## 🚀 Key Features

* **UNT-Specialized AI (Gemini 3.0 Flash Preview):** Get accurate answers to UNT-specific questions with advanced LLM technology.
* **SQLite-based Vector Search:** High-performance local semantic search for retrieving relevant educational context.
* **Smart Document Indexing:** Offline indexing script to process and vectorize UNT study materials.
* **File-Based System Prompts:** Dynamic system prompt loading from `SYSPROMPT.txt` for easy configuration.
* **Kazakh Whisper ASR:** Specialized Hugging Face model (`whisper-turbo-ksc2`) for accurate Kazakh voice transcription.
* **Redis Caching & Rate Limiting:** High-performance session management and fair usage enforcement.
* **Pydantic Configuration:** Robust settings management via environment variables.
* **Graceful Resource Management:** Proper handling of GPU/CPU resources and ML model lifecycles.

## ⚙️ Architecture

This version features a **modular, production-ready architecture** with clear separation of concerns:

```
KazakhBot-v2-1/
├── documents.db                     # SQLite vector database
├── main.py                          # Application entry point
├── SYSPROMPT.txt                    # File-based system prompt configuration
├── requirements.txt                 # Python dependencies
├── .env                            # Environment configuration (not tracked)
├── RAG/                            # RAG document storage (JSON files)
├── scripts/                        # Utility scripts
│   ├── index_documents.py          # Script to index JSONs into Vector DB
├── tests/
│   ├── test_rag_system.py
│   ├── chunker_verify.py
│   ├── db_queries_verify.py
└── src/
    ├── __init__.py
    ├── bot.py                      # Main bot class and initialization
    ├── config.py                   # Pydantic-based configuration
    ├── api_server.py               # FastAPI server for analytics/API
    ├── handlers/
    │   ├── __init__.py
    │   └── message_handler.py      # Message routing and processing
    └── services/
        ├── __init__.py
        ├── ai.py                   # Gemini AI service with RAG integration
        ├── cache.py                # Redis caching & rate limiting
        ├── speech_to_text.py       # Kazakh Whisper ASR service
        ├── vector_db.py            # SQLite-based semantic search
        ├── embeddings.py           # Sentence-transformers embeddings
        ├── analytics.py            # Usage analytics service
        └── chunker.py              # Text chunking logic
```

### Key Architectural Components:

* **`ai.py`**: Integrates Gemini 3.0 Flash Preview with a semantic retrieval pipeline.
* **`vector_db.py`**: Custom SQLite-based vector storage for efficient local search.
* **`speech_to_text.py`**: Optimized ASR using `abilmansplus/whisper-turbo-ksc2`.
* **`indexer.py`**: Automated pipeline for document cleaning, chunking, and embedding.
* **`cache.py`**: Multi-layer caching (user history, API responses) using Redis.

## 🛠️ Technologies Used

* **Python 3.8+**: Core programming language
* **aiogram 3.0+**: Asynchronous Telegram bot framework
* **Google Generative AI**: Gemini 3.0 Flash Preview for intelligent responses
* **SQLite**: Local vector database for semantic search
* **Redis**: Distributed caching and rate limiting
* **Sentence-Transformers**: Local embedding generation
* **Hugging Face Transformers**: Whisper-based Kazakh speech recognition
* **PyTorch**: Backend for ML models (with CUDA support)
* **Pydantic v2**: Settings and data validation
* **FastAPI**: Backend API and analytics (optional)

## 🚀 Getting Started

### Prerequisites

* Python 3.8 or higher
* Redis server (5.0+)
* NVIDIA GPU (recommended for ASR)
* Google Gemini API key
* Telegram Bot Token

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Flamme-VRM/KazakhBot-v2.git
cd KazakhBot-v2-1
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file with your configuration:
```env
BOT_TOKEN=your_telegram_bot_token_here
LLM_API_KEY=your_google_gemini_api_key_here
MODEL=gemini-3.0-flash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password_here
VECTOR_DB_PATH=documents.db
```

4. Index the UNT materials:
```bash
python scripts/index_documents.py --clear
```

5. Start the bot:
```bash
python main.py
```

## 📊 Rate Limiting

To ensure fair usage and service quality:

* **Limit**: 15 messages per 24 hours per user
* **Reset**: Rolling 24-hour window from first message
* **Transparent**: Users are notified of remaining messages via the `/status` command

## 🤝 Contributing

We welcome contributions! Please fork the repository and submit a pull request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

Contact the project maintainer: [@Vermeei](https://t.me/Vermeei)

## 👨‍💻 Creator

**Created by Shyngisbek Asylkhan**

---

*Empowering Kazakhstani students to excel in UNT through AI-powered education* 🇰🇿
