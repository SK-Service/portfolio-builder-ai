"""
Eval Runner - Orchestrates evaluation of the portfolio agent.

Usage:
    python eval_runner.py TC_USA_LOW              # Run single test case
    python eval_runner.py TC_USA_LOW TC_USA_MED   # Run multiple test cases
    python eval_runner.py --all                   # Run all test cases
    python eval_runner.py --list                  # List available test cases

Results are saved to eval_results/ directory with timestamps.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Verify required environment variables
required_vars = ['GOOGLE_APPLICATION_CREDENTIALS', 'ANTHROPIC_API_KEY']
missing = [v for v in required_vars if not os.getenv(v)]
if missing:
    print(f"ERROR: Missing environment variables: {missing}")
    print("Add them to your .env file")
    sys.exit(1)

# Initialize Firebase before importing agent
from firebase_admin import credentials, initialize_app, _apps

if not _apps:
    cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if Path(cred_path).exists():
        cred = credentials.Certificate(cred_path)
        initialize_app(cred)
    else:
        print(f"ERROR: Credentials file not found: {cred_path}")
        sys.exit(1)

# Import after Firebase init
from src.agent.anthropic_service import AnthropicService
from evals.correctness_evals import run_correctness_evals
from evals.quality_evals import run_quality_evals
from evals.llm_judge_eval import run_llm_judge_eval


class EvalRunner:
    """Orchestrates running evaluations against the portfolio agent."""
    
    def __init__(self):
        """Initialize the eval runner."""
        self.test_cases_dir = Path(__file__).parent / "test_cases"
        self.results_dir = Path(__file__).parent / "eval_results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize agent service
        alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY', '')
        fred_key = os.getenv('FRED_API_KEY', '')
        self.agent = AnthropicService(
            alpha_vantage_key=alpha_vantage_key,
            fred_key=fred_key
        )
    
    def list_test_cases(self) -> List[str]:
        """List all available test case IDs."""
        test_files = self.test_cases_dir.glob("*.json")
        return sorted([f.stem for f in test_files])
    
    def load_test_case(self, test_id: str) -> Dict[str, Any]:
        """Load a test case by ID."""
        test_file = self.test_cases_dir / f"{test_id}.json"
        if not test_file.exists():
            raise FileNotFoundError(f"Test case not found: {test_id}")
        
        with open(test_file, 'r') as f:
            return json.load(f)
    
    def run_single_eval(self, test_id: str, skip_llm_judge: bool = False) -> Dict[str, Any]:
        """
        Run evaluation for a single test case.
        
        Args:
            test_id: Test case ID (e.g., TC_USA_LOW)
            skip_llm_judge: If True, skip the LLM judge eval (saves API cost)
            
        Returns:
            Complete evaluation results
        """
        print(f"\n{'='*60}")
        print(f"RUNNING EVAL: {test_id}")
        print(f"{'='*60}")
        
        # Load test case
        test_case = self.load_test_case(test_id)
        test_input = test_case['input']
        expected = test_case['expected']
        
        print(f"\nTest: {test_case.get('description', test_id)}")
        print(f"Input: {test_input['risk_tolerance']} risk, {test_input['country']}, "
              f"{test_input['currency']} {test_input['investment_amount']:,}, "
              f"{test_input['investment_horizon_years']} years")
        
        # Generate portfolio
        print("\nGenerating portfolio...")
        start_time = datetime.now()
        
        try:
            portfolio = self.agent.generate_portfolio(
                risk_tolerance=test_input['risk_tolerance'],
                investment_horizon_years=test_input['investment_horizon_years'],
                country=test_input['country'],
                investment_amount=test_input['investment_amount'],
                currency=test_input['currency']
            )
            generation_time = (datetime.now() - start_time).total_seconds()
            print(f"Portfolio generated in {generation_time:.1f}s")
            
        except Exception as e:
            print(f"ERROR generating portfolio: {e}")
            return {
                'test_id': test_id,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        # Run correctness evals
        print("\nRunning correctness evals...")
        correctness_results = run_correctness_evals(portfolio, expected)
        print(f"  Correctness: {correctness_results['passed_count']}/{correctness_results['total_count']} passed "
              f"({correctness_results['pass_rate']}%)")
        
        # Run quality evals
        print("\nRunning quality evals...")
        quality_results = run_quality_evals(portfolio, test_input)
        print(f"  Quality: {quality_results['average_score']}/100 average score")
        
        # Run LLM judge eval (optional)
        llm_judge_results = None
        if not skip_llm_judge:
            print("\nRunning LLM judge eval...")
            llm_judge_results = run_llm_judge_eval(test_input, portfolio)
            if llm_judge_results.get('success'):
                print(f"  LLM Judge: {llm_judge_results.get('overall_score', 0):.1f}/10")
            else:
                print(f"  LLM Judge: ERROR - {llm_judge_results.get('error', 'Unknown error')}")
        else:
            print("\nSkipping LLM judge eval (--skip-judge flag)")
        
        # Compile results
        result = {
            'test_id': test_id,
            'description': test_case.get('description', ''),
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'generation_time_seconds': generation_time,
            'input': test_input,
            'expected': expected,
            'portfolio': portfolio,
            'correctness': correctness_results,
            'quality': quality_results,
            'llm_judge': llm_judge_results
        }
        
        # Print summary
        self._print_summary(result)
        
        return result
    
    def run_multiple_evals(self, test_ids: List[str], skip_llm_judge: bool = False) -> Dict[str, Any]:
        """
        Run evaluations for multiple test cases.
        
        Args:
            test_ids: List of test case IDs
            skip_llm_judge: If True, skip LLM judge evals
            
        Returns:
            Aggregated results
        """
        results = []
        
        for test_id in test_ids:
            try:
                result = self.run_single_eval(test_id, skip_llm_judge)
                results.append(result)
            except FileNotFoundError as e:
                print(f"WARNING: {e}")
                results.append({
                    'test_id': test_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Aggregate results
        aggregate = self._aggregate_results(results)
        
        # Print aggregate summary
        self._print_aggregate_summary(aggregate)
        
        # Save results
        self._save_results(aggregate)
        
        return aggregate
    
    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from multiple test runs."""
        successful = [r for r in results if r.get('success', False)]
        
        if not successful:
            return {
                'timestamp': datetime.now().isoformat(),
                'total_tests': len(results),
                'successful_tests': 0,
                'failed_tests': len(results),
                'results': results
            }
        
        # Calculate averages
        correctness_rates = [r['correctness']['pass_rate'] for r in successful]
        quality_scores = [r['quality']['average_score'] for r in successful]
        generation_times = [r['generation_time_seconds'] for r in successful]
        
        llm_scores = []
        for r in successful:
            if r.get('llm_judge') and r['llm_judge'].get('success'):
                llm_scores.append(r['llm_judge'].get('overall_score', 0))
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(results),
            'successful_tests': len(successful),
            'failed_tests': len(results) - len(successful),
            'averages': {
                'correctness_pass_rate': round(sum(correctness_rates) / len(correctness_rates), 1),
                'quality_score': round(sum(quality_scores) / len(quality_scores), 1),
                'llm_judge_score': round(sum(llm_scores) / len(llm_scores), 1) if llm_scores else None,
                'generation_time_seconds': round(sum(generation_times) / len(generation_times), 1)
            },
            'results': results
        }
    
    def _print_summary(self, result: Dict[str, Any]):
        """Print summary for a single eval run."""
        print(f"\n{'-'*40}")
        print("EVAL SUMMARY")
        print(f"{'-'*40}")
        
        if not result.get('success'):
            print(f"FAILED: {result.get('error', 'Unknown error')}")
            return
        
        # Correctness details
        print("\nCorrectness Evals:")
        for detail in result['correctness']['details']:
            status = "PASS" if detail['passed'] else "FAIL"
            print(f"  [{status}] {detail['eval_name']}: {detail['message']}")
        
        # Quality details
        print("\nQuality Evals:")
        for detail in result['quality']['details']:
            print(f"  [{detail['score']}/{detail['max_score']}] {detail['eval_name']}: {detail['reasoning']}")
        
        # LLM Judge details
        if result.get('llm_judge') and result['llm_judge'].get('success'):
            print("\nLLM Judge Eval:")
            scores = result['llm_judge'].get('scores', {})
            for name, score in scores.items():
                print(f"  [{score}/10] {name}")
            print(f"\n  Reasoning: {result['llm_judge'].get('reasoning', 'N/A')}")
            
            strengths = result['llm_judge'].get('strengths', [])
            if strengths:
                print(f"  Strengths: {', '.join(strengths)}")
            
            weaknesses = result['llm_judge'].get('weaknesses', [])
            if weaknesses:
                print(f"  Weaknesses: {', '.join(weaknesses)}")
    
    def _print_aggregate_summary(self, aggregate: Dict[str, Any]):
        """Print aggregate summary for multiple eval runs."""
        print(f"\n{'='*60}")
        print("AGGREGATE RESULTS")
        print(f"{'='*60}")
        
        print(f"\nTests: {aggregate['successful_tests']}/{aggregate['total_tests']} successful")
        
        if aggregate.get('averages'):
            avgs = aggregate['averages']
            print(f"\nAverages:")
            print(f"  Correctness Pass Rate: {avgs['correctness_pass_rate']}%")
            print(f"  Quality Score: {avgs['quality_score']}/100")
            if avgs.get('llm_judge_score') is not None:
                print(f"  LLM Judge Score: {avgs['llm_judge_score']}/10")
            print(f"  Generation Time: {avgs['generation_time_seconds']}s")
        
        # List any failures
        failures = [r for r in aggregate['results'] if not r.get('success')]
        if failures:
            print(f"\nFailed Tests:")
            for f in failures:
                print(f"  - {f['test_id']}: {f.get('error', 'Unknown error')}")
    
    def _save_results(self, results: Dict[str, Any]):
        """Save results to a JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine filename based on number of tests
        if results['total_tests'] == 1:
            test_id = results['results'][0]['test_id']
            filename = f"{test_id}_{timestamp}.json"
        else:
            filename = f"batch_{results['total_tests']}tests_{timestamp}.json"
        
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {filepath}")


def main():
    """Main entry point for eval runner."""
    parser = argparse.ArgumentParser(
        description="Run evaluations against the portfolio agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python eval_runner.py TC_USA_LOW              # Run single test
    python eval_runner.py TC_USA_LOW TC_EU_MED    # Run multiple tests
    python eval_runner.py --all                   # Run all tests
    python eval_runner.py --all --skip-judge      # Run all, skip LLM judge
    python eval_runner.py --list                  # List available tests
        """
    )
    
    parser.add_argument(
        'test_ids',
        nargs='*',
        help='Test case IDs to run (e.g., TC_USA_LOW TC_USA_MED)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all available test cases'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available test cases'
    )
    parser.add_argument(
        '--skip-judge',
        action='store_true',
        help='Skip LLM judge evaluation (saves API cost)'
    )
    
    args = parser.parse_args()
    
    runner = EvalRunner()
    
    # List test cases
    if args.list:
        print("Available test cases:")
        for tc in runner.list_test_cases():
            test_case = runner.load_test_case(tc)
            print(f"  {tc}: {test_case.get('description', '')}")
        return
    
    # Determine which tests to run
    if args.all:
        test_ids = runner.list_test_cases()
    elif args.test_ids:
        test_ids = args.test_ids
    else:
        parser.print_help()
        return
    
    # Run evals
    if len(test_ids) == 1:
        result = runner.run_single_eval(test_ids[0], skip_llm_judge=args.skip_judge)
        # Save single result too
        runner._save_results({
            'timestamp': datetime.now().isoformat(),
            'total_tests': 1,
            'successful_tests': 1 if result.get('success') else 0,
            'failed_tests': 0 if result.get('success') else 1,
            'results': [result]
        })
    else:
        runner.run_multiple_evals(test_ids, skip_llm_judge=args.skip_judge)


if __name__ == "__main__":
    main()
