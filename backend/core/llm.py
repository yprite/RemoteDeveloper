import os
import json
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI
from core.logging_config import logger

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables. LLM calls will fail.")
            self.client = OpenAI(api_key="missing_key")
        else:
            self.client = OpenAI(api_key=self.api_key)
        self.default_model = "gpt-4o"

    def extract_json(self, text: str) -> str:
        """Extract JSON from text, removing markdown code blocks if present."""
        # Remove ```json ... ``` blocks
        pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        
        # Try to find JSON object directly
        json_pattern = r'\{[\s\S]*\}'
        match = re.search(json_pattern, text)
        if match:
            return match.group(0)
        
        return text

    def chat_completion(self, 
                        system_prompt: str, 
                        user_prompt: str, 
                        model: Optional[str] = None,
                        json_mode: bool = False) -> str:
        
        if not self.api_key:
            return '{"error": "OpenAI API Key not configured."}'

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
            content = response.choices[0].message.content
            
            # Clean up response if JSON mode
            if json_mode:
                content = self.extract_json(content)
            
            return content
        except Exception as e:
            logger.error(f"LLM Call failed: {e}")
            if json_mode:
                return json.dumps({"error": str(e)})
            return f"Error executing LLM request: {str(e)}"
