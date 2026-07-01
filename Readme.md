# Discord Bot to interact with Gemini API as ChatBot

## Preview

![Preview](https://i.imgur.com/j3CU5EF.png)


Inspiration - https://github.com/Echoshard/Gemini_Discordbot

This bot acts as a Chatbot. It uses Google's Gemini API which is free for upto 60 calls/min as of Jan 2023.

### Supports images, audio, documents and Gemini 1.5 completely!

## Usage

Run `/setchat #channel` (requires the **Manage Server** permission) to pick the one channel per server where the bot will chat. In that channel it responds to every message; in DMs and bot-created threads (`/createthread`) it also responds to everything. @mentioning the bot in any other channel gets a quick "please talk to me in #channel" reply that deletes itself after ~5 seconds — the bot won't otherwise engage there.

Each channel/thread has it's own context and can be erased by using /forget.

Additionally, a persona can be specified while making it forget history.

Due to API restrictions, the bot cannot remember image interactions.

Chat replies are capped at 4 lines. All slash command responses use embeds; AI chat replies are always plain text.

When someone joins the server, the bot posts a short, freshly AI-generated welcome in the server's system messages channel (Server Settings > Overview > System Messages Channel). This requires the **Server Members Intent** to be enabled for the bot in the [Discord Developer Portal](https://discord.com/developers/applications) (Bot > Privileged Gateway Intents), in addition to being enabled in code.

## Requirements

Get a Google Gemini api key from ai.google.dev

Make a discord bot at discord.com/developers/applications

## Running

Clone repository

Install all dependencies as specified in requirements.txt

Create a .env file and add GOOGLE_AI_KEY and DISCORD_BOT_TOKEN in as specified in .env.development file

Run as `python main.py`

## Customization

Optionally, you can configure the bot as follows using `settings.py`:

Add custom initial conversation for every chat by editing the BOT_TEMPLATE variable as follows:

```
BOT_TEMPLATE = [
	{'role':'user','parts': ["Hi!"]},
	{'role':'model','parts': ["Hello! I am a Discord bot!"]},
	{'role':'user','parts': ["Please give short and concise answers!"]},
	{'role':'model','parts': ["I will try my best!"]},
]
```

Change content safety settings as follows:
```
SAFETY_SETTINGS = [
	{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
	{"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
	{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
	{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
]
```

Change AI generation parameters using the variables TEXT_GENERATION_CONFIG and IMAGE_GENERATION_CONFIG

## Misc

Error logs are stored in the errors.log file created at runtime.

Chat data is stored between bot runs using shelve.
