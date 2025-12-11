"""
Comprehensive User Query Test Suite for Meridian Agents
Tests both chat API and direct agent calls with 50 queries organized into 10 conversation threads.
"""

import asyncio
import httpx
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
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

@dataclass
class TestThread:
    """Represents a conversation thread with multiple queries."""
    thread_id: str
    queries: List[str]
    description: str
    is_agentic_focus: bool = False
    expected_intents: Optional[List[str]] = None  # Expected intent for each query

class MeridianTestSuite:
    """Test suite for Meridian backend and agents services."""
    
    def __init__(self, backend_url: str = "http://localhost:8000", agents_url: str = "http://localhost:8001"):
        self.backend_url = backend_url.rstrip('/')
        self.agents_url = agents_url.rstrip('/')
        self.test_user_id = "test-user-12345"
        self.created_threads: List[str] = []
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def authenticate_and_get_token(self) -> str:
        """Mock authentication - in real scenario would get JWT token."""
        # For testing, we'll assume auth is disabled or use a test token
        return "test-token-123"
    
    async def create_thread(self, title: str = "Test Thread") -> str:
        """Create a new thread for testing."""
        try:
            response = await self.client.post(
                f"{self.backend_url}/api/threads",
                json={"title": title},
                headers={"Authorization": f"Bearer {await self.authenticate_and_get_token()}"}
            )
            response.raise_for_status()
            thread_data = response.json()
            thread_id = thread_data["thread_id"]
            self.created_threads.append(thread_id)
            logger.info(f"Created thread: {thread_id}")
            return thread_id
        except Exception as e:
            logger.error(f"Failed to create thread: {e}")
            # Return a mock thread ID for testing
            return f"mock-thread-{uuid.uuid4()}"
    
    async def send_chat_message(self, thread_id: str, message: str) -> Dict[str, Any]:
        """Send a chat message and get response."""
        try:
            response = await self.client.post(
                f"{self.backend_url}/api/chat",
                json={"thread_id": thread_id, "message": message},
                headers={"Authorization": f"Bearer {await self.authenticate_and_get_token()}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Chat API error: {e}")
            return {"error": str(e), "thread_id": thread_id, "message": message}
    
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
                json=payload
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
    
    def generate_test_queries(self) -> List[TestThread]:
        """Generate comprehensive test queries organized into 10 threads with 5 queries each."""
        
        # Get today's date and some historical dates for testing
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        test_threads = []
        
        # Thread 1: Non-agentic - Basic casual conversation
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "Hello! How are you today?",
                "What's the weather like?",
                "Can you tell me a joke?",
                "What's your favorite programming language?",
                "Do you like pineapple on pizza?"
            ],
            description="Basic casual conversation",
            expected_intents=["simple_chat", "simple_chat", "simple_chat", "simple_chat", "simple_chat"]
        ))
        
        # Thread 2: Non-agentic - General knowledge and creative
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "What time is it?",
                "Can you help me with some math? 15 * 23",
                "Can you write a haiku about coding?",
                "Tell me a story about a robot",
                "If you could travel anywhere, where would you go?"
            ],
            description="General knowledge and creative prompts",
            expected_intents=["simple_chat", "simple_chat", "simple_chat", "simple_chat", "simple_chat"]
        ))
        
        # Thread 3: Basic finance - Stock market basics
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "What are the major stock indices?",
                "What's the Dow Jones?",
                "Explain S&P 500",
                "What's NASDAQ?",
                "How do stock indices work?"
            ],
            description="Stock market indices education",
            is_agentic_focus=True,
            expected_intents=["market_overview", "market_overview", "market_overview", "market_overview", "market_overview"]
        ))
        
        # Thread 4: Basic finance - Investment concepts
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "What is portfolio diversification?",
                "Should I invest in stocks or bonds?",
                "What are ETFs?",
                "What's technical analysis?",
                "What's fundamental analysis?"
            ],
            description="Investment concepts and strategies",
            is_agentic_focus=True,
            expected_intents=["basic_info", "comprehensive_trade", "basic_info", "basic_info", "basic_info"]
        ))
        
        # Thread 5: Basic finance - Company basics
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "What is Apple stock trading at today?",
                "What is Tesla's business?",
                "What's Microsoft's main products?",
                "What is NVIDIA doing?",
                "What's Amazon's business model?"
            ],
            description="Major company overviews",
            is_agentic_focus=True,
            expected_intents=["basic_info", "basic_info", "basic_info", "basic_info", "basic_info"]
        ))
        
        # Thread 6: Agentic - Apple deep analysis
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "Should I buy Apple stock today?",
                "Analyze Apple's fundamentals",
                "What's Apple's growth potential?",
                "Apple stock technical analysis",
                "Apple vs competitors"
            ],
            description="Apple comprehensive analysis",
            is_agentic_focus=True,
            expected_intents=["comprehensive_trade", "fundamental_analysis", "comprehensive_trade", "technical_analysis", "comprehensive_trade"]
        ))
        
        # Thread 7: Agentic - Tesla deep analysis
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "Is Tesla overvalued?",
                "Tesla's financial health",
                "EV market competition",
                "Tesla's innovation pipeline",
                "Short-term Tesla outlook"
            ],
            description="Tesla valuation analysis",
            is_agentic_focus=True,
            expected_intents=["comprehensive_trade", "fundamental_analysis", "comprehensive_trade", "comprehensive_trade", "comprehensive_trade"]
        ))
        
        # Thread 8: Agentic - Tech sector analysis
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "NVIDIA investment thesis",
                "Meta Platforms stock pick?",
                "Netflix streaming economics",
                "Snowflake data platform",
                "CrowdStrike cybersecurity"
            ],
            description="Tech sector company analysis",
            is_agentic_focus=True,
            expected_intents=["comprehensive_trade", "comprehensive_trade", "basic_info", "basic_info", "basic_info"]
        ))
        
        # Thread 9: Long workflow - Beginner investor journey (condensed)
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "I'm new to investing. Can you help me get started?",
                "What are the different types of investments?",
                "How do I choose a good investment?",
                "What's diversification and why is it important?",
                "What's a good long-term investment strategy?"
            ],
            description="Beginner investor education journey",
            is_agentic_focus=True,
            expected_intents=["simple_chat", "basic_info", "comprehensive_trade", "basic_info", "comprehensive_trade"]
        ))
        
        # Thread 10: Agentic - Individual agent calls
        test_threads.append(TestThread(
            thread_id="",
            queries=[
                "Run a market analysis on AAPL",
                "Get fundamental data for Apple",
                "Bull case for Tesla",
                "Risk assessment for Microsoft",
                "Comprehensive analysis of AMZN"
            ],
            description="Individual agent-focused queries",
            is_agentic_focus=True,
            expected_intents=["technical_analysis", "fundamental_analysis", "comprehensive_trade", "comprehensive_trade", "comprehensive_trade"]
        ))
        
        return test_threads
    
    async def run_thread_test(self, thread: TestThread) -> Dict[str, Any]:
        """Run a complete thread test."""
        logger.info(f"Starting thread test: {thread.description}")
        
        # Create thread
        thread_id = await self.create_thread(thread.description)
        thread.thread_id = thread_id
        
        results = {
            "thread_id": thread_id,
            "description": thread.description,
            "is_agentic_focus": thread.is_agentic_focus,
            "queries": [],
            "total_queries": len(thread.queries)
        }
        
        # Process each query in the thread
        for i, query in enumerate(thread.queries):
            logger.info(f"Processing query {i+1}/{len(thread.queries)}: {query[:50]}...")
            
            # Classify query intent
            intent_result = self.classify_query_intent(query)
            expected_intent = None
            if thread.expected_intents and i < len(thread.expected_intents):
                expected_intent = thread.expected_intents[i]
            
            # Verify intent classification matches expected (if provided)
            intent_correct = None
            if expected_intent and intent_result.get("intent") != "error":
                intent_correct = (intent_result.get("intent") == expected_intent)
                if not intent_correct:
                    logger.warning(
                        f"Intent mismatch for query '{query[:50]}...': "
                        f"expected {expected_intent}, got {intent_result.get('intent')}"
                    )
            
            # Send chat message
            chat_response = await self.send_chat_message(thread_id, query)
            
            # If this is an agentic query, also try direct agent analysis
            agent_response = None
            if thread.is_agentic_focus and any(keyword in query.lower() for keyword in 
                ['analyze', 'should i buy', 'investment', 'stock', 'company', 'market', 'run a', 'get ', 'bull case', 'risk assessment', 'comprehensive']):
                # Extract company name (simple heuristic)
                company_names = ['AAPL', 'Apple', 'MSFT', 'Microsoft', 'TSLA', 'Tesla', 
                               'AMZN', 'Amazon', 'GOOGL', 'Alphabet', 'NVDA', 'NVIDIA',
                               'META', 'NFLX', 'Netflix', 'BTC', 'Bitcoin', 'ETH', 'Ethereum']
                
                company = None
                for name in company_names:
                    if name.lower() in query.lower():
                        company = name if len(name) <= 5 else name  # Use ticker for longer names
                        break
                
                if company:
                    agent_response = await self.call_agents_analyze(company, datetime.now().strftime("%Y-%m-%d"))
            
            query_result = {
                "query_number": i + 1,
                "query": query,
                "intent_classification": intent_result,
                "expected_intent": expected_intent,
                "intent_correct": intent_correct,
                "chat_response": chat_response,
                "agent_response": agent_response,
                "timestamp": datetime.now().isoformat()
            }
            
            results["queries"].append(query_result)
            
            # Small delay between queries to avoid rate limiting
            await asyncio.sleep(0.5)
        
        logger.info(f"Completed thread test: {thread.description}")
        return results
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run the complete test suite."""
        logger.info("Starting comprehensive Meridian test suite...")
        
        start_time = datetime.now()
        test_threads = self.generate_test_queries()
        
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
            }
        })
        
        logger.info(f"Test suite completed in {duration:.2f} seconds")
        logger.info(f"Results: {successful_threads}/{len(test_threads)} threads successful")
        logger.info(f"Responses: {total_chat_responses} chat, {total_agent_responses} agent")
        if total_intent_classifications > 0:
            logger.info(f"Intent Classification: {correct_intent_classifications}/{total_intent_classifications} correct ({intent_accuracy:.2f}% accuracy)")
        
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
    # Configuration
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    agents_url = os.getenv("AGENTS_URL", "http://localhost:8001")
    
    logger.info("Meridian Comprehensive Test Suite")
    logger.info("=" * 50)
    logger.info(f"Backend URL: {backend_url}")
    logger.info(f"Agents URL: {agents_url}")
    logger.info("")
    
    async with MeridianTestSuite(backend_url, agents_url) as test_suite:
        results = await test_suite.run_full_test_suite()
        
        # Save results to file
        output_file = f"meridian_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
        print(f"\nResults saved to: {output_file}")
        
        # Cleanup
        await test_suite.cleanup_test_threads()

if __name__ == "__main__":
    asyncio.run(main())
