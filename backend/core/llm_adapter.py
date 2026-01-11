"""
LLM Adapter Module - Abstraction layer for multiple LLM backends.
Supports OpenAI API, Claude CLI, and Cursor CLI.
"""
import os
import re
import json
import subprocess
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

logger = logging.getLogger("llm_adapter")


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter name for identification."""
        pass
    
    @abstractmethod
    def generate(self, 
                 system_prompt: str, 
                 user_prompt: str, 
                 json_mode: bool = False) -> str:
        """Generate a response from the LLM."""
        pass
    
    def extract_json(self, text: str) -> str:
        """Extract JSON from text, removing markdown code blocks."""
        pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        
        json_pattern = r'\{[\s\S]*\}'
        match = re.search(json_pattern, text)
        if match:
            return match.group(0)
        
        return text


class OpenAIAdapter(LLMAdapter):
    """OpenAI API adapter."""
    
    def __init__(self):
        from openai import OpenAI
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
        self.model = "gpt-4o"
    
    @property
    def name(self) -> str:
        return "openai"
    
    def generate(self, 
                 system_prompt: str, 
                 user_prompt: str, 
                 json_mode: bool = False) -> str:
        if not self.client:
            return '{"error": "OpenAI API Key not configured."}'
        
        # OpenAI requires "json" in prompt for json_mode
        if json_mode and "json" not in system_prompt.lower() and "json" not in user_prompt.lower():
            user_prompt = f"{user_prompt}\n\nRespond in JSON format."
        
        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            
            if json_mode:
                content = self.extract_json(content)
            
            return content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            if json_mode:
                return json.dumps({"error": str(e)})
            return f"Error: {str(e)}"


class ClaudeCliAdapter(LLMAdapter):
    """Claude CLI adapter using the `claude` command."""
    
    @property
    def name(self) -> str:
        return "claude_cli"
    
    def generate(self, 
                 system_prompt: str, 
                 user_prompt: str, 
                 json_mode: bool = False) -> str:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        if json_mode:
            full_prompt += "\n\nRespond with valid JSON only."
        
        try:
            # Use claude CLI with --print flag for non-interactive mode
            result = subprocess.run(
                ["claude", "--print", full_prompt],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                logger.error(f"Claude CLI error: {result.stderr}")
                return f"Error: {result.stderr}"
            
            content = result.stdout.strip()
            
            if json_mode:
                content = self.extract_json(content)
            
            return content
            
        except FileNotFoundError:
            logger.error("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
            return '{"error": "Claude CLI not installed"}'
        except subprocess.TimeoutExpired:
            logger.error("Claude CLI timeout")
            return '{"error": "Claude CLI timeout"}'
        except Exception as e:
            logger.error(f"Claude CLI failed: {e}")
            return f"Error: {str(e)}"


class CursorCliAdapter(LLMAdapter):
    """Cursor CLI adapter using the `cursor` command."""
    
    @property
    def name(self) -> str:
        return "cursor_cli"
    
    def generate(self, 
                 system_prompt: str, 
                 user_prompt: str, 
                 json_mode: bool = False) -> str:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        if json_mode:
            full_prompt += "\n\nRespond with valid JSON only."
        
        try:
            # Cursor CLI with message flag
            result = subprocess.run(
                ["cursor", "--message", full_prompt],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                logger.error(f"Cursor CLI error: {result.stderr}")
                return f"Error: {result.stderr}"
            
            content = result.stdout.strip()
            
            if json_mode:
                content = self.extract_json(content)
            
            return content
            
        except FileNotFoundError:
            logger.error("Cursor CLI not found. Enable via Cursor app: Command Palette > 'Install cursor command'")
            return '{"error": "Cursor CLI not installed"}'
        except subprocess.TimeoutExpired:
            logger.error("Cursor CLI timeout")
            return '{"error": "Cursor CLI timeout"}'
        except Exception as e:
            logger.error(f"Cursor CLI failed: {e}")
            return f"Error: {str(e)}"


# Adapter registry
ADAPTER_REGISTRY: Dict[str, type] = {
    "openai": OpenAIAdapter,
    "claude_cli": ClaudeCliAdapter,
    "cursor_cli": CursorCliAdapter,
}

def get_adapter(adapter_name: str) -> LLMAdapter:
    """Get an adapter instance by name."""
    adapter_class = ADAPTER_REGISTRY.get(adapter_name, OpenAIAdapter)
    return adapter_class()
