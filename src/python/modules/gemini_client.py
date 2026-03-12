import os
import concurrent.futures
from google import genai
def get_api_keys():
    """Retrieve available Gemini API keys."""
    keys = []
    # Check environment variables
    for k in ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2"]:
        val = os.getenv(k)
        if val and val not in keys:
            keys.append(val)
            
    # Add the provided fallback keys
    fallback_keys = [
        "AIzaSyDAdFKVwg2evpROs9xMZVhPmYzRxgEPojY",
        "AIzaSyBqIBi8QWzZ732lU6n0d4VKjI-uJqLBCec"
    ]
    for fk in fallback_keys:
        if fk not in keys:
            keys.append(fk)
            
    return keys

def _make_call(api_key, model_name, contents, config):
    client = genai.Client(api_key=api_key)
    return client.models.generate_content(
        model=model_name,
        contents=contents,
        config=config
    )

def generate_content_with_fallback(model_name, contents, config=None, timeout_seconds=20):
    """
    Attempts to generate content using available Gemini API keys.
    Falls back to the next key if one is expired, fails, or is too slow (timeout).
    """
    keys = get_api_keys()
    if not keys:
        raise ValueError("No Gemini API keys available.")

    last_error = None
    for api_key in keys:
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_make_call, api_key, model_name, contents, config)
                # Enforce the "working fastly" requirement
                response = future.result(timeout=timeout_seconds)
                return response
        except concurrent.futures.TimeoutError:
            print(f"Warning: API key {api_key[:8]}... timed out after {timeout_seconds}s. Trying next primary/fallback key...")
            last_error = "TimeoutError"
            continue
        except Exception as e:
            print(f"Warning: API key {api_key[:8]}... failed ({str(e)}). Trying next primary/fallback key...")
            last_error = e
            continue
            
    raise RuntimeError(f"All API keys failed or timed out. Last error: {last_error}")
