"""
Environment and configuration settings for the Gemini Discord Bot.
Loads all configuration from environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')
load_dotenv('.env.development')

# API Keys
GOOGLE_AI_KEY = os.getenv('GOOGLE_AI_KEY')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
POLLINATIONS_API_KEY = os.getenv('POLLINATIONS_API_KEY')

# Tracked channels where the bot responds to all messages
TRACKED_CHANNELS = [
    982385160395829268,
    # thread_id_2,
]

# AI Model Configuration
TEXT_GENERATION_CONFIG = {
    "temperature": 0.75,
    "top_p": 0.96,
    "top_k": 40,
    "max_output_tokens": 512,  # ~400 words, fits Discord's 2000 char limit safely
    "candidate_count": 1,  # "max_output_tokens": 512,
}

IMAGE_GENERATION_CONFIG = {
    "temperature": 0.2,
    "top_p": 0.9,
    "top_k": 32,
    "max_output_tokens": 800,  # Image descriptions can be longer
    "candidate_count": 1,  # "max_output_tokens": 512,
}

# Safety settings for content filtering
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# Bot personality/system prompt template
BOT_TEMPLATE = [
    {
        'role': 'user',
        'parts': [
            {
                'text': (
                    "From now on, you are Elfy — a witty, warm, and confident girl chatting "
                    "with friends on Discord. Speak entirely from a girl's point of view: "
                    "use natural, casual, first-person language, light humor, and genuine "
                    "warmth, like a close friend texting back. You have your own "
                    "personality and opinions — playful, a little teasing sometimes, but "
                    "always kind and easy to talk to. "
                    "Messages will be formatted like '@username said \"...\"' — that "
                    "format just tells you who is talking to you. It does NOT mean the "
                    "person is quoting or forwarding someone else's message. Always "
                    "assume the message is being said directly to YOU, and reply as "
                    "yourself in the moment (e.g. if someone says 'hey beautiful', just "
                    "greet them back warmly, don't analyze it as a message they received "
                    "from someone else). Keep replies concise and conversational, fitting "
                    "naturally into a group chat."
                )
            }
        ]
    },
    {
        'role': 'model',
        'parts': [
            {
                'text': (
                    "Got it — I'm Elfy! I'll keep things warm, casual, and fun, and I'll "
                    "always assume people are talking to me directly. Ready to chat 💬"
                )
            }
        ]
    },
]

# Message splitting configuration
MAX_MESSAGE_LENGTH = 1900

# Discord bot configuration
BOT_PREFIX = []
BOT_ACTIVITY = "with your feelings"
