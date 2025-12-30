"""
LLM Judge Eval - Uses Claude to evaluate portfolio quality.

A separate Claude call evaluates the generated portfolio
for coherence, reasoning quality, and overall appropriateness.
"""

import os
import json
from typing import Dict, Any
from anthropic import Anthropic


class LLMJudgeEval:
    """Uses Claude as a judge to evaluate portfolio quality."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the LLM judge.
        
        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def evaluate(self, test_input: Dict[str, Any], portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """
        Have Claude evaluate the generated portfolio.
        
        Args:
            test_input: The input parameters used to generate the portfolio
            portfolio: The generated portfolio to evaluate
            
        Returns:
            Dictionary with scores, reasoning, and overall assessment
        """
        prompt = self._build_evaluation_prompt(test_input, portfolio)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract text from response
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content = block.text
                    break
            
            # Parse JSON from response
            result = self._parse_response(text_content)
            result['raw_response'] = text_content
            result['success'] = True
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'scores': {},
                'reasoning': '',
                'overall_score': 0
            }
    
    def _build_evaluation_prompt(self, test_input: Dict[str, Any], portfolio: Dict[str, Any]) -> str:
        """Build the evaluation prompt for the judge."""
        
        # Format recommendations for readability
        recommendations_str = ""
        for rec in portfolio.get('recommendations', []):
            recommendations_str += f"  - {rec.get('symbol')}: {rec.get('companyName')}, "
            recommendations_str += f"{rec.get('allocation')}% allocation, "
            recommendations_str += f"{rec.get('expectedReturn')}% expected return, "
            recommendations_str += f"Sector: {rec.get('sector')}\n"
        
        return f"""You are an expert financial advisor evaluating an AI-generated investment portfolio.

EVALUATION TASK:
Analyze the portfolio below and score it on multiple dimensions.

CLIENT REQUEST:
- Risk Tolerance: {test_input.get('risk_tolerance')}
- Country/Market: {test_input.get('country')}
- Investment Amount: {test_input.get('currency')} {test_input.get('investment_amount'):,}
- Investment Horizon: {test_input.get('investment_horizon_years')} years

GENERATED PORTFOLIO:
{recommendations_str}
Total Expected Return: {portfolio.get('totalExpectedReturn')}%
Risk Score: {portfolio.get('riskScore')}/100

SCORING CRITERIA (score each 1-10):

1. RISK_APPROPRIATENESS: Does the portfolio match the client's stated risk tolerance?
   - Low risk clients should have defensive stocks, lower beta, stable sectors
   - High risk clients can have growth stocks, higher volatility
   - Score 10 if perfectly matched, 1 if completely mismatched

2. DIVERSIFICATION: Is the portfolio well-diversified?
   - Consider sector spread, stock count, allocation balance
   - Score 10 for excellent diversification, 1 for poor

3. STOCK_SELECTION: Are the chosen stocks reasonable for this profile?
   - Are these reputable companies?
   - Do they fit the sector/risk criteria?
   - Score 10 for excellent choices, 1 for questionable picks

4. RETURN_REALISM: Are the expected returns realistic?
   - Typical equity returns: 7-12% annually
   - Higher risk may justify higher expectations
   - Score 10 for realistic, 1 for unrealistic projections

5. OVERALL_COHERENCE: Does the portfolio make sense as a whole?
   - Is there a clear investment thesis?
   - Would a human advisor approve this?
   - Score 10 for excellent coherence, 1 for incoherent

RESPONSE FORMAT (JSON only):
{{
  "scores": {{
    "risk_appropriateness": <1-10>,
    "diversification": <1-10>,
    "stock_selection": <1-10>,
    "return_realism": <1-10>,
    "overall_coherence": <1-10>
  }},
  "reasoning": "<2-3 sentences explaining your evaluation>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "overall_score": <1-10 average of all scores>
}}

Provide ONLY the JSON response, no additional text."""

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse the JSON response from the judge."""
        # Try to extract JSON from response
        text = text.strip()
        
        # Handle markdown code blocks
        if text.startswith('```'):
            lines = text.split('\n')
            # Remove first and last lines (code fences)
            lines = lines[1:-1] if lines[-1].strip() == '```' else lines[1:]
            # Remove 'json' identifier if present
            if lines and lines[0].strip() == 'json':
                lines = lines[1:]
            text = '\n'.join(lines)
        
        # Find JSON object
        if '{' in text and '}' in text:
            start = text.find('{')
            end = text.rfind('}') + 1
            text = text[start:end]
        
        try:
            result = json.loads(text)
            
            # Ensure required fields exist
            if 'scores' not in result:
                result['scores'] = {}
            if 'reasoning' not in result:
                result['reasoning'] = ''
            if 'overall_score' not in result:
                # Calculate from individual scores
                scores = result.get('scores', {})
                if scores:
                    result['overall_score'] = sum(scores.values()) / len(scores)
                else:
                    result['overall_score'] = 0
            
            return result
            
        except json.JSONDecodeError as e:
            return {
                'scores': {},
                'reasoning': f'Failed to parse response: {e}',
                'overall_score': 0,
                'parse_error': str(e)
            }


def run_llm_judge_eval(test_input: Dict[str, Any], portfolio: Dict[str, Any], 
                       api_key: str = None) -> Dict[str, Any]:
    """
    Convenience function to run LLM judge evaluation.
    
    Args:
        test_input: Input parameters used for generation
        portfolio: Generated portfolio from agent
        api_key: Optional Anthropic API key
        
    Returns:
        Eval results dictionary
    """
    judge = LLMJudgeEval(api_key)
    return judge.evaluate(test_input, portfolio)
