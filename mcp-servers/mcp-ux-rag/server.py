"""
MCP UX RAG Server - RAG service for UX/UI design patterns.

Provides design pattern knowledge from:
- Shadcn/ui components
- Tailwind CSS utilities
- Radix UI primitives
- Material Design guidelines
- Nielsen Norman Group (NNG) principles
- Apple Human Interface Guidelines (HIG)

Also integrates with repo-specific RAG for context.
"""
import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("mcp-ux-rag")

# Add backend to path for rag_service import
BACKEND_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend")
)
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

# Design pattern knowledge base
UX_PATTERNS = {
    "shadcn": {
        "description": "Shadcn/ui - Beautifully designed components",
        "principles": [
            "Copy and paste components - own your code",
            "Built on Radix UI primitives",
            "Tailwind CSS for styling",
            "Dark mode support out of the box",
            "Accessible by default (ARIA compliant)",
            "Composable and customizable"
        ],
        "components": [
            "Button", "Card", "Dialog", "Dropdown", "Input", "Select",
            "Tabs", "Toast", "Tooltip", "Sheet", "Command", "Calendar"
        ]
    },
    "tailwind": {
        "description": "Tailwind CSS - Utility-first CSS framework",
        "principles": [
            "Utility-first approach",
            "Responsive design with breakpoints (sm, md, lg, xl, 2xl)",
            "Dark mode with 'dark:' prefix",
            "Arbitrary values with square brackets [value]",
            "Component extraction with @apply",
            "JIT (Just-In-Time) compilation"
        ],
        "utilities": {
            "spacing": "p-4, m-2, gap-4, space-y-2",
            "flex": "flex, flex-col, items-center, justify-between",
            "grid": "grid, grid-cols-3, col-span-2",
            "colors": "bg-primary, text-muted-foreground",
            "borders": "rounded-lg, border, shadow-sm"
        }
    },
    "radix": {
        "description": "Radix UI - Low-level UI primitives",
        "principles": [
            "Unstyled, accessible components",
            "Compound component pattern",
            "Controlled and uncontrolled modes",
            "Full keyboard navigation",
            "Focus management",
            "Screen reader support"
        ]
    },
    "material_design": {
        "description": "Google Material Design guidelines",
        "principles": [
            "Material is the metaphor (tactile surfaces)",
            "Bold, graphic, intentional typography",
            "Motion provides meaning",
            "Adaptive design across devices",
            "8dp grid system",
            "Elevation and shadows for hierarchy"
        ],
        "color_system": [
            "Primary and secondary colors",
            "Surface and background",
            "Error, warning, success states",
            "On-colors for text contrast"
        ]
    },
    "nng": {
        "description": "Nielsen Norman Group - UX research principles",
        "heuristics": [
            "1. Visibility of system status",
            "2. Match between system and real world",
            "3. User control and freedom",
            "4. Consistency and standards",
            "5. Error prevention",
            "6. Recognition rather than recall",
            "7. Flexibility and efficiency of use",
            "8. Aesthetic and minimalist design",
            "9. Help users recognize and recover from errors",
            "10. Help and documentation"
        ],
        "principles": [
            "Progressive disclosure",
            "Fitts's Law (target size and distance)",
            "Miller's Law (7±2 items)",
            "Peak-end rule for experience design",
            "F-pattern and Z-pattern reading"
        ]
    },
    "apple_hig": {
        "description": "Apple Human Interface Guidelines",
        "principles": [
            "Clarity - text is legible, icons precise",
            "Deference - UI helps, doesn't compete",
            "Depth - visual layers, realistic motion",
            "Direct manipulation",
            "Feedback and responsiveness",
            "User control"
        ],
        "ios_specific": [
            "Safe areas for notch/home indicator",
            "Navigation patterns (tab bar, nav bar)",
            "Haptic feedback",
            "SF Symbols for icons",
            "Dynamic Type for accessibility"
        ],
        "macos_specific": [
            "Menu bar integration",
            "Dock and window management",
            "Keyboard shortcuts",
            "Drag and drop"
        ]
    }
}


class UxRagServer:
    """MCP-compatible RAG server for UX/UI patterns + repo context."""
    
    def __init__(self, docs_path: Optional[str] = None):
        self.docs_path = docs_path or os.path.join(os.path.dirname(__file__), "docs")
        self.patterns = UX_PATTERNS
        self._rag_service = None
        logger.info("UX RAG Server initialized")
    
    def _get_rag_service(self):
        """Lazy load rag_service."""
        if self._rag_service is None:
            try:
                from core.rag_service import get_rag_service
                self._rag_service = get_rag_service()
            except Exception as e:
                logger.warning(f"Could not load rag_service: {e}")
        return self._rag_service
    
    def query(self, query: str, top_k: int = 5, repo_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query for UX patterns + repo context.
        
        Combines:
        1. Pattern knowledge (Shadcn, Tailwind, etc.)
        2. Repo-specific code from rag_service
        """
        results = []
        query_lower = query.lower()
        
        # 1. Query pattern knowledge
        for category, data in self.patterns.items():
            score = 0
            
            if category in query_lower:
                score += 10
            
            if any(word in data.get("description", "").lower() for word in query_lower.split()):
                score += 5
            
            for key in ["principles", "heuristics", "components"]:
                if key in data:
                    items = data[key]
                    if isinstance(items, list):
                        for item in items:
                            if any(word in item.lower() for word in query_lower.split() if len(word) > 3):
                                score += 2
            
            if score > 0:
                results.append({
                    "category": category,
                    "score": score,
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                    "metadata": {"type": "ux_pattern", "source": category}
                })
        
        # 2. Query repo-specific code (if repo_filter provided)
        rag = self._get_rag_service()
        if rag and repo_filter:
            try:
                # Search for UI/UX related code in the repo
                ux_query = f"UI component {query}"
                repo_results = rag.query(ux_query, top_k=top_k, repo_filter=repo_filter)
                
                for r in repo_results:
                    results.append({
                        "category": "repo_code",
                        "score": 8,  # High priority for actual repo code
                        "content": r.get("content", ""),
                        "metadata": {
                            "type": "repo_code",
                            "source": r.get("metadata", {}).get("file", "unknown"),
                            "repo": repo_filter
                        }
                    })
            except Exception as e:
                logger.warning(f"Repo RAG query failed: {e}")
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def get_pattern(self, category: str) -> Optional[Dict[str, Any]]:
        """Get a specific pattern category."""
        return self.patterns.get(category)
    
    def get_all_patterns(self) -> Dict[str, Any]:
        """Get all pattern categories."""
        return self.patterns
    
    def get_design_recommendations(self, context: str, repo_filter: Optional[str] = None) -> str:
        """Generate design recommendations based on context + repo."""
        recommendations = []
        
        # Include repo-specific patterns if available
        if repo_filter:
            rag = self._get_rag_service()
            if rag:
                try:
                    repo_results = rag.query("UI style component css", top_k=3, repo_filter=repo_filter)
                    if repo_results:
                        recommendations.append("## 프로젝트 기존 UI 패턴")
                        for r in repo_results:
                            file_path = r.get("metadata", {}).get("file", "")
                            recommendations.append(f"- `{file_path}`")
                        recommendations.append("")
                except Exception as e:
                    logger.warning(f"Repo context failed: {e}")
        
        # Mobile context
        if any(word in context.lower() for word in ["mobile", "ios", "android", "app"]):
            recommendations.append("## Mobile Design")
            recommendations.append("- Follow Apple HIG / Material Design guidelines")
            recommendations.append("- Use touch-friendly tap targets (44x44pt minimum)")
            recommendations.append("- Consider safe areas for notches")
            recommendations.append("- Implement haptic feedback for actions")
        
        # Web context
        if any(word in context.lower() for word in ["web", "website", "dashboard"]):
            recommendations.append("\n## Web Design")
            recommendations.append("- Use Shadcn/ui components with Tailwind")
            recommendations.append("- Implement responsive breakpoints")
            recommendations.append("- Follow NNG heuristics for usability")
            recommendations.append("- Dark mode support recommended")
        
        # Accessibility
        recommendations.append("\n## Accessibility")
        recommendations.append("- Use Radix UI primitives for ARIA compliance")
        recommendations.append("- Ensure keyboard navigation")
        recommendations.append("- Provide focus indicators")
        recommendations.append("- Test with screen readers")
        
        return "\n".join(recommendations)


# MCP Server entry point
def create_server():
    """Create and return the MCP server instance."""
    return UxRagServer()


if __name__ == "__main__":
    # Simple test
    server = create_server()
    results = server.query("button component accessibility", repo_filter="RemoteDeveloper")
    for r in results:
        print(f"{r['category']}: score={r['score']}")
