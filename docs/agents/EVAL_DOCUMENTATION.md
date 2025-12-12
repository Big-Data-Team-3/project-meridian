# Agent Evaluation System Documentation

## Overview

This evaluation system provides a comprehensive testing framework for all agents in the Meridian Agents codebase. It enables automated testing of agent functionality, response quality, and performance metrics across the entire agent ecosystem.

## Architecture

### Components

1. **`eval_config.yaml`** - Configuration file defining which agents to test and their expected behaviors
2. **`run_eval.py`** - Main evaluation runner that orchestrates tests and collects results
3. **`scorers.py`** - Scoring logic for evaluating agent responses against expected criteria
4. **`reports/latest.json`** - Output file containing test results with scores and latencies

### Evaluation Flow

```
eval_config.yaml → run_eval.py → Agent Factory Functions → Agent Execution → Response Extraction → Scoring → Results JSON
```

## Agent Coverage

The evaluation system tests **11 agents** across different categories:

### Analysts (Data Collection Agents)
- **market_analyst** - Technical market analysis using indicators
- **fundamentals_analyst** - Fundamental financial analysis
- **information_analyst** - News and information analysis

### Researchers (Debate Agents)
- **bull_researcher** - Bull case arguments for investments
- **bear_researcher** - Bear case arguments against investments

### Managers (Synthesis Agents)
- **research_manager** - Synthesizes debate into investment plan
- **risk_manager** - Evaluates risk and makes final decisions

### Trader
- **trader** - Makes trading decisions (BUY/SELL/HOLD)

### Risk Debators
- **risky_debator** - Aggressive risk perspective
- **safe_debator** - Conservative risk perspective
- **neutral_debator** - Balanced risk perspective

## Configuration

### eval_config.yaml Structure

Each agent configuration includes:

```yaml
- name: agent_name
  entrypoint: "module.path:factory_function"
  requires_memory: true/false
  tests:
    - id: "test_id"
      prompt: "Test prompt text"
      expected:
        must_contain_keywords: ["required", "keywords"]
        contains: ["optional", "keywords"]
```

### Key Fields

- **`name`**: Human-readable agent identifier
- **`entrypoint`**: Python import path to the agent factory function
- **`requires_memory`**: Whether the agent needs a `FinancialSituationMemory` instance
- **`tests`**: Array of test cases
  - **`id`**: Unique test identifier
  - **`prompt`**: Input prompt for the agent (used for documentation; actual execution uses agent's internal prompt construction)
  - **`expected`**: Scoring criteria
    - **`must_contain_keywords`**: Required keywords (-0.3 per missing)
    - **`contains`**: Optional keywords (-0.15 per missing)

## Running Evaluations

### Prerequisites

1. Set `OPENAI_API_KEY` environment variable:
   ```bash
   export OPENAI_API_KEY=your-api-key
   ```

   Or create a `.env` file in the project root:
   ```bash
   echo 'OPENAI_API_KEY=your-api-key' > .env
   ```

2. Install dependencies (if not already installed)

### Execution

```bash
cd meridian-agents/tests/evals
python run_eval.py
```

### Output

Results are saved to `reports/latest.json` with the following structure:

```json
[
  {
    "id": "test_id",
    "prompt": "Test prompt",
    "response": "Agent response text",
    "score": 0.95,
    "latency": 12.34
  }
]
```

## Scoring Methodology

### Scoring Algorithm

The scoring system uses a rule-based approach with keyword matching:

1. **Base Score**: Starts at 1.0
2. **Required Keywords** (`must_contain_keywords`):
   - Missing keyword: -0.3 per keyword
   - All found: +0.1 bonus
3. **Optional Keywords** (`contains`):
   - Missing keyword: -0.15 per keyword
   - 70%+ found: +0.05 bonus
4. **Response Quality Bonuses**:
   - Response > 100 chars: +0.1
   - Response > 50 chars: +0.05
5. **Error Penalties**:
   - Error responses: 0.0 (automatic failure)

### Score Interpretation

- **0.9 - 1.0**: Excellent - All criteria met, high-quality response
- **0.7 - 0.9**: Good - Most criteria met, minor issues
- **0.4 - 0.7**: Fair - Some criteria met, needs improvement
- **0.0 - 0.4**: Poor - Missing critical criteria or errors

## Agent Execution Details

### State Management

The evaluation system creates minimal state for each agent type:

- **Analysts**: Basic state with sample reports
- **Researchers**: Includes `investment_debate_state`
- **Managers**: Includes both debate states
- **Debators**: Includes `risk_debate_state` with sample debate history
- **Trader**: Includes investment plans

### Response Extraction

The system extracts responses from various locations depending on agent type:

1. Top-level keys: `market_report`, `fundamentals_report`, `investment_plan`, `final_trade_decision`, etc.
2. Debate states: `judge_decision`, `current_risky_response`, `current_safe_response`, etc.
3. Messages: Last message content from LangChain message objects

### Special Handling

- **Agents with Memory**: `bull_researcher`, `bear_researcher`, `research_manager`, `trader`, `risk_manager` require `FinancialSituationMemory` instances
- **Trader Agent**: Requires `name` parameter in node function call
- **Debators**: Responses stored in `risk_debate_state` with sender-based extraction

## Test Design Principles

### Test Prompts

Test prompts are designed to:
- Extract ticker symbols (e.g., "AAPL") and dates (e.g., "2024-12-19") automatically
- Provide context for documentation purposes
- Match real-world usage patterns

### Expected Keywords

Keywords are chosen to:
- Verify agent produces relevant output
- Check for domain-specific terminology
- Ensure agents address the core task

### Minimal State

Tests use minimal state to:
- Focus on agent functionality, not data quality
- Enable fast execution
- Reduce dependencies on external data sources

## Results Analysis

### Metrics Collected

1. **Score**: Quality score (0.0 - 1.0)
2. **Latency**: Execution time in seconds
3. **Response**: Full agent response text

### Interpreting Results

- **High scores with low latency**: Optimal performance
- **High scores with high latency**: Quality but slow (may need optimization)
- **Low scores**: Check response content and keyword matching
- **Zero scores**: Usually indicates errors or missing required keywords

### Common Issues

1. **Missing Keywords**: Agent response doesn't contain expected terms
   - **Solution**: Adjust expected keywords or improve agent prompts
   
2. **State Errors**: Agent requires state fields not provided
   - **Solution**: Update `create_minimal_state()` function
   
3. **Response Extraction Failures**: Can't find agent output
   - **Solution**: Check agent's return structure and update extraction logic

## Extending the Evaluation System

### Adding New Agents

1. Add agent configuration to `eval_config.yaml`:
   ```yaml
   - name: new_agent
     entrypoint: "agents_module.path:create_new_agent"
     requires_memory: false
     tests:
       - id: "new_agent_test_1"
         prompt: "Test prompt"
         expected:
           must_contain_keywords: ["keyword1"]
           contains: ["keyword2"]
   ```

2. Update `create_minimal_state()` if agent needs special state
3. Update response extraction logic if agent returns data in unique format

### Adding New Tests

Simply add test cases to the agent's `tests` array in `eval_config.yaml`:

```yaml
tests:
  - id: "existing_test"
    prompt: "..."
    expected: {...}
  - id: "new_test"
    prompt: "New test scenario"
    expected:
      must_contain_keywords: ["new", "keywords"]
```

### Custom Scoring

To add custom scoring logic, modify `scorers.py`:

```python
def score_response(response, expected):
    # Add custom logic here
    # ...
    return score
```

## Best Practices

1. **Keyword Selection**: Choose keywords that are specific enough to verify quality but flexible enough to allow natural language variation
2. **Test Coverage**: Include tests for both happy paths and edge cases
3. **State Design**: Keep minimal state simple but realistic
4. **Documentation**: Update this document when adding new features
5. **Regular Runs**: Run evals regularly to catch regressions

## Troubleshooting

### Common Errors

**"OPENAI_API_KEY is not set"**
- Set the environment variable or create `.env` file

**"KeyError: 'risk_debate_state'"**
- Agent requires state that isn't being created
- Check agent type detection in `run_eval.py`

**"Error: The api_key client option must be set"**
- OpenAI client initialization issue
- Verify API key is valid and accessible

**Low scores despite good responses**
- Check keyword matching (case-insensitive but exact substring)
- Verify expected keywords match agent's vocabulary
- Consider adding synonyms or alternative keywords

### Debug Mode

To debug agent execution:

1. Add print statements in `run_eval.py` around agent execution
2. Check `reports/latest.json` for full response text
3. Verify state creation matches agent requirements

## Future Improvements

Potential enhancements:

1. **LLM-based Scoring**: Use `llm_grade()` function for more nuanced evaluation
2. **Performance Benchmarks**: Track latency trends over time
3. **Regression Testing**: Compare scores across versions
4. **Integration Tests**: Test multi-agent workflows
5. **Coverage Metrics**: Track which agent code paths are tested

## References

- Agent implementations: `meridian-agents/agents_module/`
- Factory functions: See `agents_module/__init__.py`
- State definitions: `agents_module/utils/agent_states.py`
- Memory system: `agents_module/utils/memory.py`

## Contact

For questions or issues with the evaluation system, refer to the main project documentation or create an issue in the repository.

