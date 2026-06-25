"""
Main entry point for the Discord Gemini Chatbot.
Initializes and runs the Discord bot.
"""
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from discord.ext import commands

from settings import (
    DISCORD_BOT_TOKEN,
    BOT_PREFIX,
    BOT_ACTIVITY,
)
from ai_service import AIService
from storage import ChatDataManager
from message_handler import handle_message
from commands import setup_commands, TrackedThreadsManager


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


def start_health_server(port=8080):
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


class GeminiBot:
    """Main bot class managing initialization and event handling."""
    
    def __init__(self):
        """Initialize the bot and all services."""
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.bot = commands.Bot(
            command_prefix=BOT_PREFIX,
            intents=intents,
            help_command=None,
            activity=discord.Game(BOT_ACTIVITY)
        )
        
        self.ai_service = AIService()
        self.storage_manager = ChatDataManager()
        self.threads_manager = TrackedThreadsManager()
        
        self._load_persisted_data()
        self._register_event_handlers()
        setup_commands(self.bot, self.ai_service, self.threads_manager)
    
    def _load_persisted_data(self) -> None:
        history_data = ChatDataManager.load_chat_history()
        self.ai_service.load_history(history_data)
        self.threads_manager.threads = ChatDataManager.load_tracked_threads()
    
    def _register_event_handlers(self) -> None:
        @self.bot.event
        async def on_ready():
            await self.bot.tree.sync()
            print("----------------------------------------")
            print(f'Gemini Bot Logged in as {self.bot.user}')
            print("----------------------------------------")
        
        @self.bot.event
        async def on_message(message: discord.Message):
            await handle_message(message, self.ai_service, self.storage_manager)
    
    def run(self) -> None:
        if DISCORD_BOT_TOKEN:
            self.bot.run(DISCORD_BOT_TOKEN)
        else:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is not set")


def main():
    start_health_server(port=8080)
    bot = GeminiBot()
    bot.run()


if __name__ == '__main__':
    main()
