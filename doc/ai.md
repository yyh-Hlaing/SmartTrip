# SmartTrip AI Assistant Documentation

## 1. Overview

SmartTrip AI is the conversational travel assistant used by the SmartTrip application.

The AI is designed specifically for:

- Casual conversations
- Travel questions
- Myanmar destination recommendations
- Restaurant and food recommendations
- Questions about places
- Popularity and ranking questions
- Weather questions
- Follow-up questions about previously discussed places
- Travel advice
- Basic comparisons between destinations
- Questions based on real database information

The AI does **not** simply generate random travel information.

Instead, it combines:

1. User conversation
2. Session-based conversation memory
3. Intent detection
4. Database queries
5. SQL aggregation
6. TF-IDF semantic matching
7. Real-time weather data
8. Groq LLM
9. Structured entity suggestions

The overall architecture is:

```text
                    ┌──────────────────────┐
                    │      User Chat       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   /api/chat POST     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Validate Session    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Detect Intent      │
                    └──────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
          Analytical       Follow-up       Normal
            Query          Conversation     Search
                │              │              │
                ▼              ▼              ▼
          SQL Ranking      Last Entity     TF-IDF/KNN
                │              │              │
                └──────────────┼──────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Build AI Context    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Groq LLM         │
                    │ llama-3.3-70b        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Save Conversation    │
                    │ + Last Entity        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   JSON Response      │
                    └──────────────────────┘

```text

                    ai.py
                    │
                    ├── Weather System
                    │   ├── WEATHER_CODES
                    │   ├── get_realtime_weather()
                    │   └── get_fallback_weather_for_region()
                    │
                    ├── Conversation Memory
                    │   ├── get_conversation_history()
                    │   ├── save_message()
                    │   ├── get_last_entity()
                    │   └── save_last_entity()
                    │
                    ├── Intent Detection
                    │   └── detect_intent()
                    │
                    ├── Region Detection
                    │   └── extract_region_from_text()
                    │
                    ├── Analytical Search
                    │   └── fetch_analytical_entities()
                    │
                    ├── Semantic Search
                    │   └── find_relevant_entities()
                    │
                    ├── Context Builder
                    │   └── build_context()
                    │
                    ├── Prompt Builder
                    │   └── build_system_prompt()
                    │
                    ├── Groq Integration
                    │   └── call_groq()
                    │
                    └── API
                        └── /api/chat
