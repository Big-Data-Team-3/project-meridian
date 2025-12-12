from openai import OpenAI

# Initialize client only if needed for LLM grading
_client = None

def get_client():
    """Lazy initialization of OpenAI client."""
    global _client
    if _client is None:
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it before using LLM grading: export OPENAI_API_KEY=your-api-key"
            )
        _client = OpenAI(api_key=api_key)
    return _client

# Simple rule-based scoring
def score_response(response, expected):
    """
    Score an agent response based on expected criteria.
    
    Args:
        response: The agent's response text
        expected: Dictionary with scoring criteria:
            - contains: List of keywords that should be present (optional, -0.2 per missing)
            - must_contain_keywords: List of required keywords (optional, -0.3 per missing)
    
    Returns:
        Score between 0.0 and 1.0
    """
    if not response:
        return 0.0
    
    # Penalize error responses heavily
    if response.startswith("Error:") or "KeyError" in response or "AttributeError" in response:
        return 0.0
    
    score = 1.0
    text = response.lower()

    # Check for required keywords first (more important)
    if "must_contain_keywords" in expected:
        keywords = expected["must_contain_keywords"]
        if not isinstance(keywords, list):
            keywords = [keywords]
        
        missing_count = 0
        found_count = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text:
                found_count += 1
            else:
                missing_count += 1
        
        # Deduct 0.3 per missing required keyword, but give bonus for finding all
        deduction = missing_count * 0.3
        score -= deduction
        
        # Small bonus if all required keywords found
        if missing_count == 0:
            score = min(score + 0.1, 1.0)

    # Check for optional keywords (contains) - less penalty
    if "contains" in expected:
        keywords = expected["contains"]
        if not isinstance(keywords, list):
            keywords = [keywords]
        
        missing_count = 0
        found_count = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text:
                found_count += 1
            else:
                missing_count += 1
        
        # Deduct 0.15 per missing optional keyword (less severe)
        deduction = missing_count * 0.15
        score -= deduction
        
        # Small bonus if most optional keywords found
        if found_count >= len(keywords) * 0.7:  # 70% or more found
            score = min(score + 0.05, 1.0)

    # Bonus for longer, more detailed responses (indicates agent actually ran)
    if len(response) > 100 and not response.startswith("{"):
        score = min(score + 0.1, 1.0)
    elif len(response) > 50:
        score = min(score + 0.05, 1.0)

    return max(score, 0.0)

# Optional: LLM judge
def llm_grade(response, rubric):
    """
    Use an LLM to grade a response based on a rubric.
    
    Args:
        response: The agent's response text
        rubric: Description of what makes a good response
    
    Returns:
        Score between 0.0 and 1.0
    """
    try:
        client = get_client()
        
        grading_prompt = f"""You are grading an agent response.

Response:
{response}

Rubric:
{rubric}

Rate the response on a scale of 0.0 to 1.0, where:
- 1.0 = Excellent, fully meets all criteria
- 0.7-0.9 = Good, meets most criteria
- 0.4-0.6 = Fair, meets some criteria
- 0.0-0.3 = Poor, fails to meet criteria

Respond with ONLY a number between 0.0 and 1.0 (e.g., 0.85)."""

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a fair and objective grader."},
                {"role": "user", "content": grading_prompt}
            ],
            temperature=0.0,
            max_tokens=10
        )

        score_text = completion.choices[0].message.content.strip()
        # Extract number from response
        import re
        match = re.search(r'(\d+\.?\d*)', score_text)
        if match:
            score = float(match.group(1))
            # Normalize to 0-1 range if needed
            if score > 1.0:
                score = score / 10.0 if score <= 10.0 else 1.0
            return max(0.0, min(1.0, score))
        else:
            return 0.0
    except Exception as e:
        print(f"Error in LLM grading: {str(e)}")
        return 0.0
