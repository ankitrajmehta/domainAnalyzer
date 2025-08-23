"""
    Connects all modules, orchestrating the flow of data and control. 
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
import asyncio

import queryGenerator
from geminiClient.gemini import GeminiGroundedClient
from domainAnalyzer.domain_analyzer import DomainAnalyzer


class Analyzer:
    """
    Connects all modules, orchestrating the flow of data and control.
    """

    def __init__(self):
        self.domain_analyzer = DomainAnalyzer()
        self.gemini_client = GeminiGroundedClient()
        self.generate_queries = queryGenerator.generate_queries_from_url
        self.url: str = queryGenerator.DEFAULT_URL
        self.queriesToRun: int = queryGenerator.NUM_OF_QUERIES
        self.generated_queries: List[Dict[str, Any]] = []
        self.saveFileName: str = r'analysisReports\domain_analysis_prompted.json'
        self.analysis_results: List[Dict[str, Any]] = []
        self.analysis_status: str = "idle"  # idle, analyzing, complete, error

    def run_analysis(self, url: Optional[str] = None, saveResults: bool = False, queriesToRun: int = None) -> List[Dict[str, Any]]:
        """
        Runs the analysis pipeline.

        Args:
            url (Optional[str], optional): The URL to analyze. Defaults to value set in self.url.
            saveResults (bool, optional): Whether to save the results. Defaults to False.

        Returns:
            List[Dict[str, Any]]: The analysis results.
        """
        try:
            self.analysis_status = "analyzing"
            
            # generate queries
            if url is None:
                url = self.url
            self.url = url

            if queriesToRun is None:
                queriesToRun = self.queriesToRun

            # Run the async function synchronously with the specified number of queries
            generated_queries = asyncio.run(self.generate_queries(url, queriesToRun))
            self.generated_queries = generated_queries

            # analyze domains
            self.analysis_results = self.domain_analyzer.analyze_queries(generated_queries, resolve_urls=True)

            # save results
            if saveResults:
                self.domain_analyzer.save_analysis(self.analysis_results)

            self.analysis_status = "complete"
            return self.analysis_results
            
        except Exception as e:
            self.analysis_status = "error"
            print(f"Analysis error: {e}")
            raise e

    def get_status(self) -> str:
        """
        Get the current analysis status.
        
        Returns:
            str: Current status ('idle', 'analyzing', 'complete', 'error')
        """
        return self.analysis_status

    def get_all_queries(self) -> List[str]:
        """
        Get all generated query strings (for compatibility with frontend).
        
        Returns:
            List[str]: List of query strings extracted from structured queries
        """
        return [query_obj.get('query', '') for query_obj in self.generated_queries]

    def get_all_queries_structured(self) -> List[Dict[str, Any]]:
        """
        Get all generated queries with their type metadata.
        
        Returns:
            List[Dict[str, Any]]: List of structured query objects
        """
        return self.generated_queries

    def get_query_types_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about query types.
        
        Returns:
            Dict containing counts and percentages of Direct vs Generic queries
        """
        if not self.generated_queries:
            return {'total': 0, 'direct': 0, 'generic': 0, 'direct_percentage': 0, 'generic_percentage': 0}
        
        total = len(self.generated_queries)
        direct_count = sum(1 for q in self.generated_queries if q.get('type') == 'Direct')
        generic_count = total - direct_count
        
        return {
            'total': total,
            'direct': direct_count,
            'generic': generic_count,
            'direct_percentage': round((direct_count / total) * 100, 1) if total > 0 else 0,
            'generic_percentage': round((generic_count / total) * 100, 1) if total > 0 else 0
        }

    def get_query_details(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed results for a specific query.
        
        Args:
            query (str): The query string to get details for
            
        Returns:
            Optional[Dict[str, Any]]: Query details including Gemini response and domain stats
        """
        for result in self.analysis_results:
            if result['query'] == query:
                return {
                    'query': result['query'],
                    'query_type': result.get('query_type', 'Generic'),  # Include query type
                    'gemini_response': result['complete_result']['response_text'] if result['complete_result'] else '',
                    'domains': result['links'],
                    'grounding_metadata': result['complete_result']['grounding_metadata'] if result['complete_result'] else []
                }
        return None

    def get_percentage_analysis(self) -> Dict[str, Any]:
        """
        Get percentage-based analysis showing which domains appear in what percentage of queries.
        
        Returns:
            Dict[str, Any]: Aggregated results with percentages
        """
        if not self.analysis_results:
            return {'numOfQueries': 0, 'domainPercentages': []}
        
        total_queries = len(self.analysis_results)
        domain_query_appearances = defaultdict(set)  # Track which queries each domain appears in
        
        # Track domain appearances per query
        for idx, result in enumerate(self.analysis_results):
            links = result.get('links', [])
            for link in links:
                domain = link.get('domain', '')
                if domain:
                    domain_query_appearances[domain].add(idx)
        
        # Calculate percentages
        domain_percentages = []
        for domain, query_indices in domain_query_appearances.items():
            percentage = (len(query_indices) / total_queries) * 100
            domain_percentages.append({
                'domain': domain,
                'percentage': round(percentage, 1),
                'query_count': len(query_indices)
            })
        
        # Sort by percentage (descending)
        domain_percentages.sort(key=lambda x: (-x['percentage']))
        
        return {
            'numOfQueries': total_queries,
            'domainPercentages': domain_percentages
        }
    
    def get_domain_breakdown_by_type(self) -> List[Dict[str, Any]]:
        """
        Get domain breakdown showing direct vs generic query counts for each domain.
        
        Returns:
            List[Dict[str, Any]]: List of domains with their direct/generic breakdown
        """
        if not self.generated_queries:
            return []
        
        # Count domain occurrences by query type
        domain_type_counts = defaultdict(lambda: {'direct': 0, 'generic': 0, 'total': 0})
        
        for query_obj in self.generated_queries:
            query = query_obj.get('query', '')
            query_type = query_obj.get('type', 'Generic').lower()
            
            # Find corresponding analysis result
            result = next((r for r in self.analysis_results if r.get('query') == query), None)
            if not result:
                continue
                
            # Get domains from this query result
            links = result.get('links', [])
            domains_in_query = set()
            
            for link in links:
                domain = link.get('domain', '')
                if domain:
                    domains_in_query.add(domain)
            
            # Count each domain once per query
            for domain in domains_in_query:
                if query_type == 'direct':
                    domain_type_counts[domain]['direct'] += 1
                else:
                    domain_type_counts[domain]['generic'] += 1
                domain_type_counts[domain]['total'] += 1
        
        # Convert to list with percentages
        total_queries = len(self.generated_queries)
        domain_breakdown = []
        
        for domain, counts in domain_type_counts.items():
            direct_percentage = (counts['direct'] / total_queries) * 100
            generic_percentage = (counts['generic'] / total_queries) * 100
            total_percentage = (counts['total'] / total_queries) * 100
            
            domain_breakdown.append({
                'domain': domain,
                'direct_count': counts['direct'],
                'generic_count': counts['generic'],
                'total_count': counts['total'],
                'direct_percentage': round(direct_percentage, 1),
                'generic_percentage': round(generic_percentage, 1),
                'total_percentage': round(total_percentage, 1)
            })
        
        # Sort by total percentage (descending)
        domain_breakdown.sort(key=lambda x: (-x['total_percentage']))
        
        return domain_breakdown
    

    def aggregateResults(self) -> Dict[str, Any]:
        """
        Aggregates the analysis results.

        Returns:
            Dict[str, Any]: The aggregated analysis results in the format:
            {
                'numOfQueries': int,
                'totalLinkCounts': [
                    {
                        'domain': str,
                        'count': int
                    }
                    ...
                ]
            }
        """
        total_domain_counts = defaultdict(int)
        
        for result in self.analysis_results:
            # Extract domain counts from each query result
            links = result.get('links', [])
            for link in links:
                domain = link.get('domain', '')
                count = link.get('count', 0)
                if domain:
                    total_domain_counts[domain] += count
        
        # Sort domains by total count (descending)
        sorted_domains = sorted(
            total_domain_counts.items(),
            key=lambda x: (-x[1])
        )
        
        total_link_counts = [
            {
                'domain': domain,
                'count': count
            }
            for domain, count in sorted_domains
        ]
        
        return {
            'numOfQueries': len(self.analysis_results),
            'totalLinkCounts': total_link_counts
        }
        
