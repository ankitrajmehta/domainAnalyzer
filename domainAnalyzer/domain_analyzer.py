"""
Domain Analysis Tool for Gemini Grounded Responses
==================================================

This script analyzes multiple queries using GeminiGroundedClient and generates
domain frequency statistics to understand which sources are most commonly cited.

Output Format:
[
    {
        "query": "What's the latest news?",
        "links": [
            {"domain": "cnn.com", "count": 5},
            {"domain": "bbc.com", "count": 3},
            {"domain": "reuters.com", "count": 2}
        ],
        "complete_result": {...} (Full response by gemini.py)    
    },
    ...
]
"""

import json
import re
from collections import defaultdict
from typing import Dict, List, Any
from urllib.parse import urlparse
from geminiClient.gemini import GeminiGroundedClient





class DomainAnalyzer:
    """
    Analyzes domain frequency from Gemini grounded responses.
    Handles domain normalization and counting across multiple queries.
    """
    
    def __init__(self, gemini_client: GeminiGroundedClient = None):
        """
        Initialize the domain analyzer.
        
        Args:
            gemini_client: Optional pre-configured GeminiGroundedClient instance
        """
        self.client = gemini_client or GeminiGroundedClient()
    
    def normalize_domain(self, domain: str) -> str:
        """
        Normalize domain names to handle variations and subdomains.
        
        Examples:
        - "www.cnn.com" -> "cnn.com"
        - "en.wikipedia.org" -> "wikipedia.org" 
        - "finance.yahoo.com" -> "yahoo.com"
        - "news.google.com" -> "google.com"
        
        Args:
            domain: Raw domain string
            
        Returns:
            Normalized domain string
        """
        if not domain:
            return ""
        
        # Remove www prefix
        domain = re.sub(r'^www\.', '', domain.lower())
        
        # Handle common subdomain patterns
        # Keep only the main domain for well-known sites
        domain_parts = domain.split('.')
        
        if len(domain_parts) >= 3:
            # For domains like "en.wikipedia.org", "finance.yahoo.com"
            # Keep the last two parts (wikipedia.org, yahoo.com)
            # But handle special cases like "co.uk", "com.au"

            # Define sets for efficient lookup
            COUNTRY_CODES = {
                'uk', 'au', 'ca', 'in', 'np', 'nz', 'za', 'br', 'mx', 'ar', 'cl', 'pe', 'co',
                'jp', 'kr', 'cn', 'hk', 'sg', 'my', 'th', 'id', 'ph', 'vn', 'tw',
                'de', 'fr', 'it', 'es', 'nl', 'be', 'at', 'ch', 'se', 'no', 'dk', 'fi',
                'pl', 'cz', 'hu', 'sk', 'si', 'hr', 'rs', 'bg', 'ro', 'gr', 'cy', 'mt',
                'ie', 'pt', 'lu', 'li', 'is', 'lv', 'lt', 'ee', 'ua', 'ru', 'by', 'md',
                'eg', 'il', 'tr', 'sa', 'ae', 'qa', 'kw', 'bh', 'om', 'jo', 'lb', 'ir',
                'ke', 'ng', 'gh', 'ma', 'tn', 'dz', 'ly', 'sd', 'et', 'tz', 'ug', 'rw',
                'bd', 'pk', 'lk', 'mm', 'la', 'kh', 'bn', 'mv'
            }
            SECOND_LEVEL_DOMAINS = {
                'co', 'com', 'org', 'net', 'edu', 'gov', 'mil', 'ac', 'sch', 'uni',
                'info', 'biz', 'name', 'pro', 'museum', 'travel', 'mobi', 'tel',
                'jobs', 'cat', 'asia', 'post', 'geo', 'int'
            }

            if domain_parts[-1] in COUNTRY_CODES and domain_parts[-2] in SECOND_LEVEL_DOMAINS:
                # Keep last 3 parts for domains like "bbc.co.uk"
                return '.'.join(domain_parts[-3:])
            else:
                # Keep last 2 parts for most cases
                return '.'.join(domain_parts[-2:])
        
        return domain
    
    def extract_domains_from_response(self, response_data: Dict[str, Any]) -> List[str]:
        """
        Extract all domains from a single query response.
        
        Args:
            response_data: Response from GeminiGroundedClient.process_query()
            
        Returns:
            List of normalized domain names
        """
        domains = []
        
        if not response_data.get('grounding_metadata'):
            return domains
        
        for segment in response_data['grounding_metadata']:
            for link in segment.get('links', []):
                # Try to get domain from title first (more reliable)
                title_domain = link.get('title', '')
                if title_domain:
                    normalized = self.normalize_domain(title_domain)
                    if normalized:
                        domains.append(normalized)
                        continue
                
                # Fallback to extracting from actual_url
                actual_url = link.get('actual_url')
                if actual_url:
                    try:
                        parsed = urlparse(actual_url)
                        normalized = self.normalize_domain(parsed.netloc)
                        if normalized:
                            domains.append(normalized)
                    except Exception:
                        pass
        
        return domains
    
    def count_domains(self, domains: List[str]) -> List[Dict[str, Any]]:
        """
        Count domain occurrences and sort by frequency.
        
        Args:
            domains: List of domain names
            
        Returns:
            Sorted list of {"domain": str, "count": int} dictionaries
        """
        domain_counts = defaultdict(int)
        
        for domain in domains:
            domain_counts[domain] += 1
        
        # Sort by count (descending)
        sorted_domains = sorted(
            domain_counts.items(), 
            key=lambda x: (-x[1])
        )
        
        return [{"domain": domain, "count": count} for domain, count in sorted_domains]
    
    def analyze_queries(self, queries: List[Dict[str, Any]], resolve_urls: bool = True) -> List[Dict[str, Any]]:
        """
        Analyze multiple queries and generate domain frequency statistics.

        Args:
            queries: List of query dictionaries with 'query' and 'type' fields
            resolve_urls: Whether to resolve actual URLs
            
        Returns:
            List of analysis results in the specified format
        """
        results = []
        
        print(f"Analyzing {len(queries)} structured queries...")
        
        for i, query_obj in enumerate(queries, 1):
            
            query_text = query_obj.get('query', '') if isinstance(query_obj, dict) else str(query_obj)
            query_type = query_obj.get('type', 'Generic') if isinstance(query_obj, dict) else 'Generic'
            
            print(f"\nProcessing query {i}/{len(queries)} [{query_type}]: {query_text[:50]}...")
            
            try:
                response_data = self.client.process_query(query_text, resolve_urls=resolve_urls)
                
                domains = self.extract_domains_from_response(response_data)
                
                domain_stats = self.count_domains(domains)
                
                results.append({
                    "query": query_text,
                    "query_type": query_type,  # Store the query type for future use
                    "links": domain_stats,
                    "complete_result": response_data
                })
                
                print(f"Found {len(domains)} total domain references, {len(domain_stats)} unique domains")
                
            except Exception as e:
                print(f"Error processing query '{query_text}': {e}")
                results.append({
                    "query": query_text,
                    "query_type": query_type,
                    "links": [],
                    "complete_result": None
                })
        
        return results
    
    def save_analysis(self, results: List[Dict[str, Any]], filename: str = r"analysisReports\domain_analysis_prompted.json"):
        """
        Save the analysis results to a JSON file.
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nAnalysis saved to {filename}")
    

def main():
    """
    Main function with example queries for domain analysis.
    """
    # Example structured queries
    queries = [
        {"query": "What companies are leading in bridging AI and blockchain technology", "type": "Generic"},
        {"query": "Tell me about iBriz.ai", "type": "Direct"},
        {"query": "What kind of markets does iBriz.ai operate in?", "type": "Direct"}
    ]
    
    analyzer = DomainAnalyzer()

    results = analyzer.analyze_queries(queries, resolve_urls=True)
    
    analyzer.save_analysis(results, "domain_analysis.json")

    
    print(f"\nCompleted analysis of {len(queries)} queries")

    
if __name__ == "__main__":
    main()
