from typing import Dict, Any, Optional
import json
import time
import logging
from agents.base import AgentStrategy
from core.llm import LLMService
from core.prompt_manager import PromptManager
from core.metrics_service import MetricsService

logger = logging.getLogger("agents")
llm_service = LLMService()
prompt_manager = PromptManager()
metrics_service = MetricsService()

class EvaluationAgent(AgentStrategy):
    @property
    def name(self) -> str:
        return "EVALUATION"
    
    @property
    def display_name(self) -> str:
        return "작업 평가 에이전트"
    
    @property
    def prompt_template(self) -> str:
        return prompt_manager.get_prompt(self.name)
    
    @property
    def next_agent(self) -> Optional[str]:
        return None  # Last agent in pipeline
    
    def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        
        # Build pipeline summary from history
        history = event.get("history", [])
        data = event.get("data", {})
        
        pipeline_summary = {
            "task": event.get("task", {}).get("original_prompt", ""),
            "stages_completed": [h.get("stage") for h in history],
            "outputs": {
                "requirement": data.get("requirement", "")[:200] if data.get("requirement") else "",
                "plan": data.get("plan", "")[:200] if data.get("plan") else "",
                "code": data.get("code", "")[:200] if data.get("code") else "",
                "test_results": data.get("test_results", "")[:200] if data.get("test_results") else "",
                "documentation": data.get("documentation", "")[:200] if data.get("documentation") else "",
            }
        }
        
        formatted_prompt = self.prompt_template.format(pipeline_summary=json.dumps(pipeline_summary, ensure_ascii=False))
        
        try:
            response = llm_service.chat_completion(formatted_prompt, "파이프라인 결과를 평가해주세요.", json_mode=True)
            result = json.loads(response)
            
            achievement_score = result.get("achievement_score", 0)
            agent_scores = result.get("agent_scores", {})
            improvements = result.get("improvements", [])
            
            # Record metrics for each agent
            for agent_name, score in agent_scores.items():
                success = score >= 70  # Consider 70+ as success
                duration = int((time.time() - start_time) * 1000 / max(len(agent_scores), 1))
                metrics_service.record_task(agent_name, success, duration)
            
            # Store improvement suggestions
            for improvement in improvements:
                metrics_service.store_improvement(improvement)
            
            output = f"[평가 완료]\n- 성취도: {achievement_score}/100\n- 개선점: {len(improvements)}개"
            
        except json.JSONDecodeError:
            output = f"[평가 오류] JSON 파싱 실패"
            achievement_score = 0
        except Exception as e:
            output = f"[평가 오류] {str(e)}"
            logger.error(f"Evaluation Agent failed: {e}")
            achievement_score = 0
        
        event["data"]["evaluation"] = output
        event["data"]["achievement_score"] = achievement_score
        return event
