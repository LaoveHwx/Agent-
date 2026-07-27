from openai import OpenAI

from utils.env_util import api_key, base_url, model_name
from utils.logger import setup_logger


logger = setup_logger(__name__)


def _client() -> OpenAI | None:
    if not api_key or not base_url:
        return None
    return OpenAI(api_key=api_key, base_url=base_url)


def chat_completion(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str | None:
    client = _client()
    if client is None or not model_name:
        logger.info("llm chat skipped: API_KEY, BASE_URL or MODEL_NAME is not configured")
        return None

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content
