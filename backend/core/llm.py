import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from core.logging_config import logger

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables. LLM calls will fail.")
            # Prevent OpenAI client crash on missing key by using a dummy if needed, 
            # or just don't init client yet if the library supports it. 
            # OpenAI python client requires api_key. We'll pass a dummy to allow startup.
            self.client = OpenAI(api_key="missing_key")
        else:
            self.client = OpenAI(api_key=self.api_key)
        self.default_model = "gpt-4o" # or gpt-4-turbo

    def chat_completion(self, 
                        system_prompt: str, 
                        user_prompt: str, 
                        model: Optional[str] = None,
                        json_mode: bool = False) -> str:
        
        if not self.api_key:
            return "Error: OpenAI API Key not configured."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            kwargs = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": 0.7
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Call failed: {e}")
            return f"Error executing LLM request: {str(e)}"
