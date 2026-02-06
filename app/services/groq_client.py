import os
import json
import logging
import time
import asyncio
import random
from typing import Optional, Dict
from groq import AsyncGroq

logger = logging.getLogger(__name__)

# Initialize Async Groq client
# api_key is read directly from environment (loaded by load_dotenv in main.py)
async_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# Primary Model Configuration
# Model: openai/gpt-oss-120b | Limits: High throughput for large document analysis
MODEL_NAME = "openai/gpt-oss-120b"
MODEL_LIMITS = {
    "tpm": 1000000,
    "rpm": 3000
}


class TokenBucket:
    """Token bucket for rate limiting."""
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity, self.refill_rate = capacity, refill_rate
        self.tokens, self.last_refill = capacity, time.time()
        self.lock = asyncio.Lock()

    async def consume(self, amount: float) -> bool:
        async with self.lock:
            now = time.time()
            self.tokens = min(self.capacity, self.tokens + (now - self.last_refill) * self.refill_rate)
            self.last_refill = now
            if self.tokens >= min(amount, self.capacity):
                self.tokens -= min(amount, self.capacity)
                return True
            return False

    async def wait_for(self, amount: float):
        check = min(amount, self.capacity)
        while not await self.consume(check):
            async with self.lock:
                wait = (check - self.tokens) / self.refill_rate
            await asyncio.sleep(max(0.1, wait + 0.05))

class GroqRateLimiter:
    """Manages TPM and RPM rate limits."""
    def __init__(self):
        self.tpm = TokenBucket(MODEL_LIMITS["tpm"], MODEL_LIMITS["tpm"] / 60.0)
        self.rpm = TokenBucket(MODEL_LIMITS["rpm"], MODEL_LIMITS["rpm"] / 60.0)

    async def wait_for_capacity(self, prompt_tokens: int):
        await self.rpm.wait_for(1)
        await self.tpm.wait_for(prompt_tokens)

rate_limiter = GroqRateLimiter()

def estimate_tokens(text: str) -> int:
    """Estimated tokens (chars // 4)."""
    return len(text) // 4

async def call_groq(prompt: str, model: str = None, temp: float = 0.0) -> str:
    """Asynchronous Groq API call with rate limiting."""
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
        logger.error(f"Groq call failed: {str(e)}")
        raise

async def call_groq_with_retry(prompt: str, model: str = None, retries: int = 5) -> str:
    """Call Groq with exponential backoff on failure."""
    for i in range(retries):
        try: return await call_groq(prompt, model)
        except Exception as e:
            if i == retries - 1: raise
            wait = (2 ** (i + 1)) + random.uniform(0, 1)
            await asyncio.sleep(wait if "429" not in str(e) else wait + 5)

def validate_json_response(response: str) -> dict:
    """Clean and parse JSON from LLM response with fallback for common errors."""
    try:
        clean = response.strip()
        # Handle markdown code blocks
        if "```json" in clean:
            clean = clean.split("```json")[1]
            if "```" in clean:
                clean = clean.split("```")[0]
        elif "```" in clean:
            clean = clean.split("```")[1]
            if "```" in clean:
                clean = clean.split("```")[0]

        clean = clean.strip()
        return json.loads(clean)
    except json.JSONDecodeError as e:
        # Fallback: Try to escape unescaped control characters (newlines to \n)
        try:
            import re
            # Replace literal newlines in strings with \n, but be careful not to break structure
            # This is a naive heuristic: if we see a newline that is NOT followed by whitespace+quote or whitespace+brace, it might be inside a string
            replaced = re.sub(r'(?<!\\)\n', r'\\n', clean)
            return json.loads(replaced)
        except:
             pass
        raise ValueError(f"Invalid JSON: {str(e)} | Context: {clean[:100]}...")
    except Exception as e:
        raise ValueError(f"Invalid JSON: {str(e)}")
