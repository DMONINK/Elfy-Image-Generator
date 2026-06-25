# Elfy — Discord AI Chatbot

A conversational Discord bot powered by **[Google Gemini](https://ai.google.dev/gemini-api/docs/api-key)** for chat & **[Pollinations.ai](https://pollinations.ai)** for image generation. Elfy maintains per-channel memory, handles images and documents as attachments, and can generate or transform images on request.

[![Try Now](https://img.shields.io/badge/Try%20Now-%F0%9F%8C%B8%20Live%20Demo-b19fdd?style=for-the-badge)](https://dmonink.github.io/Elfy-Image-Generator/)

---

## Features

- **Conversational chat** — Gemini-backed responses with persistent per-channel history across bot restarts
- **Text-to-image generation** — routes image requests to Pollinations.ai (Flux model); Gemini first expands the prompt for better detail
- **Image editing** — attach a photo and ask Elfy to transform it (anime, cartoon, painting, etc.) using Gemini's native image model

  **Note:** Image editing will not work with free tier API, you'll need paid Gemini API for this to work.
- **Multimodal inputs** — accepts images, audio, PDFs, code files, and CSVs as Discord attachments
- **Custom personas** — `/forget [persona]` resets history and sets a new personality on the fly
- **Tracked threads** — `/createthread` spawns a dedicated thread where Elfy responds to every message automatically
- **DM support** — talk to Elfy directly without mentioning her

---

## Setup

### 1. Prerequisites

- Python 3.10+
- A Discord bot token — [discord.com/developers/applications](https://discord.com/developers/applications)
- A Google Gemini API key — [Google AI Studio](https://aistudio.google.com/) (free tier: up to 60 req/min)
- A Pollinations.ai API key — [Pollinations.ai](https://pollinations.ai) (required for authenticated image generation)

### 2. Clone and install

```bash
git clone https://github.com/DMONINK/Elfy-AI
cd Elfy-AI
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
GOOGLE_AI_KEY=your_gemini_api_key
POLLINATIONS_API_KEY=your_pollinations_api_key
```

| Variable | Required | Description |
|---|---|---|
| `DISCORD_BOT_TOKEN` | ✅ | Bot token from the Discord developer portal |
| `GOOGLE_AI_KEY` | ✅ | Gemini API key from ai.google.dev |
| `POLLINATIONS_API_KEY` | ✅ | Pollinations.ai key for authenticated image generation |

### 4. Run

```bash
python main.py
```

---

## Usage

Elfy responds when:
- **@mentioned** in any channel
- Messaged in a **DM**
- Active in a **tracked channel or thread** (configured in `settings.py` or created via `/createthread`)

### Commands

| Command | Description |
|---|---|
| `/forget` | Clear chat history for the current channel |
| `/forget [persona]` | Clear history and set a new persona (e.g. `/forget a pirate`) |
| `/createthread [name]` | Create a thread where Elfy responds to every message |

### Image generation

Say anything containing phrases like *generate an image*, *create a picture*, *draw*, *imagine*, *render*, etc. and Elfy will route the request to Pollinations.ai.

```
generate an image of a fox in a neon city at night
```

### Image editing

Attach a photo and use phrases like *turn this into*, *anime style*, *cartoonify*, *restyle this*, etc.

```
[attach photo] make this anime style
```

---

## Customization

All configuration lives in `settings.py`.

### Bot persona / system prompt

Edit `BOT_TEMPLATE` to change Elfy's personality or starting instructions:

```python
BOT_TEMPLATE = [
    {'role': 'user', 'parts': ["You are a helpful assistant."]},
    {'role': 'model', 'parts': ["Got it! Ready to help."]},
]
```

### Tracked channels

Add channel or thread IDs to `TRACKED_CHANNELS` so Elfy responds to every message without needing an @mention:

```python
TRACKED_CHANNELS = [
    123456789012345678,  # replace with your channel ID
]
```

### Generation parameters

```python
TEXT_GENERATION_CONFIG = {
    "temperature": 0.75,
    "top_p": 0.96,
    "top_k": 40,
    "max_output_tokens": 512,
}

IMAGE_GENERATION_CONFIG = {
    "temperature": 0.2,
    "top_p": 0.9,
    "top_k": 32,
    "max_output_tokens": 800,
}
```

### Content safety

```python
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT",        "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH",        "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",  "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",  "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
```

Set any threshold to `"BLOCK_NONE"` to disable that filter.

---

## How it works

```
Discord message
      │
      ▼
 Intent detection
 ┌────────────────────────────────────┐
 │ image edit? → Gemini image model   │
 │ image gen?  → Gemini prompt boost  │
 │              → Pollinations.ai Flux│
 │ text chat?  → Gemini chat session  │
 └────────────────────────────────────┘
      │
      ▼
 Reply in Discord (text split to 1900 chars, images as file attachments)
      │
      ▼
 History saved to local shelve DB
```

---

## File structure

```
├── main.py            # Entry point, bot initialization
├── ai_service.py      # Gemini + Pollinations.ai integration
├── message_handler.py # Discord message routing
├── commands.py        # Slash commands (/forget, /createthread)
├── attachments.py     # Attachment download and MIME detection
├── storage.py         # Persistent chat history (shelve)
├── settings.py        # All configuration and environment loading
└── requirements.txt
```

---

## Notes

- Chat history persists between bot restarts via Python's `shelve` module (`chatdata.*` files)
- Error logs are written to `errors.log` at runtime
- A lightweight health-check HTTP server runs on port `8080` (useful for uptime monitors and hosting platforms)
- Image attachment context is not retained in chat history due to API limitations

---

## License

MIT — see [LICENSE](LICENSE) for details.
