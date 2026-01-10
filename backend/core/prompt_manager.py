import os
import yaml
import logging

logger = logging.getLogger("ai_dev_team")

class PromptManager:
    _instance = None
    _prompts = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance.load_prompts()
        return cls._instance
    
    def load_prompts(self):
        """Load prompts from YAML file."""
        # Assume prompts.yaml is in backend/prompts.yaml or sibling to this file
        # We need to find the file relative to backend root
        import sys
        
        # Try to locate prompts.yaml
        possible_paths = [
            "prompts.yaml",
            "backend/prompts.yaml",
            "../prompts.yaml"
        ]
        
        yaml_path = None
        for path in possible_paths:
            if os.path.exists(path):
                yaml_path = path
                break
        
        if not yaml_path:
            logger.warning("prompts.yaml not found. Using empty prompts.")
            return

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                self._prompts = yaml.safe_load(f)
            logger.info(f"Loaded prompts from {yaml_path}")
        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")

    def get_prompt(self, agent_name: str) -> str:
        """Get prompt template for an agent."""
        return self._prompts.get(agent_name, "")

    def reload(self):
        """Force reload prompts."""
        self.load_prompts()
