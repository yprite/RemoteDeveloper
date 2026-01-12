"""
MCP Client Service - Connects to local MCP RAG servers.

Provides interface for agents to query:
- mcp-ux-rag: UX/UI design patterns
- mcp-arch-rag: Architecture patterns
"""
import os
import sys
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("mcp_client")

# Add mcp-servers to path dynamically
MCP_SERVERS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers")
)


class McpClient:
    """Client for connecting to local MCP RAG servers."""
    
    def __init__(self):
        self._servers = {}
        self._load_servers()
    
    def _load_servers(self):
        """Load available MCP servers."""
        # Add mcp-servers to path if not already there
        if MCP_SERVERS_PATH not in sys.path:
            sys.path.insert(0, MCP_SERVERS_PATH)
        
        # Try to load UX RAG server
        try:
            from importlib import import_module
            ux_module = import_module("mcp-ux-rag.server")
            self._servers["mcp-ux-rag"] = ux_module.create_server()
            logger.info("Loaded mcp-ux-rag server")
        except Exception as e:
            logger.warning(f"Failed to load mcp-ux-rag: {e}")
        
        # Try to load Architecture RAG server
        try:
            from importlib import import_module
            arch_module = import_module("mcp-arch-rag.server")
            self._servers["mcp-arch-rag"] = arch_module.create_server()
            logger.info("Loaded mcp-arch-rag server")
        except Exception as e:
            logger.warning(f"Failed to load mcp-arch-rag: {e}")
    
    def query(self, server_name: str, query: str, top_k: int = 5, repo_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query a specific MCP server.
        
        Args:
            server_name: Name of the server (e.g., 'mcp-ux-rag')
            query: Search query
            top_k: Number of results to return
            repo_filter: Optional repo name for context-aware queries
        
        Returns:
            List of matching patterns/documents
        """
        server = self._servers.get(server_name)
        if not server:
            logger.error(f"MCP server not found: {server_name}")
            return []
        
        try:
            return server.query(query, top_k=top_k, repo_filter=repo_filter)
        except Exception as e:
            logger.error(f"MCP query failed ({server_name}): {e}")
            return []
    
    def get_recommendations(self, server_name: str, context: str, repo_filter: Optional[str] = None) -> str:
        """
        Get recommendations from a specific MCP server.
        
        Args:
            server_name: Name of the server
            context: Context for generating recommendations
            repo_filter: Optional repo name for context-aware recommendations
        
        Returns:
            Recommendation text
        """
        server = self._servers.get(server_name)
        if not server:
            logger.error(f"MCP server not found: {server_name}")
            return ""
        
        try:
            if server_name == "mcp-ux-rag":
                return server.get_design_recommendations(context, repo_filter=repo_filter)
            elif server_name == "mcp-arch-rag":
                return server.get_architecture_recommendations(context, repo_filter=repo_filter)
            else:
                return ""
        except Exception as e:
            logger.error(f"MCP get_recommendations failed ({server_name}): {e}")
            return ""
    
    def get_pattern(self, server_name: str, category: str) -> Optional[Dict[str, Any]]:
        """Get a specific pattern from a server."""
        server = self._servers.get(server_name)
        if not server:
            return None
        
        try:
            return server.get_pattern(category)
        except Exception as e:
            logger.error(f"MCP get_pattern failed: {e}")
            return None
    
    def list_servers(self) -> List[str]:
        """List available MCP servers."""
        return list(self._servers.keys())
    
    def is_server_available(self, server_name: str) -> bool:
        """Check if a server is available."""
        return server_name in self._servers


# Singleton instance
_mcp_client: Optional[McpClient] = None


def get_mcp_client() -> McpClient:
    """Get the singleton MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = McpClient()
    return _mcp_client
