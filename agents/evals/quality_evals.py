"""
Quality Evals - Soft scoring for portfolio quality.

These evals score the portfolio on a 0-100 scale.
Target: 90%+ average score.
"""

from typing import Dict, Any, List


class QualityEvals:
    """Soft quality scoring evaluations."""
    
    def __init__(self, portfolio: Dict[str, Any], test_input: Dict[str, Any]):
        """
        Initialize with portfolio output and test input.
        
        Args:
            portfolio: The generated portfolio from the agent
            test_input: The input parameters used to generate the portfolio
        """
        self.portfolio = portfolio
        self.test_input = test_input
        self.results: List[Dict[str, Any]] = []
    
    def run_all(self) -> Dict[str, Any]:
        """
        Run all quality evals and return summary.
        
        Returns:
            Dictionary with scores and details for each eval
        """
        self.results = []
        
        # Run each eval
        self._eval_sector_balance()
        self._eval_allocation_distribution()
        self._eval_risk_return_coherence()
        self._eval_diversification_quality()
        self._eval_horizon_appropriateness()
        
        # Calculate summary
        scores = [r['score'] for r in self.results]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            'average_score': round(avg_score, 1),
            'max_possible': 100,
            'eval_count': len(self.results),
            'details': self.results
        }
    
    def _add_result(self, name: str, score: int, max_score: int, reasoning: str):
        """Add a quality eval result."""
        self.results.append({
            'eval_name': name,
            'score': score,
            'max_score': max_score,
            'percentage': round(score / max_score * 100, 1) if max_score > 0 else 0,
            'reasoning': reasoning
        })
    
    def _eval_sector_balance(self):
        """
        Score how well sectors are balanced.
        
        Scoring:
        - 5 or more sectors: 100 points
        - 4 sectors: 80 points
        - 3 sectors: 60 points
        - 2 sectors: 40 points
        - 1 sector: 20 points
        """
        recommendations = self.portfolio.get('recommendations', [])
        sectors = set(rec.get('sector', 'unknown') for rec in recommendations)
        sector_count = len(sectors)
        
        score_map = {5: 100, 4: 80, 3: 60, 2: 40, 1: 20, 0: 0}
        score = score_map.get(min(sector_count, 5), 100)
        
        self._add_result(
            'sector_balance',
            score,
            100,
            f"Portfolio covers {sector_count} sectors: {', '.join(sorted(sectors))}"
        )
    
    def _eval_allocation_distribution(self):
        """
        Score how evenly allocations are distributed.
        
        Uses coefficient of variation (CV) of allocations.
        Lower CV = more even distribution = higher score.
        
        Scoring:
        - CV < 0.2: 100 points (very even)
        - CV < 0.4: 80 points (reasonably even)
        - CV < 0.6: 60 points (moderate spread)
        - CV < 0.8: 40 points (uneven)
        - CV >= 0.8: 20 points (highly concentrated)
        """
        recommendations = self.portfolio.get('recommendations', [])
        allocations = [rec.get('allocation', 0) for rec in recommendations]
        
        if not allocations or len(allocations) < 2:
            self._add_result(
                'allocation_distribution',
                50,
                100,
                "Not enough stocks to evaluate distribution"
            )
            return
        
        mean = sum(allocations) / len(allocations)
        if mean == 0:
            self._add_result(
                'allocation_distribution',
                0,
                100,
                "Mean allocation is zero"
            )
            return
        
        variance = sum((x - mean) ** 2 for x in allocations) / len(allocations)
        std_dev = variance ** 0.5
        cv = std_dev / mean
        
        if cv < 0.2:
            score = 100
        elif cv < 0.4:
            score = 80
        elif cv < 0.6:
            score = 60
        elif cv < 0.8:
            score = 40
        else:
            score = 20
        
        alloc_str = ', '.join(f"{a:.0f}%" for a in sorted(allocations, reverse=True))
        self._add_result(
            'allocation_distribution',
            score,
            100,
            f"Allocations: [{alloc_str}], CV={cv:.2f}"
        )
    
    def _eval_risk_return_coherence(self):
        """
        Score whether expected return matches risk level.
        
        Higher risk should correlate with higher expected return.
        
        Scoring based on risk profile:
        - Low risk: 5-10% return = 100, 10-12% = 80, else 60
        - Medium risk: 8-14% return = 100, outside range = 70
        - High risk: 12-20% return = 100, <12% = 60, >20% = 80
        """
        risk_tolerance = self.test_input.get('risk_tolerance', 'Medium')
        total_return = self.portfolio.get('totalExpectedReturn', 0)
        risk_score = self.portfolio.get('riskScore', 50)
        
        if risk_tolerance == 'Low':
            if 5 <= total_return <= 10:
                score = 100
                reasoning = "Return well-matched for conservative profile"
            elif 10 < total_return <= 12:
                score = 80
                reasoning = "Return slightly high for conservative profile"
            else:
                score = 60
                reasoning = f"Return {total_return:.1f}% not ideal for conservative profile"
        
        elif risk_tolerance == 'Medium':
            if 8 <= total_return <= 14:
                score = 100
                reasoning = "Return well-matched for balanced profile"
            else:
                score = 70
                reasoning = f"Return {total_return:.1f}% outside ideal range for balanced profile"
        
        else:  # High
            if 12 <= total_return <= 20:
                score = 100
                reasoning = "Return well-matched for aggressive profile"
            elif total_return > 20:
                score = 80
                reasoning = "Return may be overly optimistic"
            else:
                score = 60
                reasoning = f"Return {total_return:.1f}% low for aggressive profile"
        
        self._add_result(
            'risk_return_coherence',
            score,
            100,
            f"{reasoning} (Risk: {risk_tolerance}, Return: {total_return:.1f}%, Score: {risk_score})"
        )
    
    def _eval_diversification_quality(self):
        """
        Score overall diversification quality.
        
        Considers:
        - Number of stocks (more is better up to 6)
        - Sector spread
        - No single stock dominates
        """
        recommendations = self.portfolio.get('recommendations', [])
        
        if not recommendations:
            self._add_result(
                'diversification_quality',
                0,
                100,
                "No recommendations to evaluate"
            )
            return
        
        # Stock count score (0-30 points)
        stock_count = len(recommendations)
        if stock_count >= 5:
            stock_score = 30
        elif stock_count == 4:
            stock_score = 25
        elif stock_count == 3:
            stock_score = 15
        else:
            stock_score = 5
        
        # Sector diversity score (0-40 points)
        sectors = set(rec.get('sector', '') for rec in recommendations)
        sector_count = len(sectors)
        sector_score = min(sector_count * 10, 40)
        
        # Concentration score (0-30 points)
        allocations = [rec.get('allocation', 0) for rec in recommendations]
        max_allocation = max(allocations) if allocations else 0
        if max_allocation <= 25:
            conc_score = 30
        elif max_allocation <= 30:
            conc_score = 25
        elif max_allocation <= 35:
            conc_score = 20
        elif max_allocation <= 40:
            conc_score = 15
        else:
            conc_score = 5
        
        total_score = stock_score + sector_score + conc_score
        
        self._add_result(
            'diversification_quality',
            total_score,
            100,
            f"Stocks: {stock_count} ({stock_score}pts), Sectors: {sector_count} ({sector_score}pts), "
            f"Max alloc: {max_allocation:.0f}% ({conc_score}pts)"
        )
    
    def _eval_horizon_appropriateness(self):
        """
        Score whether portfolio suits the investment horizon.
        
        Longer horizons can tolerate more risk/growth stocks.
        Shorter horizons should be more conservative.
        """
        horizon = self.test_input.get('investment_horizon_years', 5)
        risk_tolerance = self.test_input.get('risk_tolerance', 'Medium')
        risk_score = self.portfolio.get('riskScore', 50)
        
        # Define appropriate risk ranges based on horizon
        if horizon <= 2:
            # Short term: should be conservative regardless of stated preference
            if risk_score <= 50:
                score = 100
                reasoning = "Conservative positioning appropriate for short horizon"
            elif risk_score <= 65:
                score = 70
                reasoning = "Moderate risk acceptable for short horizon"
            else:
                score = 40
                reasoning = f"Risk score {risk_score} too high for {horizon}-year horizon"
        
        elif horizon <= 5:
            # Medium term: should match stated preference
            score = 90  # Generally appropriate
            reasoning = f"Risk level reasonable for {horizon}-year horizon"
        
        elif horizon <= 10:
            # Long term: can take more risk
            score = 95
            reasoning = f"Long horizon ({horizon} years) allows for growth focus"
        
        else:
            # Very long term: high risk acceptable
            score = 100
            reasoning = f"Very long horizon ({horizon} years) supports any risk level"
        
        self._add_result(
            'horizon_appropriateness',
            score,
            100,
            reasoning
        )


def run_quality_evals(portfolio: Dict[str, Any], test_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to run all quality evals.
    
    Args:
        portfolio: Generated portfolio from agent
        test_input: Input parameters used for generation
        
    Returns:
        Eval results dictionary
    """
    evals = QualityEvals(portfolio, test_input)
    return evals.run_all()
