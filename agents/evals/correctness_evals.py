"""
Correctness Evals - Hard pass/fail checks for portfolio validity.

These evals must pass 100%. They verify structural correctness
and mathematical accuracy of the generated portfolio.
"""

from typing import Dict, Any, List, Tuple


class CorrectnessEvals:
    """Hard constraint evaluations that must all pass."""
    
    def __init__(self, portfolio: Dict[str, Any], expected: Dict[str, Any]):
        """
        Initialize with portfolio output and expected constraints.
        
        Args:
            portfolio: The generated portfolio from the agent
            expected: Expected constraints from test case
        """
        self.portfolio = portfolio
        self.expected = expected
        self.results: List[Dict[str, Any]] = []
    
    def run_all(self) -> Dict[str, Any]:
        """
        Run all correctness evals and return summary.
        
        Returns:
            Dictionary with pass/fail status and details for each eval
        """
        self.results = []
        
        # Run each eval
        self._eval_schema_valid()
        self._eval_allocation_sum()
        self._eval_stock_count()
        self._eval_risk_score_range()
        self._eval_no_duplicate_symbols()
        self._eval_country_match()
        self._eval_concentration_limit()
        self._eval_sector_diversity()
        self._eval_expected_return_range()
        
        # Calculate summary
        passed = sum(1 for r in self.results if r['passed'])
        total = len(self.results)
        all_passed = passed == total
        
        return {
            'all_passed': all_passed,
            'passed_count': passed,
            'total_count': total,
            'pass_rate': round(passed / total * 100, 1) if total > 0 else 0,
            'details': self.results
        }
    
    def _add_result(self, name: str, passed: bool, message: str, 
                    actual: Any = None, expected: Any = None):
        """Add an eval result."""
        self.results.append({
            'eval_name': name,
            'passed': passed,
            'message': message,
            'actual': actual,
            'expected': expected
        })
    
    def _eval_schema_valid(self):
        """Check that all required fields are present."""
        required_fields = ['recommendations', 'totalExpectedReturn', 'riskScore']
        missing = [f for f in required_fields if f not in self.portfolio]
        
        if missing:
            self._add_result(
                'schema_valid',
                False,
                f"Missing required fields: {missing}",
                actual=list(self.portfolio.keys()),
                expected=required_fields
            )
            return
        
        # Check recommendations structure
        if not isinstance(self.portfolio['recommendations'], list):
            self._add_result(
                'schema_valid',
                False,
                "recommendations is not a list",
                actual=type(self.portfolio['recommendations']).__name__,
                expected='list'
            )
            return
        
        # Check each recommendation has required fields
        rec_required = ['symbol', 'companyName', 'allocation', 'expectedReturn', 'sector']
        for i, rec in enumerate(self.portfolio['recommendations']):
            missing_rec = [f for f in rec_required if f not in rec]
            if missing_rec:
                self._add_result(
                    'schema_valid',
                    False,
                    f"Recommendation {i} missing fields: {missing_rec}",
                    actual=list(rec.keys()),
                    expected=rec_required
                )
                return
        
        self._add_result(
            'schema_valid',
            True,
            "All required fields present",
            actual='All fields present',
            expected=required_fields
        )
    
    def _eval_allocation_sum(self):
        """Check that allocations sum to 100%."""
        recommendations = self.portfolio.get('recommendations', [])
        if not recommendations:
            self._add_result(
                'allocation_sum',
                False,
                "No recommendations to sum",
                actual=0,
                expected=100.0
            )
            return
        
        total = sum(rec.get('allocation', 0) for rec in recommendations)
        tolerance = self.expected.get('allocation_tolerance', 0.5)
        target = self.expected.get('allocation_sum', 100.0)
        
        passed = abs(total - target) <= tolerance
        
        self._add_result(
            'allocation_sum',
            passed,
            f"Allocation sum: {total:.2f}% (tolerance: +/-{tolerance}%)",
            actual=round(total, 2),
            expected=f"{target} +/- {tolerance}"
        )
    
    def _eval_stock_count(self):
        """Check that stock count is within expected range."""
        count = len(self.portfolio.get('recommendations', []))
        min_stocks = self.expected.get('min_stocks', 4)
        max_stocks = self.expected.get('max_stocks', 6)
        
        passed = min_stocks <= count <= max_stocks
        
        self._add_result(
            'stock_count',
            passed,
            f"Stock count: {count} (expected: {min_stocks}-{max_stocks})",
            actual=count,
            expected=f"{min_stocks}-{max_stocks}"
        )
    
    def _eval_risk_score_range(self):
        """Check that risk score is within expected range for risk profile."""
        risk_score = self.portfolio.get('riskScore', -1)
        min_score = self.expected.get('risk_score_min', 0)
        max_score = self.expected.get('risk_score_max', 100)
        
        passed = min_score <= risk_score <= max_score
        
        self._add_result(
            'risk_score_range',
            passed,
            f"Risk score: {risk_score} (expected: {min_score}-{max_score})",
            actual=risk_score,
            expected=f"{min_score}-{max_score}"
        )
    
    def _eval_no_duplicate_symbols(self):
        """Check that there are no duplicate stock symbols."""
        recommendations = self.portfolio.get('recommendations', [])
        symbols = [rec.get('symbol', '') for rec in recommendations]
        unique_symbols = set(symbols)
        
        passed = len(symbols) == len(unique_symbols)
        duplicates = [s for s in symbols if symbols.count(s) > 1]
        
        self._add_result(
            'no_duplicate_symbols',
            passed,
            f"Unique symbols: {len(unique_symbols)}/{len(symbols)}" + 
            (f" Duplicates: {set(duplicates)}" if duplicates else ""),
            actual=len(unique_symbols),
            expected=len(symbols)
        )
    
    def _eval_country_match(self):
        """Check that all stocks are from the requested country."""
        recommendations = self.portfolio.get('recommendations', [])
        allowed_country = self.expected.get('allowed_country', '')
        
        if not allowed_country:
            self._add_result(
                'country_match',
                True,
                "No country constraint specified",
                actual='N/A',
                expected='N/A'
            )
            return
        
        # Check each stock's country
        mismatched = []
        for rec in recommendations:
            stock_country = rec.get('country', '')
            if stock_country and stock_country != allowed_country:
                mismatched.append(f"{rec.get('symbol')}:{stock_country}")
        
        passed = len(mismatched) == 0
        
        self._add_result(
            'country_match',
            passed,
            f"All stocks from {allowed_country}" if passed else f"Mismatched: {mismatched}",
            actual='All matched' if passed else mismatched,
            expected=allowed_country
        )
    
    def _eval_concentration_limit(self):
        """Check that no single stock exceeds concentration limit."""
        recommendations = self.portfolio.get('recommendations', [])
        max_allowed = self.expected.get('max_single_allocation', 40.0)
        
        violations = []
        for rec in recommendations:
            allocation = rec.get('allocation', 0)
            if allocation > max_allowed:
                violations.append(f"{rec.get('symbol')}:{allocation}%")
        
        passed = len(violations) == 0
        
        self._add_result(
            'concentration_limit',
            passed,
            f"Max allocation within {max_allowed}% limit" if passed else f"Violations: {violations}",
            actual='All within limit' if passed else violations,
            expected=f"<= {max_allowed}%"
        )
    
    def _eval_sector_diversity(self):
        """Check that portfolio has minimum sector diversity."""
        recommendations = self.portfolio.get('recommendations', [])
        min_sectors = self.expected.get('min_sectors', 3)
        
        sectors = set(rec.get('sector', 'unknown') for rec in recommendations)
        sector_count = len(sectors)
        
        passed = sector_count >= min_sectors
        
        self._add_result(
            'sector_diversity',
            passed,
            f"Sectors: {sector_count} ({', '.join(sectors)})",
            actual=sector_count,
            expected=f">= {min_sectors}"
        )
    
    def _eval_expected_return_range(self):
        """Check that total expected return is within reasonable range."""
        total_return = self.portfolio.get('totalExpectedReturn', 0)
        min_return = self.expected.get('expected_return_min', 5.0)
        max_return = self.expected.get('expected_return_max', 25.0)
        
        passed = min_return <= total_return <= max_return
        
        self._add_result(
            'expected_return_range',
            passed,
            f"Expected return: {total_return:.1f}% (range: {min_return}-{max_return}%)",
            actual=round(total_return, 1),
            expected=f"{min_return}-{max_return}%"
        )


def run_correctness_evals(portfolio: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to run all correctness evals.
    
    Args:
        portfolio: Generated portfolio from agent
        expected: Expected constraints from test case
        
    Returns:
        Eval results dictionary
    """
    evals = CorrectnessEvals(portfolio, expected)
    return evals.run_all()
