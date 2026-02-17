"""
Groq API Client
Handles asynchronous communication with Groq LPUs with rate limiting and retries.
"""

import os
import json
import logging
import time
import asyncio
import random
import re
from typing import Optional, Dict
from groq import AsyncGroq

logger = logging.getLogger(__name__)

# Initialize client
async_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# Configuration
MODEL_NAME = "openai/gpt-oss-120b"
TPM_LIMIT = 1000000
RPM_LIMIT = 3000

class TokenBucket:
    """Token bucket for thread-safe rate limiting."""
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity, self.refill_rate = capacity, refill_rate
        self.tokens, self.last_refill = capacity, time.time()
        self.lock = asyncio.Lock()

    async def consume(self, amount: float) -> bool:
        """Attempt to consume tokens from the bucket."""
        async with self.lock:
            now = time.time()
            self.tokens = min(self.capacity, self.tokens + (now - self.last_refill) * self.refill_rate)
            self.last_refill = now
            if self.tokens >= min(amount, self.capacity):
                self.tokens -= min(amount, self.capacity)
                return True
            return False

    async def wait_for(self, amount: float):
        """Wait until enough tokens are available."""
        check = min(amount, self.capacity)
        while not await self.consume(check):
            async with self.lock:
                wait = (check - self.tokens) / self.refill_rate
            await asyncio.sleep(max(0.1, wait + 0.05))

class GroqRateLimiter:
    """Manages TPM and RPM rate limits for Groq API."""
    def __init__(self):
        self.tpm = TokenBucket(TPM_LIMIT, TPM_LIMIT / 60.0)
        self.rpm = TokenBucket(RPM_LIMIT, RPM_LIMIT / 60.0)

    async def wait_for_capacity(self, prompt_tokens: int):
        """Wait for enough capacity to send a request."""
        await self.rpm.wait_for(1)
        await self.tpm.wait_for(prompt_tokens)

rate_limiter = GroqRateLimiter()

def estimate_tokens(text: str) -> int:
    """
    Roughly estimate token count based on string length.

    Args:
        text (str): Input text.

    Returns:
        int: Estimated token count.
    """
    return len(text) // 4

async def call_groq(prompt: str, model: str = None, temp: float = 0.0) -> str:
    """
    Single asynchronous call to Groq API.

    Args:
        prompt (str): Prompt to send.
        model (str, optional): Model override.
        temp (float): Temperature setting.

    Returns:
        str: Raw response content.
    """
    try:
        target = model or MODEL_NAME
        res = await async_client.chat.completions.create(
            model=target, temperature=temp, max_tokens=6000,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a tender analyst. Output valid JSON only. Escape all newlines and quotes within string values."},
                {"role": "user", "content": prompt}
            ]
        )
        return res.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API call failed: {str(e)}")
        raise

async def call_groq_with_retry(prompt: str, model: str = None, retries: int = 5) -> str:
    """
    Call Groq API with exponential backoff and retries.

    Args:
        prompt (str): Prompt to send.
        model (str, optional): Model override.
        retries (int): Number of retries.

    Returns:
        str: Raw response content.
    """
    for i in range(retries):
        try:
            return await call_groq(prompt, model)
        except Exception as e:
            if i == retries - 1: raise
            wait = (2 ** (i + 1)) + random.uniform(0, 1)
            await asyncio.sleep(wait if "429" not in str(e) else wait + 5)

def validate_json_response(response: str) -> dict:
    """
    Clean and parse JSON from LLM response content.

    Args:
        response (str): Raw string response from LLM.

    Returns:
        dict: Parsed JSON object.

    Raises:
        ValueError: If JSON is invalid and cannot be recovered.
    """
    try:
        clean = response.strip()

        # Strip markdown blocks if present
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0]
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0]

        clean = clean.strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        try:
            # Attempt to fix literal newlines in strings
            replaced = re.sub(r'(?<!\\)\n', r'\\n', clean)
            return json.loads(replaced)
        except:
             pass
        raise ValueError(f"Invalid JSON response from LLM: {response[:100]}...")
