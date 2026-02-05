# app/unbound_client.py
"""
Client for calling the Unbound API to interact with various LLM models.
Replace UNBOUND_API_KEY with your actual API key from the hackathon.
"""
import httpx
import os
import logging
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

# Configuration - Replace with your actual Unbound API details
UNBOUND_API_URL = os.getenv("UNBOUND_API_URL", "https://api.getunbound.ai/v1/chat/completions")
UNBOUND_API_KEY = os.getenv("UNBOUND_API_KEY", "c87829d8a0dd941e60fa2a2e265728f039534d4061b36f6a572159678eab3bca8829550ada87bc4f496d150dc4d0420a")

# Model mapping (Unbound may use different model IDs)
# Most models use direct IDs, no mapping needed
MODEL_MAPPING = {}

# Cost per 1M tokens (approximate - adjust based on actual pricing)
# These are example rates - update with actual Unbound pricing
MODEL_COSTS = {
    "kimi-k2p5": {"input": 0.15, "output": 0.60, "context_limit": 262000},
    "kimi-k2-instruct-0905": {"input": 0.15, "output": 0.60, "context_limit": 256000},
    # Add more models as needed
}

# Model tiers for auto-selection (cheapest first)
MODEL_TIERS = [
    {"id": "kimi-k2-instruct-0905", "complexity": "simple", "description": "Best for simple, instruction-following tasks"},
    {"id": "kimi-k2p5", "complexity": "complex", "description": "Best for complex reasoning, extended thinking"},
]

DEFAULT_COST = {"input": 0.50, "output": 1.50}  # Fallback for unknown models


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost in USD based on token usage."""
    costs = MODEL_COSTS.get(model, DEFAULT_COST)
    input_cost = (prompt_tokens / 1_000_000) * costs["input"]
    output_cost = (completion_tokens / 1_000_000) * costs["output"]
    return round(input_cost + output_cost, 6)


def select_model_for_task(prompt: str, criteria_type: str = "always_pass") -> str:
    """
    Auto-select the best model for a task based on complexity.
    
    Simple heuristics:
    - Short prompts with simple criteria → use cheaper model
    - Long prompts, code generation, or complex criteria → use better model
    """
    prompt_length = len(prompt)
    
    # Indicators of complex tasks
    complex_indicators = [
        "code", "function", "class", "implement", "algorithm",
        "analyze", "reason", "explain why", "step by step",
        "json schema", "validate", "debug", "optimize"
    ]
    
    is_complex = (
        prompt_length > 1000 or
        criteria_type in ["llm_judge", "json_valid", "code_block"] or
        any(indicator in prompt.lower() for indicator in complex_indicators)
    )
    
    if is_complex:
        return "kimi-k2p5"  # Better model for complex tasks
    else:
        return "kimi-k2-instruct-0905"  # Cheaper model for simple tasks


async def call_llm(
    model: str,
    prompt: str,
    context: Optional[str] = None,
    system_prompt: Optional[str] = None,
    max_tokens: int = 4000,
    temperature: float = 0.7
) -> dict:
    """
    Call an LLM via the Unbound API.
    
    Args:
        model: The model ID to use
        prompt: The user prompt
        context: Optional context from previous step
        system_prompt: Optional system prompt
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
    
    Returns:
        dict with 'success', 'response', and optionally 'error'
    """
    # Build the full prompt with context if provided
    full_prompt = prompt
    if context:
        full_prompt = f"Context from previous step:\n{context}\n\n---\n\n{prompt}"
    
    # Build messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": full_prompt})
    
    # Map model ID
    mapped_model = MODEL_MAPPING.get(model, model)
    
    # Prepare request
    payload = {
        "model": mapped_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    headers = {
        "Authorization": f"Bearer {UNBOUND_API_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        logger.info(f"Calling Unbound API: model={mapped_model}, prompt_length={len(full_prompt)}")
        
        # Use synchronous requests with retry logic for connection issues
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        import time
        
        # Retry logic with manual backoff for connection errors
        max_retries = 5
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 2, 4, 8, 16 seconds
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries}, waiting {wait_time}s...")
                    time.sleep(wait_time)
                
                # Use fresh session with connection: close to avoid keep-alive issues
                headers["Connection"] = "close"
                
                response = requests.post(
                    UNBOUND_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=180
                )
                
                logger.info(f"API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    # OpenAI-compatible response format
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return {
                        "success": True,
                        "response": content,
                        "usage": data.get("usage", {}),
                    }
                elif response.status_code in [429, 500, 502, 503, 504]:
                    # Retryable server errors
                    last_error = f"API error: {response.status_code} - {response.text[:200]}"
                    logger.warning(f"Retryable error on attempt {attempt + 1}: {last_error}")
                    continue
                else:
                    logger.error(f"API error: {response.status_code} - {response.text[:500]}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code} - {response.text[:200]}",
                        "response": None,
                    }
                    
            except requests.Timeout:
                last_error = "Request timed out after 180 seconds"
                logger.warning(f"Timeout on attempt {attempt + 1}")
                continue
                
            except (requests.ConnectionError, requests.RequestException) as e:
                last_error = f"Connection error: {str(e)}"
                logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                continue
        
        # All retries exhausted
        logger.error(f"All {max_retries} retries exhausted. Last error: {last_error}")
        return {
            "success": False,
            "error": f"Request failed after {max_retries} retries: {last_error}",
            "response": None,
        }
            
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "response": None,
        }


async def call_llm_for_judgment(
    prompt: str,
    llm_output: str,
    criteria: str,
    model: str = "kimi-k2p5"
) -> dict:
    """
    Use an LLM to judge whether output meets criteria.
    
    Args:
        prompt: The original prompt that generated the output
        llm_output: The output to evaluate
        criteria: The criteria to evaluate against
        model: Model to use for judging
    
    Returns:
        dict with 'passed' (bool) and 'explanation' (str)
    """
    judgment_prompt = f"""You are evaluating whether an LLM's output meets specific criteria.

ORIGINAL PROMPT:
{prompt}

LLM OUTPUT:
{llm_output}

CRITERIA TO EVALUATE:
{criteria}

Evaluate whether the output meets the criteria. Respond in this exact format:
PASSED: [YES or NO]
EXPLANATION: [Brief explanation of your judgment]
"""
    
    result = await call_llm(
        model=model,
        prompt=judgment_prompt,
        temperature=0.1  # Low temperature for consistent judgment
    )
    
    if not result["success"]:
        return {
            "passed": False,
            "explanation": f"Could not evaluate: {result['error']}"
        }
    
    response = result["response"].upper()
    passed = "PASSED: YES" in response or "PASSED:YES" in response
    
    # Extract explanation
    explanation = result["response"]
    if "EXPLANATION:" in result["response"]:
        explanation = result["response"].split("EXPLANATION:", 1)[1].strip()
    
    return {
        "passed": passed,
        "explanation": explanation
    }


async def summarize_for_context(
    content: str,
    max_tokens: int = 500,
    model: str = "kimi-k2p5"
) -> str:
    """
    Summarize content to create context for the next step.
    
    Args:
        content: The content to summarize
        max_tokens: Maximum tokens for the summary
        model: Model to use for summarization
    
    Returns:
        Summarized content
    """
    summary_prompt = f"""Summarize the following content concisely, preserving key information, code snippets, and important details:

{content}

Provide a clear, structured summary that captures the essential points."""
    
    result = await call_llm(
        model=model,
        prompt=summary_prompt,
        max_tokens=max_tokens,
        temperature=0.3
    )
    
    if result["success"]:
        return result["response"]
    else:
        # Return truncated original if summarization fails
        return content[:2000] + "... [truncated]" if len(content) > 2000 else content
