"""
Intent Classification Test Suite for Meridian
Tests intent detection for user queries with category-based testing.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

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
    logger.info("Instructor-based intent classification available")
except (ImportError, RuntimeError) as e:
    logger.warning(f"Intent classification not available: {e}")
    INTENT_CLASSIFICATION_AVAILABLE = False

@dataclass
class TestThread:
    """Represents a test category with multiple queries."""
    queries: List[str]
    description: str
    category: str  # Category name for filtering
    expected_intents: List[str]  # Expected intent for each query

class IntentClassificationTestSuite:
    """Test suite for intent classification accuracy."""

    def classify_query_intent(self, query: str) -> Dict[str, Any]:
        """Classify query intent using instructor-based LLM classifier ONLY (no fallback)."""
        if not INTENT_CLASSIFICATION_AVAILABLE:
            error_msg = "Instructor-based classification is required but not available"
            logger.error(f"{error_msg}. Install instructor library and configure OpenAI API.")
            return {
                "intent": "error",
                "error": error_msg,
                "classification_method": "failed"
            }

        try:
            # Use instructor-based LLM classification through the orchestrator
            orchestrator = get_agent_orchestrator()
            intent, workflow = orchestrator.classify_and_get_workflow(query)

            result = {
                "intent": intent.value if hasattr(intent, 'value') else str(intent),
                "workflow_type": workflow.workflow_type,
                "agents": workflow.agents,
                "timeout_seconds": workflow.timeout_seconds,
                "classification_method": "instructor_llm"
            }

            logger.debug(f"Instructor classified '{query[:50]}...' as {result['intent']}")
            return result

        except Exception as e:
            error_msg = f"Instructor-based classification failed: {str(e)}"
            logger.error(error_msg)
            return {
                "intent": "error",
                "error": error_msg,
                "classification_method": "failed"
            }

    
    
    def generate_test_queries(self, category_filter: Optional[str] = None) -> List[TestThread]:
        """Generate test queries organized by category."""

        test_threads = []

        # Category: simple_chat - No agents, direct OpenAI responses
        test_threads.append(TestThread(
            queries=[
                "Hello! What are you?",
                "What can you help me with?",
                "Tell me about yourself",
                "What is Meridian?",
                "How can you help me with investing?"
            ],
            description="Simple chat - no agents",
            category="simple_chat",
            expected_intents=["simple_chat", "simple_chat", "simple_chat", "simple_chat", "simple_chat"]
        ))

        # Category: basic_info - Single agent (information)
        test_threads.append(TestThread(
            queries=[
                "What is Apple stock trading at today?",
                "What is Tesla's business?",
                "What's Microsoft's main products?",
                "What is NVIDIA doing?",
                "What's Amazon's business model?"
            ],
            description="Basic info - information agent",
            category="basic_info",
            expected_intents=["basic_info", "basic_info", "basic_info", "basic_info", "basic_info"]
        ))

        # Category: technical_analysis - Single agent (market)
        test_threads.append(TestThread(
            queries=[
                "Run a market analysis on AAPL",
                "Apple stock technical analysis",
                "What's the technical outlook for Tesla?",
                "Show me technical indicators for Microsoft",
                "Technical chart analysis for NVIDIA"
            ],
            description="Technical analysis - market agent",
            category="technical_analysis",
            expected_intents=["technical_analysis", "technical_analysis", "technical_analysis", "technical_analysis", "technical_analysis"]
        ))

        # Category: fundamental_analysis - Single agent (fundamentals)
        test_threads.append(TestThread(
            queries=[
                "Analyze Apple's fundamentals",
                "Get fundamental data for Apple",
                "Tesla's financial health",
                "Microsoft's financial metrics",
                "NVIDIA's valuation analysis"
            ],
            description="Fundamental analysis - fundamentals agent",
            category="fundamental_analysis",
            expected_intents=["fundamental_analysis", "fundamental_analysis", "fundamental_analysis", "fundamental_analysis", "fundamental_analysis"]
        ))

        # Category: market_overview - Multi-agent (market + information)
        test_threads.append(TestThread(
            queries=[
                "What are the major stock indices?",
                "What's the Dow Jones?",
                "Explain S&P 500",
                "What's NASDAQ?",
                "How do stock indices work?"
            ],
            description="Market overview - market and information agents",
            category="market_overview",
            expected_intents=["market_overview", "market_overview", "market_overview", "market_overview", "market_overview"]
        ))

        # Category: comprehensive_analysis - Full workflow (multiple agents)
        test_threads.append(TestThread(
            queries=[
                "Should I buy Apple stock today?",
                "Is Tesla overvalued?",
                "Bull case for Tesla",
                "Risk assessment for Microsoft",
                "Comprehensive analysis of AMZN"
            ],
            description="Comprehensive analysis - full workflow",
            category="comprehensive_analysis",
            expected_intents=["comprehensive_trade", "comprehensive_trade", "comprehensive_trade", "comprehensive_trade", "comprehensive_trade"]
        ))

        # Category: news_sentiment - News and sentiment analysis
        test_threads.append(TestThread(
            queries=[
                "What's the news on Apple today?",
                "Tesla social media sentiment",
                "Microsoft recent announcements",
                "Market sentiment for NVIDIA",
                "Breaking news in tech stocks"
            ],
            description="News and sentiment analysis",
            category="news_sentiment",
            expected_intents=["news_sentiment", "news_sentiment", "news_sentiment", "news_sentiment", "news_sentiment"]
        ))

        # Category: portfolio_review - Portfolio analysis
        test_threads.append(TestThread(
            queries=[
                "How is my portfolio performing?",
                "Review my investments",
                "Portfolio allocation analysis",
                "Should I rebalance my portfolio?",
                "Portfolio risk assessment"
            ],
            description="Portfolio analysis and review",
            category="portfolio_review",
            expected_intents=["portfolio_review", "portfolio_review", "portfolio_review", "portfolio_review", "portfolio_review"]
        ))

        # Category: mixed_conversation - Multi-turn with different intents
        test_threads.append(TestThread(
            queries=[
                "I'm new to investing. Can you help me get started?",
                "What are the different types of investments?",
                "How do I choose a good investment?",
                "What's diversification and why is it important?",
                "What's a good long-term investment strategy?"
            ],
            description="Mixed conversation - various intents",
            category="mixed_conversation",
            expected_intents=["simple_chat", "basic_info", "comprehensive_trade", "basic_info", "comprehensive_trade"]
        ))

        # Filter by category if specified
        if category_filter:
            test_threads = [t for t in test_threads if t.category == category_filter]
            if not test_threads:
                logger.warning(f"No test threads found for category: {category_filter}")

        return test_threads
    
    def run_category_test(self, thread: TestThread) -> Dict[str, Any]:
        """Run intent classification test for a category."""
        logger.info(f"Testing category: {thread.description} ({len(thread.queries)} queries)")

        results = {
            "category": thread.category,
            "description": thread.description,
            "queries": [],
            "total_queries": len(thread.queries),
            "intent_classification": {
                "total": len(thread.queries),
                "correct": 0,
                "incorrect": 0,
                "errors": []
            }
        }

        # Test each query in the category
        for i, query in enumerate(thread.queries):
            try:
                logger.debug(f"Testing query {i+1}/{len(thread.queries)}: {query[:50]}...")

                # Classify query intent
                intent_result = self.classify_query_intent(query)
                expected_intent = thread.expected_intents[i] if i < len(thread.expected_intents) else None

                # Check if classification matches expected
                intent_correct = False
                if expected_intent and intent_result and intent_result.get("intent") != "error":
                    intent_correct = (intent_result.get("intent") == expected_intent)

                if intent_correct:
                    results["intent_classification"]["correct"] += 1
                    logger.debug(f"✓ Query {i+1} correct: {intent_result.get('intent')}")
                else:
                    results["intent_classification"]["incorrect"] += 1
                    if expected_intent:
                        logger.warning(
                            f"✗ Query {i+1} incorrect: expected '{expected_intent}', "
                            f"got '{intent_result.get('intent')}' for query: {query[:50]}..."
                        )
                        results["intent_classification"]["errors"].append(
                            f"Query {i+1}: expected '{expected_intent}', got '{intent_result.get('intent')}'"
                        )

                query_result = {
                    "query_number": i + 1,
                    "query": query,
                    "intent_classification": intent_result,
                    "expected_intent": expected_intent,
                    "intent_correct": intent_correct,
                    "timestamp": datetime.now().isoformat()
                }

                results["queries"].append(query_result)

            except Exception as e:
                logger.error(f"Error testing query {i+1}: {e}", exc_info=True)
                query_result = {
                    "query_number": i + 1,
                    "query": query,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                results["queries"].append(query_result)
                results["intent_classification"]["incorrect"] += 1
                results["intent_classification"]["errors"].append(f"Query {i+1}: {str(e)}")

        accuracy = (results["intent_classification"]["correct"] / results["intent_classification"]["total"] * 100) if results["intent_classification"]["total"] > 0 else 0
        results["intent_classification"]["accuracy_percent"] = round(accuracy, 2)

        logger.info(
            f"Category {thread.category}: {results['intent_classification']['correct']}/{results['intent_classification']['total']} correct "
            f"({accuracy:.1f}% accuracy)"
        )

        return results
    
    def run_full_test_suite(self, category_filter: Optional[str] = None) -> Dict[str, Any]:
        """Run the complete intent classification test suite."""
        logger.info("Starting Intent Classification Test Suite...")
        if category_filter:
            logger.info(f"Filtering by category: {category_filter}")

        start_time = datetime.now()
        test_threads = self.generate_test_queries(category_filter=category_filter)

        logger.info(f"Generated {len(test_threads)} test categories with {sum(len(t.queries) for t in test_threads)} total queries")

        results = {
            "test_suite_info": {
                "start_time": start_time.isoformat(),
                "total_categories": len(test_threads),
                "total_queries": sum(len(t.queries) for t in test_threads),
                "intent_classification_available": INTENT_CLASSIFICATION_AVAILABLE
            },
            "category_results": []
        }

        # Run each category test
        for i, thread in enumerate(test_threads):
            logger.info(f"Testing category {i+1}/{len(test_threads)}: {thread.description}")
            try:
                category_result = self.run_category_test(thread)
                results["category_results"].append(category_result)
            except Exception as e:
                logger.error(f"Failed to test category {thread.description}: {e}")
                results["category_results"].append({
                    "category": thread.category,
                    "description": thread.description,
                    "error": str(e),
                    "total_queries": len(thread.queries)
                })

        # Calculate final statistics
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Calculate overall intent classification statistics
        total_classifications = sum(r.get("intent_classification", {}).get("total", 0) for r in results["category_results"] if "intent_classification" in r)
        correct_classifications = sum(r.get("intent_classification", {}).get("correct", 0) for r in results["category_results"] if "intent_classification" in r)
        incorrect_classifications = sum(r.get("intent_classification", {}).get("incorrect", 0) for r in results["category_results"] if "intent_classification" in r)

        overall_accuracy = (correct_classifications / total_classifications * 100) if total_classifications > 0 else 0

        results["test_suite_info"].update({
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration, 2),
            "overall_intent_classification": {
                "total_classifications": total_classifications,
                "correct": correct_classifications,
                "incorrect": incorrect_classifications,
                "accuracy_percent": round(overall_accuracy, 2)
            }
        })

        logger.info(f"Test suite completed in {duration:.2f} seconds")
        logger.info(f"Overall Intent Classification: {correct_classifications}/{total_classifications} correct ({overall_accuracy:.2f}% accuracy)")

        return results
    

def main():
    """Main test runner."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Meridian Intent Classification Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available categories:
  - simple_chat: Simple chat queries (no agents)
  - basic_info: Basic information queries (information agent)
  - technical_analysis: Technical analysis queries (market agent)
  - fundamental_analysis: Fundamental analysis queries (fundamentals agent)
  - news_sentiment: News and sentiment analysis queries
  - market_overview: Market overview queries (market + information agents)
  - comprehensive_analysis: Comprehensive analysis queries (full workflow)
  - portfolio_review: Portfolio analysis and review queries
  - mixed_conversation: Mixed conversation with various intents

Example usage:
  python test_user_query_intents.py --category comprehensive_analysis
  python test_user_query_intents.py --category simple_chat
  python test_user_query_intents.py  # Run all categories
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
            "news_sentiment",
            "market_overview",
            "comprehensive_analysis",
            "portfolio_review",
            "mixed_conversation"
        ],
        default=None,
        help="Category of queries to test (default: all categories)"
    )

    args = parser.parse_args()
    category_filter = args.category

    logger.info("Meridian Intent Classification Test Suite")
    logger.info("=" * 50)
    if category_filter:
        logger.info(f"Category Filter: {category_filter}")
    logger.info("")

    try:
        test_suite = IntentClassificationTestSuite()
        results = test_suite.run_full_test_suite(category_filter=category_filter)

        # Save results to file
        category_suffix = f"_{category_filter}" if category_filter else "_all"
        output_file = f"intent_classification_test_results{category_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Results saved to {output_file}")

        # Print summary
        info = results["test_suite_info"]
        print("\n" + "=" * 50)
        print("INTENT CLASSIFICATION TEST SUITE SUMMARY")
        print("=" * 50)
        print(f"Duration: {info['duration_seconds']} seconds")
        print(f"Categories: {info['total_categories']}")
        print(f"Queries: {info['total_queries']} total")
        print(f"Intent Classification Available: {info['intent_classification_available']}")

        overall = info.get('overall_intent_classification', {})
        if overall:
            print(f"\nOverall Intent Classification Results:")
            print(f"  Total Classifications: {overall['total_classifications']}")
            print(f"  Correct: {overall['correct']}")
            print(f"  Incorrect: {overall['incorrect']}")
            print(f"  Accuracy: {overall['accuracy_percent']}%")

        print(f"\nDetailed results saved to: {output_file}")

        # Show per-category breakdown
        if results.get("category_results"):
            print(f"\nPer-Category Results:")
            for category_result in results["category_results"]:
                if "intent_classification" in category_result:
                    cat_info = category_result["intent_classification"]
                    print(f"  {category_result['category']}: {cat_info['correct']}/{cat_info['total']} ({cat_info['accuracy_percent']}%)")

    except Exception as e:
        logger.error(f"Test suite failed: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
