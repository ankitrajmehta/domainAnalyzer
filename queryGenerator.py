import crawler.modular_geo_crawler as modular_geo_crawler
import asyncio
import json
import re
from typing import List, Optional
from geminiClient.gemini import GeminiGroundedClient
from domainAnalyzer.domain_analyzer import DomainAnalyzer

# Configuration
DEFAULT_URL = "https://ibriz.ai/" #content is extracted and queries are generated based on this
NUM_OF_QUERIES = 8

async def crawl_website(url: str) -> Optional[dict]:
    """
    Crawl a website and return the content data.
    
    Args:
        url: The URL to crawl
        
    Returns:
        Dictionary containing crawled data or None if failed
    """
    try:
        result = await modular_geo_crawler.crawl_url(url)
        
        if result and "clean_text" in result:
            return result
        else:
            print("Error: Crawling failed - no clean text found")
            return None
            
    except Exception as e:
        print(f"Error: Crawling failed - {e}")
        return None

def get_prompt(clean_text: str, num_queries: int = NUM_OF_QUERIES) -> str:
    """
    Generate a prompt for query generation.
    
    Args:
        clean_text: The cleaned text content from the website
        num_queries: Number of queries to generate
        
    Returns:
        The formatted prompt string
    """
    
    prompt = f"""You are an expert query generator specializing in creating diverse, realistic search queries. 

        Your task is to analyze the provided website content and generate relevant queries that real users might search for when looking for information related to this content.

        CONTENT TO ANALYZE:
        ```
        {clean_text}
        ```

        QUERY GENERATION REQUIREMENTS:
        1. Generate {num_queries} diverse queries covering different aspects of the content
        2. Include queries about:
        - Main topics and themes mentioned
        - Specific services, products, or offerings
        - Industry trends and related concepts
        - Company/brand name variations
        - Problem-solving queries users might have
        - Comparison queries with competitors
        - How-to and informational queries

        3. Make queries natural and varied in length (2-8 words typically)
        4. Include both specific and general queries
        5. Use different question formats (what, how, why, where, best, etc.)

        CRITICAL OUTPUT FORMAT:
        - Return ONLY a valid Python list format
        - Each query must be a string enclosed in double quotes
        - Separate queries with commas
        - NO additional text, explanations, or formatting
        - Example format: ["query 1", "query 2", "query 3"]

        Generate the queries now:"""
    
    return prompt

def extract_queries_from_response(response_text: str) -> List[str]:
    """
    Extract and validate queries from the AI response, ensuring we get a clean Python list.
    
    Args:
        response_text: The raw response from the AI
        
    Returns:
        List of cleaned query strings
    """
    queries = []
    
    try:
        # First, try to find a list pattern in the response
        list_pattern = r'\[.*?\]'
        list_matches = re.findall(list_pattern, response_text, re.DOTALL)
        
        if list_matches:
            # Take the first (hopefully only) list found
            list_str = list_matches[0]
            
            try:
                # Try to parse as JSON first (safest)
                parsed_queries = json.loads(list_str)
                if isinstance(parsed_queries, list):
                    queries = [str(q).strip().strip('"\'') for q in parsed_queries if q and str(q).strip()]
                    return queries
            except json.JSONDecodeError:
                pass
            
            try:
                # Try to evaluate as Python literal (more dangerous, but sometimes necessary)
                import ast
                parsed_queries = ast.literal_eval(list_str)
                if isinstance(parsed_queries, list):
                    queries = [str(q).strip().strip('"\'') for q in parsed_queries if q and str(q).strip()]
                    return queries
            except (ValueError, SyntaxError):
                pass
        
        # Fallback: Extract strings from quotes
        quote_patterns = [
            r'"([^"]+)"',  # Double quotes
            r"'([^']+)'",  # Single quotes
        ]
        
        for pattern in quote_patterns:
            matches = re.findall(pattern, response_text)
            if matches:
                queries.extend([match.strip() for match in matches if match.strip()])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for query in queries:
            if query not in seen and len(query) > 3:  # Filter out very short queries
                seen.add(query)
                unique_queries.append(query)
        
        queries = unique_queries
        
    except Exception as e:
        print(f"Error extracting queries: {e}")
        queries = []
    
    # Final validation and cleaning
    if not queries:
        # Last resort: split by commas and clean
        lines = response_text.split('\n')
        for line in lines:
            if ',' in line and not line.strip().startswith('['):
                potential_queries = [q.strip().strip('"\'') for q in line.split(',')]
                queries.extend([q for q in potential_queries if q and len(q) > 3])
    
    # Ensure we have a reasonable number of queries
    if len(queries) > 20:
        queries = queries[:20]  # Limit to 20 queries max
    
    return queries

async def generate_queries_from_url(url: str, num_queries: int = NUM_OF_QUERIES) -> List[str]:
    """
    Main function to crawl a URL and generate queries from its content.
    
    Args:
        url: The URL to crawl and analyze
        num_queries: Number of queries to generate
        
    Returns:
        List of generated queries
    """
    # Crawl the website
    crawled_data = await crawl_website(url)
    if not crawled_data:
        print("Error: Cannot generate queries - website crawling failed")
        return []
    
    # Initialize Gemini client
    try:
        client = GeminiGroundedClient()
    except Exception as e:
        print(f"Error: Failed to initialize Gemini client - {e}")
        return []
    

    prompt = get_prompt(crawled_data["clean_text"], num_queries)
    
    try:
        response = client.process_query(prompt, resolve_urls=False, use_grounding=False)

    except Exception as e:
        print(f"Error: Failed to get AI response - {e}")
        return []
    
    
    queries = extract_queries_from_response(response["response_text"])
    
    return queries

async def generate_queries_from_crawledData(crawled_data: dict, num_queries: int = NUM_OF_QUERIES) -> List[str]:
    """
    Main function to crawl a URL and generate queries from its content.
    
    Args:
        crawled_data: The crawled data dictionary
        num_queries: Number of queries to generate
        
    Returns:
        List of generated queries
    """
    # Crawl the website
    if not crawled_data:
        print("Error: Cannot generate queries - website crawling failed")
        return []
    
    # Initialize Gemini client
    try:
        client = GeminiGroundedClient()
    except Exception as e:
        print(f"Error: Failed to initialize Gemini client - {e}")
        return []
    

    prompt = get_prompt(crawled_data["clean_text"], num_queries)
    
    try:
        response = client.process_query(prompt, resolve_urls=False, use_grounding=False)

    except Exception as e:
        print(f"Error: Failed to get AI response - {e}")
        return []
    
    
    queries = extract_queries_from_response(response["response_text"])
    
    return queries

if __name__ == "__main__":
        
    url = DEFAULT_URL
    
    print(f"\nQuery Generator - Analyzing: {url}")
    
    # Generate queries
    queries = asyncio.run(generate_queries_from_url(url))
    
    print(f"\nGenerated {len(queries)} queries:")

    print(queries)

    # Analyze domain
    analyzer = DomainAnalyzer()
    results = analyzer.analyze_queries(queries, resolve_urls=True)
    analyzer.save_analysis(results, r"analysisReports\domain_analysis_prompted.json")

