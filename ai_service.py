"""
AI service layer for interacting with Google's Generative AI API.
Handles chat session management, response generation, and image generation.

Image generation uses Pollinations.AI gen.pollinations.ai API with your API key.
"""

import asyncio
import traceback
import urllib.parse
from functools import partial
from typing import Dict, List, Any, Optional, Tuple

import aiohttp
from google import genai
from google.genai import types

from settings import (
    GOOGLE_AI_KEY,
    POLLINATIONS_API_KEY,
    TEXT_GENERATION_CONFIG,
    IMAGE_GENERATION_CONFIG,
    SAFETY_SETTINGS,
    BOT_TEMPLATE
)
from storage import log_error

# Keywords that indicate a user wants an image generated
IMAGE_KEYWORDS = [
    "generate image", "generate a image", "generate an image",
    "create image", "create a image", "create an image",
    "make image", "make a image", "make an image",
    "draw image", "draw a image", "draw an image",
    "generate picture", "create picture", "make picture", "draw picture",
    "generate a picture", "create a picture", "make a picture", "draw a picture",
    "generate photo", "create photo", "make photo",
    "generate a photo", "create a photo", "make a photo",
    "show me a picture", "show me an image", "show me a photo",
    "paint", "illustrate", "render image", "render a",
    "imagine", "visualize", "sketch",
]

# Keywords that indicate a user wants an existing image edited/restyled
# (as opposed to generating a brand new image from a text prompt only)
IMAGE_EDIT_KEYWORDS = [
    "turn this image", "turn this photo", "turn this picture",
    "transform this image", "transform this photo", "transform this picture",
    "convert this image", "convert this photo", "convert this picture",
    "make this image", "make this photo", "make this picture",
    "edit this image", "edit this photo", "edit this picture",
    "restyle this", "style this image", "style this photo",
    "anime style", "anime version", "cartoon version", "cartoonify",
    "turn me into", "turn him into", "turn her into", "turn them into",
    "as an anime", "as a cartoon", "as a painting",
]

# Pollinations gen API — authenticated endpoint
# Model options: flux, flux-realism, flux-pro, seedream, gptimage, etc.
# flux-pro = sharper/more detailed than base flux; enhance=true lets
# Pollinations apply its own internal prompt boosting on top of ours.
POLLINATIONS_IMAGE_URL = (
    "https://gen.pollinations.ai/image/{prompt}"
    "?model=flux&width=1024&height=1024&nologo=true&enhance=true"
)

CHAT_MODEL = "gemini-3.1-flash-lite"

# Gemini native image generation/editing model ("Nano Banana"). Supports
# text-to-image AND image+text-to-image (i.e. editing an uploaded photo).
IMAGE_EDIT_MODEL = "gemini-2.5-flash-image"

# Lightweight text model used to expand short/simple image prompts into
# detailed, descriptive ones before sending to Pollinations.
PROMPT_ENHANCER_MODEL = "gemini-2.5-flash"

PROMPT_ENHANCER_INSTRUCTION = (
    "You are an expert prompt engineer for AI image generation (Flux model). "
    "Expand the user's short image request into a single, richly detailed "
    "image-generation prompt. Include: subject details, art style, lighting, "
    "color palette, composition/camera angle, mood, and texture/quality cues "
    "(e.g. 'highly detailed', '8k', 'cinematic lighting') where appropriate. "
    "Keep it under 75 words. Do not add commentary, explanations, quotes, or "
    "labels — output ONLY the final image prompt itself, nothing else."
)


def is_image_request(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in IMAGE_KEYWORDS)


def is_image_edit_request(text: str, attachments: List[Dict[str, Any]]) -> bool:
    """True if the user attached an image and wants it transformed/restyled."""
    if not attachments:
        return False
    has_image_attachment = any(
        isinstance(a, dict) and str(a.get("mime_type", "")).startswith("image/")
        for a in attachments
    )
    if not has_image_attachment:
        return False
    lower = text.lower()
    return any(keyword in lower for keyword in IMAGE_EDIT_KEYWORDS)


class AIService:
    """Manages interactions with Google's Generative AI API."""

    def __init__(self):
        self.client = genai.Client(api_key=GOOGLE_AI_KEY)

        self._text_config = types.GenerateContentConfig(
            temperature=TEXT_GENERATION_CONFIG.get("temperature", 0.9),
            top_p=TEXT_GENERATION_CONFIG.get("top_p", 1),
            top_k=TEXT_GENERATION_CONFIG.get("top_k", 1),
        )

        self._chats: Dict[int, Any] = {}
        self._history: Dict[int, List[Dict[str, Any]]] = {}

    @staticmethod
    def _normalize_history(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        chats.create(history=...) requires each part to be a dict (or Part)
        with a 'text' key — plain strings are rejected by the SDK's
        validator. This normalizes any {"role":..., "parts": ["str", ...]}
        entries into the dict form the SDK expects, regardless of whether
        the history came from BOT_TEMPLATE, saved storage, or elsewhere.
        """
        normalized = []
        for entry in history:
            parts = entry.get("parts", [])
            norm_parts = [
                {"text": p} if isinstance(p, str) else p
                for p in parts
            ]
            normalized.append({**entry, "parts": norm_parts})
        return normalized

    def _make_chat(self, channel_id: int, history: List[Dict[str, Any]]) -> None:
        safe_history = self._normalize_history(history)
        self._chats[channel_id] = self.client.chats.create(
            model=CHAT_MODEL,
            history=safe_history,
            config=self._text_config,
        )
        self._history[channel_id] = list(history)

    def load_history(self, history_data: Dict[int, List[Dict[str, Any]]]) -> None:
        for channel_id, history in history_data.items():
            try:
                self._make_chat(channel_id, history)
            except Exception as e:
                print(
                    f"[load_history] Skipping channel {channel_id} — "
                    f"saved history incompatible (will start fresh): {e}"
                )
                self._make_chat(channel_id, list(BOT_TEMPLATE))

    # ------------------------------------------------------------------
    # Image editing — Gemini native image model (image-in, image-out)
    # ------------------------------------------------------------------

    async def edit_image_with_attachment(
        self,
        prompt: str,
        attachments: List[Dict[str, Any]],
    ) -> Optional[bytes]:
        """
        Send an uploaded image + text instruction to Gemini's native image
        model and return the newly generated image bytes, or None on failure.
        """
        parts: List[Any] = []
        for a in attachments:
            if isinstance(a, dict) and str(a.get("mime_type", "")).startswith("image/"):
                parts.append(
                    types.Part.from_bytes(data=a["data"], mime_type=a["mime_type"])
                )
        parts.append(prompt)

        def _call() -> Any:
            return self.client.models.generate_content(
                model=IMAGE_EDIT_MODEL,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _call)

            if not response or not response.candidates:
                return None

            for part in response.candidates[0].content.parts:
                if getattr(part, "inline_data", None) is not None:
                    return part.inline_data.data

            print("[edit_image_with_attachment] No inline image data in response")
            return None
        except Exception:
            log_error(
                text=prompt,
                error_traceback=traceback.format_exc(),
                history="N/A (image editing)",
                candidates="N/A",
                parts="N/A",
                prompt_feedbacks="N/A",
            )
            raise

    # ------------------------------------------------------------------
    # Image generation — Pollinations gen API (authenticated)
    # ------------------------------------------------------------------

    async def _enhance_image_prompt(self, prompt: str) -> str:
        """
        Expand a short/simple image prompt into a detailed one using Gemini,
        so Pollinations/Flux has more to work with. Falls back to the
        original prompt if enhancement fails for any reason.
        """
        def _call() -> Any:
            return self.client.models.generate_content(
                model=PROMPT_ENHANCER_MODEL,
                contents=[PROMPT_ENHANCER_INSTRUCTION, f"User request: {prompt}"],
                config=types.GenerateContentConfig(
                    temperature=IMAGE_GENERATION_CONFIG.get("temperature", 0.2),
                    top_p=IMAGE_GENERATION_CONFIG.get("top_p", 0.9),
                    top_k=IMAGE_GENERATION_CONFIG.get("top_k", 32),
                    max_output_tokens=IMAGE_GENERATION_CONFIG.get("max_output_tokens", 200),
                ),
            )

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, _call)
            enhanced = (response.text or "").strip().strip('"')
            return enhanced if enhanced else prompt
        except Exception as e:
            print(f"[_enhance_image_prompt] Falling back to raw prompt: {e}")
            return prompt

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        """
        Generate an image via Pollinations gen API using your API key.
        The prompt is first enriched by Gemini for better detail/quality.
        Returns raw image bytes or None on failure.
        """
        enhanced_prompt = await self._enhance_image_prompt(prompt)

        # Collapse whitespace/newlines and cap length — very long or
        # newline-containing prompts can trigger HTTP 400 once URL-encoded.
        cleaned_prompt = " ".join(enhanced_prompt.split())
        if len(cleaned_prompt) > 500:
            cleaned_prompt = cleaned_prompt[:500].rsplit(" ", 1)[0]

        encoded = urllib.parse.quote(cleaned_prompt)
        url = POLLINATIONS_IMAGE_URL.format(prompt=encoded)

        headers = {}
        if POLLINATIONS_API_KEY:
            headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    else:
                        body = await resp.text()
                        print(
                            f"[generate_image] Pollinations returned HTTP {resp.status} "
                            f"— body: {body[:500]} — prompt length: {len(cleaned_prompt)} "
                            f"— url length: {len(url)}"
                        )
                        return None
        except Exception:
            log_error(
                text=prompt,
                error_traceback=traceback.format_exc(),
                history="N/A (image generation)",
                candidates="N/A",
                parts="N/A",
                prompt_feedbacks="N/A",
            )
            raise

    # ------------------------------------------------------------------
    # Text chat
    # ------------------------------------------------------------------

    def _send_message_sync(self, channel_id: int, prompt_parts: List[Any]) -> Any:
        # chats.send_message() accepts: a single str/File/Part, OR a list of
        # str/File/FileDict/Part/PartDict. It does NOT accept a types.Content
        # object directly (that raises "Message must be a valid part type").
        def _to_part(p: Any) -> Any:
            if isinstance(p, str):
                return p
            if isinstance(p, types.Part):
                return p
            if isinstance(p, dict):
                # Expect a dict like {"mime_type": "image/jpeg", "data": b"..."}
                mime_type = p.get("mime_type") or p.get("mimeType")
                data = p.get("data")
                if mime_type and data is not None:
                    return types.Part.from_bytes(data=data, mime_type=mime_type)
                raise ValueError(f"Unrecognized attachment dict shape: {list(p.keys())}")
            raise TypeError(f"Unsupported prompt part type: {type(p)}")

        if len(prompt_parts) == 1 and isinstance(prompt_parts[0], str):
            message = prompt_parts[0]
        else:
            message = [_to_part(p) for p in prompt_parts]

        response = self._chats[channel_id].send_message(message)

        user_text = " ".join(
            p if isinstance(p, str) else "" for p in prompt_parts
        ).strip()
        if user_text:
            self._history[channel_id].append(
                {"role": "user", "parts": [user_text]}
            )
        if response and response.text:
            self._history[channel_id].append(
                {"role": "model", "parts": [response.text]}
            )
        return response

    async def generate_response(
        self,
        channel_id: int,
        attachments: List[Dict[str, Any]],
        text: str,
    ) -> Tuple[str, Optional[bytes]]:
        # ---- Image editing path (uploaded image + "turn this into..." etc) ----
        if is_image_edit_request(text, attachments):
            image_bytes = await self.edit_image_with_attachment(text, attachments)
            if image_bytes:
                return ("Here's your transformed image! 🎨", image_bytes)
            else:
                return (
                    "Sorry, I wasn't able to transform that image. "
                    "Please try a different prompt.",
                    None,
                )

        # ---- Image generation path (text-to-image, no input image) ----
        if is_image_request(text):
            image_prompt = text
            if 'said "' in text:
                start = text.index('said "') + 6
                end = text.rfind('"')
                if end > start:
                    image_prompt = text[start:end]

            image_bytes = await self.generate_image(image_prompt)
            if image_bytes:
                return ("Here's your generated image! 🎨", image_bytes)
            else:
                return (
                    "Sorry, I wasn't able to generate that image. "
                    "Please try a different prompt.",
                    None,
                )

        # ---- Normal text chat path ----
        response = None
        try:
            prompt_parts: List[Any] = attachments.copy()
            prompt_parts.append(text)

            if channel_id not in self._chats:
                self._make_chat(channel_id, list(BOT_TEMPLATE))

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                partial(self._send_message_sync, channel_id, prompt_parts),
            )

            return (response.text if response else "", None)

        except Exception:
            try:
                history_info = str(self._history.get(channel_id, []))
                candidates = str(response.candidates) if response else "N/A"
                parts_info = str(response.parts) if response else "N/A"
                prompt_feedbacks = str(response.prompt_feedbacks) if response else "N/A"
            except Exception:
                history_info = candidates = parts_info = prompt_feedbacks = "N/A"

            log_error(
                text=text,
                error_traceback=traceback.format_exc(),
                history=history_info,
                candidates=candidates,
                parts=parts_info,
                prompt_feedbacks=prompt_feedbacks,
            )
            raise

    def reset_channel_history(
        self,
        channel_id: int,
        custom_template: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        if custom_template is None:
            custom_template = BOT_TEMPLATE
        self._make_chat(channel_id, list(custom_template))

    def delete_channel_history(self, channel_id: int) -> None:
        self._chats.pop(channel_id, None)
        self._history.pop(channel_id, None)

    def get_history(self, channel_id: int) -> List[Dict[str, Any]]:
        return self._history.get(channel_id, [])
