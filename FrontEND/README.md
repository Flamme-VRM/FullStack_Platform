# AsylBILIM — Mobile UI

Flutter-based mobile interface for the **AsylBILIM** AI-powered UNT exam preparation platform.

## Features

- 💬 **Multi-chat support** — create, switch, rename, and delete conversations
- 🤖 **AI responses with Markdown** — renders bold, italics, code blocks, and lists
- 🎙️ **Voice input** — record audio and send it for Kazakh speech recognition (STT)
- 🔒 **Persistent user ID** — chats survive app restarts via `shared_preferences`
- 📡 **Server health monitoring** — offline banner when backend is unreachable
- ⚡ **SSE Streaming** — real-time response delivery for zero perceived latency
- ⌨️ **Premium Typewriter Effect** — AI responses reveal word-by-word with smooth Markdown rendering
- ⏳ **Pulsing Indicator** — elegant animation while waiting for the first token

## Project Structure

```
lib/
├── main.dart                 # App entry point, theme, MaterialApp
├── models/
│   ├── chat_info.dart        # ChatInfo model
│   ├── chat_message.dart     # ChatMessage model
│   ├── rate_limit_info.dart  # RateLimitInfo model
│   └── models.dart           # Barrel export
├── screens/
│   └── chat_screen.dart      # Main chat screen (stateful logic)
├── services/
│   └── api_service.dart      # HTTP client for all backend API calls
└── widgets/
    ├── chat_drawer.dart      # Side drawer with chat list
    ├── chat_input_area.dart  # Text input + mic button
    ├── message_bubble.dart   # Message bubble + typing animation
    ├── welcome_screen.dart   # Empty state / welcome view
    └── widgets.dart          # Barrel export
```

## Prerequisites

- [Flutter SDK](https://docs.flutter.dev/get-started/install) ≥ 3.0.0
- Android SDK (via Android Studio or command-line tools)
- Backend server running ([AI_Platform](https://github.com/Flamme-VRM/AI_Platform))

## Getting Started

```bash
# Install dependencies
flutter pub get

# Run on connected device or emulator
flutter run
```

### API Configuration

The app auto-detects the platform for the API URL:
- **Android emulator**: `http://10.0.2.2:8000/api`
- **iOS / Desktop / Web**: `http://localhost:8000/api`

To connect from a physical device, update `ApiService.baseUrl` in `lib/services/api_service.dart` with your machine's local IP.

## Backend

This frontend connects to the [AsylBILIM AI Platform](https://github.com/Flamme-VRM/AI_Platform) backend (FastAPI + Redis + Gemini AI + RAG).

## Dependencies

| Package | Purpose |
|---------|---------|
| `http` | HTTP requests to backend API |
| `flutter_markdown` | Render Markdown in bot responses |
| `shared_preferences` | Persist user ID across sessions |
| `record` | Audio recording for voice input |
| `path_provider` | Temporary file storage for recordings |
| `permission_handler` | Microphone permission management |

## License

MIT