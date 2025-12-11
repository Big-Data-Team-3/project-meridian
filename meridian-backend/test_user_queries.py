"""
Comprehensive User Query Test Suite for Meridian Agents
Tests both chat API and direct agent calls with category-based testing and agent trace validation.
"""

import argparse
import asyncio
import httpx
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import uuid

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import intent classification (with fallback if not available)
try:
    from services.query_classifier import get_query_classifier
    from services.agent_orchestrator import get_agent_orchestrator
    from models.query_intent import QueryIntent
    INTENT_CLASSIFICATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Intent classification not available: {e}")
    INTENT_CLASSIFICATION_AVAILABLE = False

# Agent name mapping from workflow config names to actual agent names in traces
AGENT_NAME_MAP = {
    "market": "Market Analyst",
    "information": "Information Analyst",
    "fundamentals": "Fundamentals Analyst",
    "bull_researcher": "Bull Researcher",
    "bear_researcher": "Bear Researcher",
    "research_manager": "Research Manager",
    "trader": "Trader",
    "risky_analyst": "Risky Analyst",
    "neutral_analyst": "Neutral Analyst",
    "safe_analyst": "Safe Analyst",
    "risk_judge": "Risk Manager",
}

def map_agent_names(workflow_agents: List[str]) -> List[str]:
    """Map workflow agent names to actual agent trace names."""
    return [AGENT_NAME_MAP.get(agent, agent.replace("_", " ").title()) for agent in workflow_agents]

@dataclass
class ExpectedAgentTrace:
    """Expected agent trace for a query."""
    intent: str
    workflow_type: str
    agents_called: List[str]  # Exact agents that should be called (actual agent names)
    agents_used: List[str]  # Agents from workflow config (workflow names)
    allow_extra_agents: bool = False  # Whether to allow additional agents

@dataclass
class TestThread:
    """Represents a conversation thread with multiple queries."""
    thread_id: str
    queries: List[str]
    description: str
    category: str  # Category name for filtering
    is_agentic_focus: bool = False
    expected_intents: Optional[List[str]] = None  # Expected intent for each query
    expected_traces: List[ExpectedAgentTrace] = field(default_factory=list)  # Expected agent traces

class MeridianTestSuite:
    """Test suite for Meridian backend and agents services."""
    
    def __init__(self, backend_url: str = "http://localhost:8000", agents_url: str = "http://localhost:8001", bearer_token: str = None):
        self.backend_url = backend_url.rstrip('/')
        self.agents_url = agents_url.rstrip('/')
        self.test_user_id = "test-user-12345"
        self.created_threads: List[str] = []
        self.bearer_token = bearer_token
        
        if not self.bearer_token:
            raise ValueError("Bearer token is required for authentication")
        
        # Initialize HTTP client with auth headers
        # Note: httpx.AsyncClient headers are set per-request, so we'll set them explicitly in each request
        self.client = httpx.AsyncClient(timeout=300.0)
        
        # Verify token format
        if not self.bearer_token.startswith("Bearer "):
            # Token should not include "Bearer " prefix - we'll add it in headers
            self.auth_header = {"Authorization": f"Bearer {self.bearer_token}"}
        else:
            # If user included "Bearer ", use as-is
            self.auth_header = {"Authorization": self.bearer_token}
        
        logger.debug(f"Initialized test suite with token: {self.bearer_token[:20]}...")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def authenticate_and_get_token(self) -> str:
        """Get bearer token for authentication."""
        return self.bearer_token
    
    async def create_thread(self, title: str = "Test Thread") -> str:
        """Create a new thread for testing."""
        try:
            # Log the request details for debugging
            logger.info(f"Creating thread with title: '{title}'")
            logger.debug(f"Using bearer token: {self.bearer_token[:20]}..." if self.bearer_token else "No token")
            
            response = await self.client.post(
                f"{self.backend_url}/api/threads",
                json={"title": title},
                headers=self.auth_header
            )
            response.raise_for_status()
            thread_data = response.json()
            thread_id = thread_data["thread_id"]
            self.created_threads.append(thread_id)
            logger.info(f"Successfully created thread: {thread_id} with title: '{title}'")
            return thread_id
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                if "detail" in error_body:
                    error_detail = f"HTTP {e.response.status_code}: {error_body['detail']}"
            except:
                error_detail = f"HTTP {e.response.status_code}: {e.response.text or str(e)}"
            logger.error(f"Failed to create thread '{title}': {error_detail}")
            logger.error(f"Response headers: {dict(e.response.headers)}")
            raise Exception(f"Failed to create thread: {error_detail}")
        except Exception as e:
            logger.error(f"Failed to create thread '{title}': {e}", exc_info=True)
            raise Exception(f"Failed to create thread: {str(e)}")
    
    async def send_chat_message(self, thread_id: str, message: str) -> Dict[str, Any]:
        """Send a chat message and get response."""
        try:
            logger.debug(f"Sending chat message to thread {thread_id}")
            response = await self.client.post(
                f"{self.backend_url}/api/chat",
                json={"thread_id": thread_id, "message": message},
                headers=self.auth_header
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                if "detail" in error_body:
                    error_detail = f"HTTP {e.response.status_code}: {error_body['detail']}"
            except:
                error_detail = f"HTTP {e.response.status_code}: {e.response.text or str(e)}"
            logger.error(f"Chat API error for thread {thread_id}: {error_detail}")
            return {"error": error_detail, "thread_id": thread_id, "message": message}
        except Exception as e:
            logger.error(f"Chat API error for thread {thread_id}: {e}", exc_info=True)
            return {"error": str(e), "thread_id": thread_id, "message": message}
    
    async def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Retrieve all messages for a thread."""
        try:
            response = await self.client.get(
                f"{self.backend_url}/api/threads/{thread_id}/messages",
                headers=self.auth_header
            )
            response.raise_for_status()
            data = response.json()
            if data is None:
                logger.warning(f"Response data is None for thread {thread_id}")
                return []
            if not isinstance(data, dict):
                logger.warning(f"Response data is not a dict for thread {thread_id}: {type(data)}")
                return []
            return data.get("messages", []) if data else []
        except Exception as e:
            logger.error(f"Failed to get messages for thread {thread_id}: {e}", exc_info=True)
            return []
    
    async def get_assistant_message(self, thread_id: str, query_index: int = -1) -> Optional[Dict]:
        """Retrieve the assistant message for a thread (by index, default is last)."""
        messages = await self.get_thread_messages(thread_id)
        if not messages:
            logger.debug(f"No messages found for thread {thread_id}")
            return None
        assistant_messages = [m for m in messages if m and isinstance(m, dict) and m.get("role") == "assistant"]
        if assistant_messages:
            # Return the message at the specified index (default: last one)
            index = query_index if query_index >= 0 else len(assistant_messages) + query_index
            if 0 <= index < len(assistant_messages):
                return assistant_messages[index]
        logger.debug(f"No assistant messages found for thread {thread_id} (total messages: {len(messages)})")
        return None
    
    def validate_agent_trace(
        self,
        expected: ExpectedAgentTrace,
        actual_metadata: Dict[str, Any],
        chat_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate actual agent trace against expected."""
        if not actual_metadata:
            actual_metadata = {}
        agent_trace = actual_metadata.get("agent_trace", {}) if actual_metadata else {}
        
        # For direct_response workflows (like simple_chat), metadata might be null/empty
        # This is expected - they don't go through agent service, so no agent_trace exists
        if expected.workflow_type == "direct_response":
            # For direct_response, we only care about agents not being called
            # Intent and workflow are validated separately via intent_classification
            actual_agents_called = agent_trace.get("agents_called", []) if agent_trace else []
            actual_agents_used = actual_metadata.get("agents_used", []) if actual_metadata else []
            
            # If no metadata exists, that's fine for direct_response - check chat_response for intent
            intent_from_trace = agent_trace.get("intent") if agent_trace else None
            workflow_from_trace = agent_trace.get("workflow") if agent_trace else None
            
            # Fallback to chat_response if available
            if not intent_from_trace and chat_response:
                intent_from_trace = chat_response.get("intent")
            if not workflow_from_trace and chat_response:
                workflow_from_trace = chat_response.get("workflow")
            
            results = {
                "intent_match": (intent_from_trace == expected.intent) if intent_from_trace else True,  # Accept if no trace but workflow is direct_response
                "workflow_match": (workflow_from_trace == expected.workflow_type) if workflow_from_trace else True,  # Accept if no trace but workflow is direct_response
                "agents_called_match": len(actual_agents_called) == 0,  # Must be empty for direct_response
                "agents_used_match": len(actual_agents_used) == 0,  # Must be empty for direct_response
                "actual_agents_called": actual_agents_called,
                "actual_agents_used": actual_agents_used,
                "expected_agents_called": expected.agents_called,
                "expected_agents_used": expected.agents_used,
                "errors": []
            }
        else:
            # For agentic workflows, we expect agent_trace to exist
            results = {
                "intent_match": agent_trace.get("intent") == expected.intent if agent_trace else False,
                "workflow_match": agent_trace.get("workflow") == expected.workflow_type if agent_trace else False,
                "agents_called_match": False,
                "agents_used_match": False,
                "actual_agents_called": agent_trace.get("agents_called", []) if agent_trace else [],
                "actual_agents_used": actual_metadata.get("agents_used", []) if actual_metadata else [],
                "expected_agents_called": expected.agents_called,
                "expected_agents_used": expected.agents_used,
                "errors": []
            }
        
        # Check agents_called (exact match unless allow_extra_agents)
        actual_called = set(results["actual_agents_called"])
        expected_called = set(expected.agents_called)
        
        if expected.allow_extra_agents:
            results["agents_called_match"] = expected_called.issubset(actual_called)
            if not results["agents_called_match"]:
                missing = expected_called - actual_called
                results["errors"].append(
                    f"Missing expected agents: {sorted(missing)}"
                )
        else:
            results["agents_called_match"] = actual_called == expected_called
            if not results["agents_called_match"]:
                missing = expected_called - actual_called
                extra = actual_called - expected_called
                if missing:
                    results["errors"].append(f"Missing agents: {sorted(missing)}")
                if extra:
                    results["errors"].append(f"Unexpected agents: {sorted(extra)}")
        
        # Check agents_used (should match workflow config)
        results["agents_used_match"] = (
            set(results["actual_agents_used"]) == set(expected.agents_used)
        )
        if not results["agents_used_match"]:
            results["errors"].append(
                f"Agents used mismatch: expected {expected.agents_used}, "
                f"got {results['actual_agents_used']}"
            )
        
        results["all_match"] = all([
            results["intent_match"],
            results["workflow_match"],
            results["agents_called_match"],
            results["agents_used_match"]
        ])
        
        return results
    
    async def call_agents_analyze(self, company: str, date: str, context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Call the agents analysis endpoint directly."""
        try:
            payload = {
                "company_name": company,
                "trade_date": date
            }
            if context:
                payload["conversation_context"] = context
            
            response = await self.client.post(
                f"{self.backend_url}/api/agents/analyze",
                json=payload,
                headers=self.auth_header
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Agents API error: {e}")
            return {"error": str(e), "company": company, "date": date}
    
    def classify_query_intent(self, query: str) -> Dict[str, Any]:
        """Classify query intent and get workflow configuration."""
        if not INTENT_CLASSIFICATION_AVAILABLE:
            return {
                "intent": "unknown",
                "workflow": "unknown",
                "error": "Intent classification not available"
            }
        
        try:
            orchestrator = get_agent_orchestrator()
            
            intent, workflow = orchestrator.classify_and_get_workflow(query)
            
            return {
                "intent": intent.value if hasattr(intent, 'value') else str(intent),
                "workflow_type": workflow.workflow_type,
                "agents": workflow.agents,
                "timeout_seconds": workflow.timeout_seconds
            }
        except Exception as e:
            logger.error(f"Intent classification error: {e}", exc_info=True)
            return {
                "intent": "error",
                "workflow": "error",
                "error": str(e)
            }
    
    def generate_test_queries(self, category_filter: Optional[str] = None) -> List[TestThread]:
        """Generate comprehensive test queries organized by category."""
        
        test_threads = []
        
        # Category: simple_chat - No agents, direct OpenAI responses
        # Simple queries that test Meridian's identity awareness and basic conversational ability
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "Hello! What are you?",
                "What can you help me with?",
                "Tell me about yourself",
                "What is Meridian?",
                "How can you help me with investing?"
            ],
            description="Simple chat - no agents",
            category="simple_chat",
            is_agentic_focus=False,
            expected_intents=["simple_chat", "simple_chat", "simple_chat", "simple_chat", "simple_chat"],
            expected_traces=[
                ExpectedAgentTrace(
                    intent="simple_chat",
                    workflow_type="direct_response",
                    agents_called=[],
                    agents_used=[]
                ),
                ExpectedAgentTrace(
                    intent="simple_chat",
                    workflow_type="direct_response",
                    agents_called=[],
                    agents_used=[]
                ),
                ExpectedAgentTrace(
                    intent="simple_chat",
                    workflow_type="direct_response",
                    agents_called=[],
                    agents_used=[]
                ),
                ExpectedAgentTrace(
                    intent="simple_chat",
                    workflow_type="direct_response",
                    agents_called=[],
                    agents_used=[]
                ),
                ExpectedAgentTrace(
                    intent="simple_chat",
                    workflow_type="direct_response",
                    agents_called=[],
                    agents_used=[]
                )
            ]
        ))
        
        # Category: basic_info - Single agent (information)
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "What is Apple stock trading at today?",
                "What is Tesla's business?",
                "What's Microsoft's main products?",
                "What is NVIDIA doing?",
                "What's Amazon's business model?"
            ],
            description="Basic info - information agent",
            category="basic_info",
            is_agentic_focus=True,
            expected_intents=["basic_info", "basic_info", "basic_info", "basic_info", "basic_info"],
            expected_traces=[
                ExpectedAgentTrace(
                    intent="basic_info",
                    workflow_type="single_agent",
                    agents_called=["Information Analyst"],
                    agents_used=["information"]
                ),
                ExpectedAgentTrace(
                    intent="basic_info",
                    workflow_type="single_agent",
                    agents_called=["Information Analyst"],
                    agents_used=["information"]
                ),
                ExpectedAgentTrace(
                    intent="basic_info",
                    workflow_type="single_agent",
                    agents_called=["Information Analyst"],
                    agents_used=["information"]
                ),
                ExpectedAgentTrace(
                    intent="basic_info",
                    workflow_type="single_agent",
                    agents_called=["Information Analyst"],
                    agents_used=["information"]
                ),
                ExpectedAgentTrace(
                    intent="basic_info",
                    workflow_type="single_agent",
                    agents_called=["Information Analyst"],
                    agents_used=["information"]
                )
            ]
        ))
        
        # Category: technical_analysis - Single agent (market)
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "Run a market analysis on AAPL",
                "Apple stock technical analysis",
                "What's the technical outlook for Tesla?",
                "Show me technical indicators for Microsoft",
                "Technical chart analysis for NVIDIA"
            ],
            description="Technical analysis - market agent",
            category="technical_analysis",
            is_agentic_focus=True,
            expected_intents=["technical_analysis", "technical_analysis", "technical_analysis", "technical_analysis", "technical_analysis"],
            expected_traces=[
                ExpectedAgentTrace(
                    intent="technical_analysis",
                    workflow_type="single_agent",
                    agents_called=["Market Analyst"],
                    agents_used=["market"]
                ),
                ExpectedAgentTrace(
                    intent="technical_analysis",
                    workflow_type="single_agent",
                    agents_called=["Market Analyst"],
                    agents_used=["market"]
                ),
                ExpectedAgentTrace(
                    intent="technical_analysis",
                    workflow_type="single_agent",
                    agents_called=["Market Analyst"],
                    agents_used=["market"]
                ),
                ExpectedAgentTrace(
                    intent="technical_analysis",
                    workflow_type="single_agent",
                    agents_called=["Market Analyst"],
                    agents_used=["market"]
                ),
                ExpectedAgentTrace(
                    intent="technical_analysis",
                    workflow_type="single_agent",
                    agents_called=["Market Analyst"],
                    agents_used=["market"]
                )
            ]
        ))
        
        # Category: fundamental_analysis - Single agent (fundamentals)
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "Analyze Apple's fundamentals",
                "Get fundamental data for Apple",
                "Tesla's financial health",
                "Microsoft's financial metrics",
                "NVIDIA's valuation analysis"
            ],
            description="Fundamental analysis - fundamentals agent",
            category="fundamental_analysis",
            is_agentic_focus=True,
            expected_intents=["fundamental_analysis", "fundamental_analysis", "fundamental_analysis", "fundamental_analysis", "fundamental_analysis"],
            expected_traces=[
                ExpectedAgentTrace(
                    intent="fundamental_analysis",
                    workflow_type="single_agent",
                    agents_called=["Fundamentals Analyst"],
                    agents_used=["fundamentals"]
                ),
                ExpectedAgentTrace(
                    intent="fundamental_analysis",
                    workflow_type="single_agent",
                    agents_called=["Fundamentals Analyst"],
                    agents_used=["fundamentals"]
                ),
                ExpectedAgentTrace(
                    intent="fundamental_analysis",
                    workflow_type="single_agent",
                    agents_called=["Fundamentals Analyst"],
                    agents_used=["fundamentals"]
                ),
                ExpectedAgentTrace(
                    intent="fundamental_analysis",
                    workflow_type="single_agent",
                    agents_called=["Fundamentals Analyst"],
                    agents_used=["fundamentals"]
                ),
                ExpectedAgentTrace(
                    intent="fundamental_analysis",
                    workflow_type="single_agent",
                    agents_called=["Fundamentals Analyst"],
                    agents_used=["fundamentals"]
                )
            ]
        ))
        
        # Category: market_overview - Multi-agent (market + information)
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "What are the major stock indices?",
                "What's the Dow Jones?",
                "Explain S&P 500",
                "What's NASDAQ?",
                "How do stock indices work?"
            ],
            description="Market overview - market and information agents",
            category="market_overview",
            is_agentic_focus=True,
            expected_intents=["market_overview", "market_overview", "market_overview", "market_overview", "market_overview"],
            expected_traces=[
                ExpectedAgentTrace(
                    intent="market_overview",
                    workflow_type="multi_agent",
                    agents_called=["Market Analyst", "Information Analyst"],
                    agents_used=["market", "information"],
                    allow_extra_agents=True  # May include additional agents
                ),
                ExpectedAgentTrace(
                    intent="market_overview",
                    workflow_type="multi_agent",
                    agents_called=["Market Analyst", "Information Analyst"],
                    agents_used=["market", "information"],
                    allow_extra_agents=True
                ),
                ExpectedAgentTrace(
                    intent="market_overview",
                    workflow_type="multi_agent",
                    agents_called=["Market Analyst", "Information Analyst"],
                    agents_used=["market", "information"],
                    allow_extra_agents=True
                ),
                ExpectedAgentTrace(
                    intent="market_overview",
                    workflow_type="multi_agent",
                    agents_called=["Market Analyst", "Information Analyst"],
                    agents_used=["market", "information"],
                    allow_extra_agents=True
                ),
                ExpectedAgentTrace(
                    intent="market_overview",
                    workflow_type="multi_agent",
                    agents_called=["Market Analyst", "Information Analyst"],
                    agents_used=["market", "information"],
                    allow_extra_agents=True
                )
            ]
        ))
        
        # Category: comprehensive_analysis - Full workflow (multiple agents with debate and risk)
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "Should I buy Apple stock today?",
                "Is Tesla overvalued?",
                "Bull case for Tesla",
                "Risk assessment for Microsoft",
                "Comprehensive analysis of AMZN"
            ],
            description="Comprehensive analysis - full workflow",
            category="comprehensive_analysis",
            is_agentic_focus=True,
            expected_intents=["comprehensive_trade", "comprehensive_trade", "comprehensive_trade", "comprehensive_trade", "comprehensive_trade"],
            expected_traces=[
                ExpectedAgentTrace(
                    intent="comprehensive_trade",
                    workflow_type="full_workflow",
                    agents_called=["Market Analyst", "Fundamentals Analyst", "Information Analyst", "Risk Manager"],
                    agents_used=["market", "fundamentals", "information"],
                    allow_extra_agents=True  # Full workflow may include additional agents
                ),
                ExpectedAgentTrace(
                    intent="comprehensive_trade",
                    workflow_type="full_workflow",
                    agents_called=["Market Analyst", "Fundamentals Analyst", "Information Analyst", "Risk Manager"],
                    agents_used=["market", "fundamentals", "information"],
                    allow_extra_agents=True
                ),
                ExpectedAgentTrace(
                    intent="comprehensive_trade",
                    workflow_type="full_workflow",
                    agents_called=["Market Analyst", "Fundamentals Analyst", "Information Analyst", "Risk Manager"],
                    agents_used=["market", "fundamentals", "information"],
                    allow_extra_agents=True
                ),
                ExpectedAgentTrace(
                    intent="comprehensive_trade",
                    workflow_type="full_workflow",
                    agents_called=["Market Analyst", "Fundamentals Analyst", "Information Analyst", "Risk Manager"],
                    agents_used=["market", "fundamentals", "information"],
                    allow_extra_agents=True
                ),
                ExpectedAgentTrace(
                    intent="comprehensive_trade",
                    workflow_type="full_workflow",
                    agents_called=["Market Analyst", "Fundamentals Analyst", "Information Analyst", "Risk Manager"],
                    agents_used=["market", "fundamentals", "information"],
                    allow_extra_agents=True
                )
            ]
        ))
        
        # Category: mixed_conversation - Multi-turn with different intents
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "I'm new to investing. Can you help me get started?",
                "What are the different types of investments?",
                "How do I choose a good investment?",
                "What's diversification and why is it important?",
                "What's a good long-term investment strategy?"
            ],
            description="Mixed conversation - various intents",
            category="mixed_conversation",
            is_agentic_focus=True,
            expected_intents=["simple_chat", "basic_info", "comprehensive_trade", "basic_info", "comprehensive_trade"],
            expected_traces=[
                ExpectedAgentTrace(
                    intent="simple_chat",
                    workflow_type="direct_response",
                    agents_called=[],
                    agents_used=[]
                ),
                ExpectedAgentTrace(
                    intent="basic_info",
                    workflow_type="single_agent",
                    agents_called=["Information Analyst"],
                    agents_used=["information"]
                ),
                ExpectedAgentTrace(
                    intent="comprehensive_trade",
                    workflow_type="full_workflow",
                    agents_called=["Market Analyst", "Fundamentals Analyst", "Information Analyst", "Risk Manager"],
                    agents_used=["market", "fundamentals", "information"],
                    allow_extra_agents=True
                ),
                ExpectedAgentTrace(
                    intent="basic_info",
                    workflow_type="single_agent",
                    agents_called=["Information Analyst"],
                    agents_used=["information"]
                ),
                ExpectedAgentTrace(
                    intent="comprehensive_trade",
                    workflow_type="full_workflow",
                    agents_called=["Market Analyst", "Fundamentals Analyst", "Information Analyst", "Risk Manager"],
                    agents_used=["market", "fundamentals", "information"],
                    allow_extra_agents=True
                )
            ]
        ))
        
        # Filter by category if specified
        if category_filter:
            test_threads = [t for t in test_threads if t.category == category_filter]
            if not test_threads:
                logger.warning(f"No test threads found for category: {category_filter}")
        
        return test_threads
    
    async def run_thread_test(self, thread: TestThread) -> Dict[str, Any]:
        """Run a complete thread test with agent trace validation."""
        logger.info(f"Starting thread test: {thread.description} (category: {thread.category})")
        
        # Create thread with category name as the title
        thread_title = thread.category.replace("_", " ").title()  # e.g., "simple_chat" -> "Simple Chat"
        thread_id = await self.create_thread(thread_title)
        thread.thread_id = thread_id
        
        results = {
            "thread_id": thread_id,
            "category": thread.category,
            "description": thread.description,
            "is_agentic_focus": thread.is_agentic_focus,
            "queries": [],
            "total_queries": len(thread.queries),
            "validation_summary": {
                "total": len(thread.queries),
                "passed": 0,
                "failed": 0,
                "errors": []
            }
        }
        
        # Process each query in the thread (multi-turn context)
        for i, query in enumerate(thread.queries):
            try:
                logger.info(f"Processing query {i+1}/{len(thread.queries)}: {query[:50]}...")

                # Classify query intent
                intent_result = self.classify_query_intent(query)
                expected_intent = None
                if thread.expected_intents and i < len(thread.expected_intents):
                    expected_intent = thread.expected_intents[i]

                # Verify intent classification matches expected (if provided)
                intent_correct = None
                if expected_intent and intent_result and intent_result.get("intent") != "error":
                    intent_correct = (intent_result.get("intent") == expected_intent)
                    if not intent_correct:
                        logger.warning(
                            f"Intent mismatch for query '{query[:50]}...': "
                            f"expected {expected_intent}, got {intent_result.get('intent')}"
                        )

                # Send chat message
                chat_response = await self.send_chat_message(thread_id, query)

                # Check if there was an error in the chat response
                if chat_response and "error" in chat_response:
                    logger.error(f"Chat API returned error for query {i+1}: {chat_response.get('error')}")
                    assistant_message = None
                else:
                    # Wait for streaming to complete if needed (for agentic queries)
                    if chat_response and chat_response.get("use_streaming"):
                        logger.info(f"Waiting for streaming to complete for query {i+1}...")
                        # Wait longer for comprehensive workflows
                        wait_time = 10 if intent_result and intent_result.get("workflow_type") == "full_workflow" else 5
                        await asyncio.sleep(wait_time)
                    else:
                        # For non-streaming responses (like simple_chat), wait a bit for message to be saved
                        await asyncio.sleep(1.0)

                    # Retrieve the assistant message with metadata
                    assistant_message = await self.get_assistant_message(thread_id, query_index=-1)

                    # If message not found, try once more after a short delay
                    if not assistant_message:
                        logger.warning(f"Assistant message not found immediately for query {i+1}, retrying...")
                        await asyncio.sleep(1.0)
                        assistant_message = await self.get_assistant_message(thread_id, query_index=-1)

                # Validate agent trace
                validation_result = None
                expected_trace = thread.expected_traces[i] if i < len(thread.expected_traces) else None

                if expected_trace:
                    # For direct_response workflows, we can validate even without assistant_message metadata
                    # by using chat_response data
                    if assistant_message:
                        metadata = assistant_message.get("metadata", {}) if assistant_message else {}
                        if metadata is None:
                            metadata = {}
                    else:
                        # No assistant message, but for direct_response we can still validate
                        metadata = {}

                    # Pass chat_response for fallback validation (especially for direct_response)
                    validation_result = self.validate_agent_trace(expected_trace, metadata, chat_response)

                    if validation_result and validation_result.get("all_match"):
                        results["validation_summary"]["passed"] += 1
                        logger.info(f"✓ Query {i+1} passed agent trace validation")
                    else:
                        results["validation_summary"]["failed"] += 1
                        if validation_result and validation_result.get("errors"):
                            results["validation_summary"]["errors"].extend(validation_result["errors"])
                        # Log specific failures for debugging
                        if validation_result:
                            failures = []
                            if not validation_result.get("intent_match"):
                                failures.append("intent mismatch")
                            if not validation_result.get("workflow_match"):
                                failures.append("workflow mismatch")
                            if not validation_result.get("agents_called_match"):
                                failures.append("agents_called mismatch")
                            if not validation_result.get("agents_used_match"):
                                failures.append("agents_used mismatch")
                            logger.warning(
                                f"✗ Query {i+1} failed agent trace validation: {', '.join(failures)}"
                            )
                        else:
                            logger.warning(f"✗ Query {i+1} failed agent trace validation: no validation result")

                query_result = {
                    "query_number": i + 1,
                    "query": query,
                    "intent_classification": intent_result if intent_result else {},
                    "expected_intent": expected_intent,
                    "intent_correct": intent_correct,
                    "chat_response": chat_response if chat_response else {},
                    "expected_trace": expected_trace.__dict__ if expected_trace else None,
                    "actual_metadata": assistant_message.get("metadata", {}) if assistant_message else None,
                    "validation": validation_result,
                    "timestamp": datetime.now().isoformat()
                }

                results["queries"].append(query_result)

                # Small delay between queries to avoid rate limiting
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(f"Error processing query {i+1}: {e}", exc_info=True)
                # Add error to results
                query_result = {
                    "query_number": i + 1,
                    "query": query,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                results["queries"].append(query_result)
                results["validation_summary"]["failed"] += 1
                results["validation_summary"]["errors"].append(f"Query {i+1}: {str(e)}")
                continue
        
        logger.info(
            f"Completed thread test: {thread.description} - "
            f"{results['validation_summary']['passed']}/{results['validation_summary']['total']} passed"
        )
        return results
    
    async def run_full_test_suite(self, category_filter: Optional[str] = None) -> Dict[str, Any]:
        """Run the complete test suite, optionally filtered by category."""
        logger.info("Starting comprehensive Meridian test suite...")
        if category_filter:
            logger.info(f"Filtering by category: {category_filter}")
        
        start_time = datetime.now()
        test_threads = self.generate_test_queries(category_filter=category_filter)
        
        logger.info(f"Generated {len(test_threads)} test threads with {sum(len(t.queries) for t in test_threads)} total queries")
        
        results = {
            "test_suite_info": {
                "start_time": start_time.isoformat(),
                "total_threads": len(test_threads),
                "total_queries": sum(len(t.queries) for t in test_threads),
                "backend_url": self.backend_url,
                "agents_url": self.agents_url
            },
            "thread_results": []
        }
        
        # Run each thread test
        for i, thread in enumerate(test_threads):
            logger.info(f"Running thread {i+1}/{len(test_threads)}: {thread.description}")
            try:
                thread_result = await self.run_thread_test(thread)
                results["thread_results"].append(thread_result)
            except Exception as e:
                logger.error(f"Failed to run thread {thread.description}: {e}")
                results["thread_results"].append({
                    "thread_id": thread.thread_id,
                    "description": thread.description,
                    "error": str(e),
                    "total_queries": len(thread.queries)
                })
            
            # Progress update
            completed_queries = sum(len(r.get("queries", [])) for r in results["thread_results"] 
                                  if "queries" in r)
            logger.info(f"Progress: {completed_queries}/{results['test_suite_info']['total_queries']} queries completed")
        
        # Calculate final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        successful_threads = len([r for r in results["thread_results"] if "error" not in r])
        failed_threads = len([r for r in results["thread_results"] if "error" in r])
        
        total_chat_responses = sum(len(r.get("queries", [])) for r in results["thread_results"] 
                                 if "queries" in r)
        total_agent_responses = sum(1 for r in results["thread_results"] 
                                  if "queries" in r 
                                  for q in r["queries"] 
                                  if q.get("agent_response") and "error" not in q["agent_response"])
        
        # Calculate intent classification statistics
        total_intent_classifications = sum(1 for r in results["thread_results"] 
                                          if "queries" in r 
                                          for q in r["queries"] 
                                          if q.get("intent_classification") and q["intent_classification"].get("intent") != "error")
        
        correct_intent_classifications = sum(1 for r in results["thread_results"] 
                                           if "queries" in r 
                                           for q in r["queries"] 
                                           if q.get("intent_correct") is True)
        
        incorrect_intent_classifications = sum(1 for r in results["thread_results"] 
                                             if "queries" in r 
                                             for q in r["queries"] 
                                             if q.get("intent_correct") is False)
        
        intent_accuracy = (correct_intent_classifications / total_intent_classifications * 100) if total_intent_classifications > 0 else 0
        
        # Calculate agent trace validation statistics
        total_validations = sum(r.get("validation_summary", {}).get("total", 0) for r in results["thread_results"] if "validation_summary" in r)
        passed_validations = sum(r.get("validation_summary", {}).get("passed", 0) for r in results["thread_results"] if "validation_summary" in r)
        failed_validations = sum(r.get("validation_summary", {}).get("failed", 0) for r in results["thread_results"] if "validation_summary" in r)
        validation_accuracy = (passed_validations / total_validations * 100) if total_validations > 0 else 0
        
        results["test_suite_info"].update({
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "successful_threads": successful_threads,
            "failed_threads": failed_threads,
            "total_chat_responses": total_chat_responses,
            "total_agent_responses": total_agent_responses,
            "intent_classification": {
                "total_classifications": total_intent_classifications,
                "correct": correct_intent_classifications,
                "incorrect": incorrect_intent_classifications,
                "accuracy_percent": round(intent_accuracy, 2)
            },
            "agent_trace_validation": {
                "total_validations": total_validations,
                "passed": passed_validations,
                "failed": failed_validations,
                "accuracy_percent": round(validation_accuracy, 2)
            }
        })
        
        logger.info(f"Test suite completed in {duration:.2f} seconds")
        logger.info(f"Results: {successful_threads}/{len(test_threads)} threads successful")
        logger.info(f"Responses: {total_chat_responses} chat, {total_agent_responses} agent")
        if total_intent_classifications > 0:
            logger.info(f"Intent Classification: {correct_intent_classifications}/{total_intent_classifications} correct ({intent_accuracy:.2f}% accuracy)")
        if total_validations > 0:
            logger.info(f"Agent Trace Validation: {passed_validations}/{total_validations} passed ({validation_accuracy:.2f}% accuracy)")
        
        return results
    
    async def cleanup_test_threads(self):
        """Clean up created test threads (optional)."""
        logger.info(f"Cleaning up {len(self.created_threads)} test threads...")
        # Note: In a real implementation, you might want to delete test threads
        # But for now, we'll just log them
        for thread_id in self.created_threads:
            logger.info(f"Test thread created: {thread_id}")

async def main():
    """Main test runner."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Meridian Comprehensive Test Suite with Agent Trace Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available categories:
  - simple_chat: Simple chat queries (no agents)
  - basic_info: Basic information queries (information agent)
  - technical_analysis: Technical analysis queries (market agent)
  - fundamental_analysis: Fundamental analysis queries (fundamentals agent)
  - market_overview: Market overview queries (market + information agents)
  - comprehensive_analysis: Comprehensive analysis queries (full workflow)
  - mixed_conversation: Mixed conversation with various intents

Example usage:
  python test_user_queries.py --category comprehensive_analysis
  python test_user_queries.py --category simple_chat
  python test_user_queries.py  # Run all categories
        """
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=[
            "simple_chat",
            "basic_info",
            "technical_analysis",
            "fundamental_analysis",
            "market_overview",
            "comprehensive_analysis",
            "mixed_conversation"
        ],
        default=None,
        help="Category of queries to test (default: all categories)"
    )
    parser.add_argument(
        "--backend-url",
        type=str,
        default=os.getenv("BACKEND_URL", "http://localhost:8000"),
        help="Backend service URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--agents-url",
        type=str,
        default=os.getenv("AGENTS_URL", "http://localhost:8001"),
        help="Agents service URL (default: http://localhost:8001)"
    )
    
    args = parser.parse_args()
    
    # Get bearer token from user
    print("\n" + "=" * 50)
    print("Meridian Comprehensive Test Suite")
    print("=" * 50)
    print("\nAuthentication required for API access.")
    bearer_token = input("Enter bearer token: ").strip()
    
    if not bearer_token:
        print("Error: Bearer token is required. Exiting.")
        sys.exit(1)
    
    # Confirm token was received
    print(f"Token received: {bearer_token[:20]}...{bearer_token[-10:] if len(bearer_token) > 30 else ''}")
    print("")
    
    backend_url = args.backend_url
    agents_url = args.agents_url
    category_filter = args.category
    
    logger.info("Meridian Comprehensive Test Suite")
    logger.info("=" * 50)
    logger.info(f"Backend URL: {backend_url}")
    logger.info(f"Agents URL: {agents_url}")
    if category_filter:
        logger.info(f"Category Filter: {category_filter}")
    logger.info("")
    
    try:
        async with MeridianTestSuite(backend_url, agents_url, bearer_token) as test_suite:
            results = await test_suite.run_full_test_suite(category_filter=category_filter)
        
        # Save results to file
            category_suffix = f"_{category_filter}" if category_filter else "_all"
            output_file = f"meridian_test_results{category_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_file}")
        
        # Print summary
        info = results["test_suite_info"]
        print("\n" + "=" * 50)
        print("TEST SUITE SUMMARY")
        print("=" * 50)
        print(f"Duration: {info['duration_seconds']:.2f} seconds")
        print(f"Threads: {info['successful_threads']}/{info['total_threads']} successful")
        print(f"Queries: {info['total_queries']} total")
        print(f"Chat Responses: {info['total_chat_responses']}")
        print(f"Agent Responses: {info['total_agent_responses']}")
            
        if 'intent_classification' in info:
            intent_info = info['intent_classification']
            print(f"\nIntent Classification Results:")
            print(f"  Total Classifications: {intent_info['total_classifications']}")
            print(f"  Correct: {intent_info['correct']}")
            print(f"  Incorrect: {intent_info['incorrect']}")
            print(f"  Accuracy: {intent_info['accuracy_percent']}%")
            
            if 'agent_trace_validation' in info:
                trace_info = info['agent_trace_validation']
                print(f"\nAgent Trace Validation Results:")
                print(f"  Total Validations: {trace_info['total_validations']}")
                print(f"  Passed: {trace_info['passed']}")
                print(f"  Failed: {trace_info['failed']}")
                print(f"  Accuracy: {trace_info['accuracy_percent']}%")
            
        print(f"\nResults saved to: {output_file}")
        
        # Cleanup
        await test_suite.cleanup_test_threads()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
