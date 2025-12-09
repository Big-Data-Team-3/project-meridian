#!/bin/bash

# Meridian Project - Test All Agents Script
# This script tests all agents using test_agent.py

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENTS_DIR="$PROJECT_ROOT/meridian-agents"
TEST_SCRIPT="$AGENTS_DIR/test_agent.py"

# Default values
TICKER="${1:-AAPL}"
DATE="${2:-$(date +%Y-%m-%d)}"

# Track results
PASSED=0
FAILED=0
FAILED_AGENTS=()

# Agent list - organized by category
# Note: "information" agent combines the functionality of the old "news" and "social" agents
ANALYST_AGENTS=("market" "fundamentals" "information")
RESEARCHER_AGENTS=("bull" "bear")
MANAGER_AGENTS=("research_manager" "trader" "risk_manager")
DEBATOR_AGENTS=("risky" "safe" "neutral")

ALL_AGENTS=(
    "${ANALYST_AGENTS[@]}"
    "${RESEARCHER_AGENTS[@]}"
    "${MANAGER_AGENTS[@]}"
    "${DEBATOR_AGENTS[@]}"
)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Meridian Project - Test All Agents${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Check if test_agent.py exists
if [ ! -f "$TEST_SCRIPT" ]; then
    echo -e "${RED}❌ Error: test_agent.py not found at $TEST_SCRIPT${NC}"
    exit 1
fi

# Check if we're in the right directory or can find the script
if [ ! -f "$TEST_SCRIPT" ]; then
    echo -e "${RED}❌ Error: Cannot find test_agent.py${NC}"
    echo -e "${YELLOW}   Expected location: $TEST_SCRIPT${NC}"
    exit 1
fi

# Check for OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  Warning: OPENAI_API_KEY not set${NC}"
    echo -e "${YELLOW}   The script will check for it, but you may need to set it first${NC}\n"
fi

echo -e "${CYAN}Configuration:${NC}"
echo -e "  Ticker: ${BLUE}$TICKER${NC}"
echo -e "  Date: ${BLUE}$DATE${NC}"
echo -e "  Total Agents: ${BLUE}${#ALL_AGENTS[@]}${NC}"
echo -e "  Test Script: ${BLUE}$TEST_SCRIPT${NC}\n"

echo -e "${GREEN}Starting agent tests...${NC}\n"
echo -e "${GREEN}========================================${NC}\n"

# Function to test a single agent
test_agent() {
    local agent=$1
    local ticker=$2
    local date=$3
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}Testing: ${BLUE}$agent${NC} (Ticker: $ticker, Date: $date)"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    # Change to agents directory to run the test
    cd "$AGENTS_DIR"
    
    if python test_agent.py --agent "$agent" --ticker "$ticker" --date "$date" > /tmp/agent_test_${agent}.log 2>&1; then
        echo -e "\n${GREEN}✅ PASSED: $agent${NC}\n"
        ((PASSED++))
        return 0
    else
        echo -e "\n${RED}❌ FAILED: $agent${NC}\n"
        ((FAILED++))
        FAILED_AGENTS+=("$agent")
        
        # Show last few lines of error
        echo -e "${YELLOW}Last 10 lines of output:${NC}"
        tail -n 10 /tmp/agent_test_${agent}.log | sed 's/^/  /'
        echo ""
        return 1
    fi
}

# Test Analyst Agents
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 ANALYST AGENTS (OpenAI Agents SDK)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

for agent in "${ANALYST_AGENTS[@]}"; do
    test_agent "$agent" "$TICKER" "$DATE"
done

# Test Researcher Agents
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔍 RESEARCHER AGENTS (OpenAI Agents SDK)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

for agent in "${RESEARCHER_AGENTS[@]}"; do
    test_agent "$agent" "$TICKER" "$DATE"
done

# Test Manager Agents
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}👔 MANAGER AGENTS (OpenAI Agents SDK)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

for agent in "${MANAGER_AGENTS[@]}"; do
    test_agent "$agent" "$TICKER" "$DATE"
done

# Test Debator Agents
echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}💬 DEBATOR AGENTS (OpenAI Agents SDK)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

for agent in "${DEBATOR_AGENTS[@]}"; do
    test_agent "$agent" "$TICKER" "$DATE"
done

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Test Summary${NC}"
echo -e "${GREEN}========================================${NC}\n"

TOTAL=$((PASSED + FAILED))
echo -e "Total Agents Tested: ${BLUE}$TOTAL${NC}"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}\n"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All agents passed!${NC}\n"
    exit 0
else
    echo -e "${RED}❌ Some agents failed:${NC}"
    for agent in "${FAILED_AGENTS[@]}"; do
        echo -e "  ${RED}• $agent${NC}"
        echo -e "    Log: ${YELLOW}/tmp/agent_test_${agent}.log${NC}"
    done
    echo ""
    echo -e "${YELLOW}💡 Tip: Check individual log files for detailed error messages${NC}\n"
    exit 1
fi

