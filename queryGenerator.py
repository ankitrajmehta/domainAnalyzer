import crawler.modular_geo_crawler as modular_geo_crawler
import asyncio
import json
import re
from typing import List, Optional
from geminiClient.gemini import GeminiGroundedClient
from domainAnalyzer.domain_analyzer import DomainAnalyzer
from structure_recommendation.structure_analyzer import StructureAnalyzer

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

def get_structure_recommendations_prompt(structure_analysis: dict, crawled_data: dict) -> str:
    """
    Generate a prompt for getting structure recommendations from Gemini.
    
    Args:
        structure_analysis: Analysis results from StructureAnalyzer
        crawled_data: Original crawled data
        
    Returns:
        The formatted prompt string for structure recommendations
    """
    
    content_sample = crawled_data.get("clean_text", "")[:1000]  # First 1000 chars
    
    prompt = f"""You are a GEO (Generative Engine Optimization) expert. Analyze this website's structure and provide specific recommendations to improve its chances of being cited by AI systems like ChatGPT, Gemini, and Claude.

WEBSITE CONTENT SAMPLE:
{content_sample}

CURRENT STRUCTURE ANALYSIS:
- Word count: {structure_analysis['content_metrics']['word_count']}
- Heading structure: {structure_analysis['heading_structure']['distribution']}
- Semantic elements present: {structure_analysis['semantic_elements']['elements']}
- Missing semantic elements: {structure_analysis['semantic_elements']['missing_elements']}
- Meta tag issues: Missing {structure_analysis['meta_completeness']['missing_critical']}
- Structural issues found: {structure_analysis['structural_issues']}

FOCUS AREAS:
1. HTML Structure improvements for better AI parsing
2. Content organization for enhanced citability  
3. Meta tag optimization for AI understanding
4. Semantic markup enhancements

REQUIREMENTS:
- Provide 4-5 specific, actionable structure recommendations
- Focus only on technical structure improvements
- Each recommendation should explain WHY it helps with AI citations
- Be concise and implementation-focused

CRITICAL: You MUST respond with ONLY a valid JSON array. No explanations, no markdown, no additional text.

OUTPUT FORMAT - Return EXACTLY this structure:
[
  {{
    "title": "Add Semantic Article Tags",
    "description": "Implement proper article and section semantic HTML5 tags",
    "reason": "AI systems parse semantic HTML better for content understanding",
    "implementation": "Wrap main content in <article> tags and use <section> for subsections",
    "priority": "high"
  }}
]

Generate structure recommendations now:"""
    
    return prompt

def extract_recommendations_from_response(response_text: str) -> List[dict]:
    """
    Extract structure recommendations from Gemini response.
    
    Args:
        response_text: The raw response from Gemini
        
    Returns:
        List of recommendation dictionaries
    """
    recommendations = []
    
    try:
        # First, try to find JSON array in response
        json_pattern = r'\[[\s\S]*?\]'
        json_match = re.search(json_pattern, response_text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group()
            try:
                # Clean up the JSON string
                json_str = json_str.strip()
                # Remove any markdown code block markers
                json_str = re.sub(r'^```json\s*', '', json_str)
                json_str = re.sub(r'\s*```$', '', json_str)
                
                parsed_recs = json.loads(json_str)
                if isinstance(parsed_recs, list):
                    for rec in parsed_recs:
                        if isinstance(rec, dict) and "title" in rec:
                            recommendations.append({
                                "title": rec.get("title", ""),
                                "description": rec.get("description", ""),
                                "reason": rec.get("reason", ""),
                                "implementation": rec.get("implementation", ""),
                                "priority": rec.get("priority", "medium")
                            })
                return recommendations
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Attempted to parse: {json_str[:200]}...")
        
        # Fallback: Parse structured text format
        # Look for patterns like "Title:" or "1. Title:"
        title_pattern = r'(?:^|\n)\s*(?:\d+\.\s*)?(?:Title|Recommendation):\s*(.+?)(?=\n|$)'
        titles = re.findall(title_pattern, response_text, re.MULTILINE | re.IGNORECASE)
        
        if titles:
            print(f"Found {len(titles)} recommendations in text format, converting to structured format")
            for i, title in enumerate(titles[:5]):  # Limit to 5 recommendations
                recommendations.append({
                    "title": title.strip(),
                    "description": f"Recommendation {i+1} from AI analysis",
                    "reason": "Improves GEO optimization for AI citations",
                    "implementation": "Follow AI-generated guidance",
                    "priority": "medium"
                })
            return recommendations
        
        # If still no recommendations found
        print("Warning: Could not parse recommendations from AI response")
        print(f"Response preview: {response_text[:300]}...")
        return []
        
    except Exception as e:
        print(f"Error extracting recommendations: {e}")
        return []

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

async def analyze_with_structure_recommendations(url: str) -> dict:
    """
    Complete analysis including queries, domain analysis, and structure recommendations.
    
    Args:
        url: The URL to analyze
        
    Returns:
        Complete analysis results
    """
    # Step 1: Crawl website
    print(f"Crawling website: {url}")
    crawled_data = await crawl_website(url)
    if not crawled_data:
        print("Error: Cannot generate analysis - website crawling failed")
        return {}
    
    # Step 2: Generate queries
    print("Generating queries...")
    queries = await generate_queries_from_url(url)
    if not queries:
        print("Warning: No queries generated, proceeding with structure analysis only")
        queries = []
    
    # Step 3: Perform domain analysis
    print(f"Analyzing domains for {len(queries)} queries...")
    analyzer = DomainAnalyzer()
    domain_results = analyzer.analyze_queries(queries, resolve_urls=True) if queries else []
    
    # Step 4: Analyze website structure
    
    structure_analyzer = StructureAnalyzer()
    structure_analysis = structure_analyzer.analyze_for_recommendations(crawled_data)
    
    # Step 5: Get AI-powered structure recommendations
    
    structure_recommendations = []
    try:
        client = GeminiGroundedClient()
        rec_prompt = get_structure_recommendations_prompt(structure_analysis, crawled_data)
        rec_response = client.process_query(rec_prompt, resolve_urls=False)
        structure_recommendations = extract_recommendations_from_response(rec_response["response_text"])
        print(f"Generated {len(structure_recommendations)} structure recommendations")
    except Exception as e:
        print(f"Warning: Could not generate AI recommendations - {e}")
    
    # Step 6: Format results in the same format as domain_analysis_prompted.json
    # Add structure analysis to each query result
    for result in domain_results:
        result["structure_analysis"] = structure_analysis
        result["structure_recommendations"] = structure_recommendations
    
    # If no queries were generated, create a single result with just structure data
    if not domain_results:
        domain_results = [{
            "query": "Structure Analysis Only",
            "links": [],
            "complete_result": {
                "query": "Structure Analysis Only",
                "response_text": "No queries generated - structure analysis only",
                "web_search_queries": [],
                "grounding_metadata": [],
                "has_grounding": False
            },
            "structure_analysis": structure_analysis,
            "structure_recommendations": structure_recommendations,
            "website_url": url,
            "crawl_timestamp": crawled_data.get("timestamp", "")
        }]
    else:
        # Add metadata to all results
        for result in domain_results:
            result["website_url"] = url
            result["crawl_timestamp"] = crawled_data.get("timestamp", "")
    
    # Print summary
    print(f"\nAnalysis completed:")
    print(f"- Queries analyzed: {len(queries)}")
    print(f"- Structure recommendations: {len(structure_recommendations)}")
    print(f"- Critical structure issues: {len(structure_analysis.get('structural_issues', []))}")
    print(f"- Website word count: {structure_analysis.get('content_metrics', {}).get('word_count', 0)}")
    
    # Save results with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"domain_analysis_with_structure_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(domain_results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {filename}")
    except Exception as e:
        print(f"Warning: Could not save results - {e}")
    
    # Print sample recommendations
    if structure_recommendations:
        print(f"\nSample Structure Recommendations:")
        for i, rec in enumerate(structure_recommendations[:3], 1):
            print(f"{i}. {rec.get('title', 'No title')}")
    else:
        print(f"\nNo structure recommendations generated")
    
    return {
        "results": domain_results,
        "summary": {
            "queries_count": len(queries),
            "recommendations_count": len(structure_recommendations),
            "structure_issues_count": len(structure_analysis.get('structural_issues', [])),
            "word_count": structure_analysis.get('content_metrics', {}).get('word_count', 0)
        }
    }

if __name__ == "__main__":
    import sys
    
    # Check if URL is provided as command line argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = DEFAULT_URL
    
    print(f"\nIntegrated GEO Analyzer - Analyzing: {url}")
    
    # Run the complete analysis
    try:
        results = asyncio.run(analyze_with_structure_recommendations(url))
        
        if results and results.get("summary"):
            summary = results["summary"]
            print(f"\n Analysis Complete!")
            print(f" Summary: {summary['queries_count']} queries, {summary['recommendations_count']} recommendations")
            print(f"  Issues found: {summary['structure_issues_count']} structural issues")
            
        else:
            print("\nAnalysis failed - no results generated")
            
    except KeyboardInterrupt:
        print("\n  Analysis interrupted by user")
    except Exception as e:
        print(f"\n Analysis failed with error: {e}")
        
        # Fallback to original behavior for debugging
        print(f"\nFalling back to query generation only...")
        try:
            queries = asyncio.run(generate_queries_from_url(url))
            print(f"\nGenerated {len(queries)} queries:")
            print(queries)
            
            # Analyze domain
            analyzer = DomainAnalyzer()
            results = analyzer.analyze_queries(queries, resolve_urls=True)
            analyzer.save_analysis(results, "domain_analysis_prompted.json")
        except Exception as fallback_error:
            print(f"Fallback also failed: {fallback_error}")

