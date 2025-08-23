import crawler.modular_geo_crawler as modular_geo_crawler
import asyncio
import json
import re
from typing import List, Optional, Dict, Any
from geminiClient.gemini import GeminiGroundedClient
from domainAnalyzer.domain_analyzer import DomainAnalyzer
from structure_recommendation.structure_analyzer import StructureAnalyzer
from pydantic import BaseModel
from typing import Literal

# Pydantic models for structured output. Defines the response model for query generation by gemini
class QueryItem(BaseModel):
    query: str
    type: Literal["Direct", "Generic"]

class QueryResponse(BaseModel):
    queries: List[QueryItem]

# Configuration
DEFAULT_URL = "https://ibriz.ai/" #content is extracted and queries are generated based on this
NUM_OF_QUERIES = 3

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
    Generate a prompt for structured query generation with type classification.
    
    Args:
        clean_text: The cleaned text content from the website
        num_queries: Number of queries to generate
        
    Returns:
        The formatted prompt string
    """
    
    prompt = f"""You are an expert query generator specializing in creating diverse, realistic search queries with type classification.

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
   - Company/brand name variations (if applicable)
   - Problem-solving queries users might have
   - Comparison queries with competitors
   - How-to and informational queries

3. For each query, classify it as either:
   - "Direct": Query explicitly mentions the SPECIFIC company/brand name that OWNS this website (the entity whose website you're analyzing)
   - "Generic": Query discusses general concepts, technologies, industry topics, or even specific products WITHOUT mentioning the website owner's company/brand name

CRITICAL CLASSIFICATION RULES:
- "Direct" queries MUST mention the actual company/brand that owns this website
- Just mentioning a product category, technology, or service is NOT Direct - it's Generic
- Only queries that include the website owner's specific company/brand name are Direct
- When in doubt, classify as Generic

EXAMPLES:
- If analyzing the iBriz.ai website:
  * "What is iBriz.ai?" → Direct (mentions the website owner's company name)
  * "iBriz blockchain solutions" → Direct (mentions the website owner's company name)  
  * "AI blockchain integration platforms" → Generic (general industry topic, no company name)
  * "Best blockchain consulting services" → Generic (general service category)
  * "OpenAI GPT models" → Generic (mentions different company, not the website owner)
  * "Enterprise AI solutions" → Generic (general product category)

4. Make queries natural and varied in length (2-8 words typically)
5. Use different question formats (what, how, why, where, best, etc.)

CRITICAL OUTPUT FORMAT:
Return ONLY a valid JSON object in this exact structure:
{{
  "queries": [
    {{
      "query": "query text here",
      "type": "Direct"
    }},
    {{
      "query": "another query here", 
      "type": "Generic"
    }}
  ]
}}

Generate the structured response now:"""
    
    return prompt


# Simple fallback queries for when all structured attempts fail
def get_fallback_queries(num_queries: int = 3) -> List[Dict[str, Any]]:
    """
    Generate simple fallback queries when structured output completely fails.
    
    Args:
        num_queries: Number of fallback queries to generate
        
    Returns:
        List of basic query dictionaries
    """
    fallback_queries = [
        {"query": "Failed query generation process. Return blank", "type": "Generic"}
    ]
    
    # Return the requested number of queries (up to available)
    return fallback_queries[:min(num_queries, len(fallback_queries))]

async def generate_queries_from_url(url: str, num_queries: int = NUM_OF_QUERIES) -> List[Dict[str, Any]]:
    """
    Main function to crawl a URL and generate structured queries from its content.
    
    Args:
        url: The URL to crawl and analyze
        num_queries: Number of queries to generate
        
    Returns:
        List of query dictionaries with 'query' and 'type' fields
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
    
    # Try structured output generation with retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}: Generating structured queries...")
            
            response = client.generate_response(
                prompt, 
                use_grounding=False,
                structured_output=True,
                response_schema=QueryResponse
            )
            
            # Parse the structured response
            if hasattr(response, 'parsed') and response.parsed:
                queries = []
                for query_item in response.parsed.queries:
                    queries.append({
                        "query": query_item.query,
                        "type": query_item.type
                    })
                print(f"Successfully generated {len(queries)} structured queries using Pydantic parsing")
                return queries
            else:
                print(f"Attempt {attempt + 1} failed: No parsed structured response")
                if attempt < max_retries - 1:
                    print("Retrying structured output generation...")
                    continue
        
        except Exception as e:
            print(f"Attempt {attempt + 1} failed with error: {e}")
            if attempt < max_retries - 1:
                print("Retrying structured output generation...")
                continue
    
    # If all structured attempts failed, use simple fallback
    print("All structured output attempts failed. Using simple fallback queries.")
    return get_fallback_queries(num_queries)




# Not used. Enable if running this file as main
# def get_structure_recommendations_prompt(structure_analysis: dict, crawled_data: dict) -> str:
#     """
#     Generate a prompt for getting comprehensive GEO recommendations from Gemini.
    
#     Args:
#         structure_analysis: Analysis results from StructureAnalyzer
#         crawled_data: Original crawled data
        
#     Returns:
#         The formatted prompt string for structure recommendations
#     """
    
#     content_sample = crawled_data.get("clean_text", "")[:800]  # First 800 chars
#     missing_elements = structure_analysis.get('semantic_elements', {}).get('missing_elements', [])
#     missing_meta = structure_analysis.get('meta_completeness', {}).get('missing_critical', [])
#     structural_issues = structure_analysis.get('structural_issues', [])
    
#     prompt = f"""You are a professional website optimization consultant. Analyze this specific website and provide 4 customized recommendations based on the actual content and issues found.

# WEBSITE CONTENT SAMPLE:
# "{content_sample}"

# SPECIFIC ISSUES IDENTIFIED:
# - Missing semantic elements: {missing_elements}
# - Missing critical meta tags: {missing_meta}  
# - Structural problems found: {len(structural_issues)}
# - Content length: {structure_analysis.get('content_metrics', {}).get('word_count', 0)} words
# - H1 headings: {structure_analysis.get('heading_structure', {}).get('h1_count', 0)}
# - Total headings: {structure_analysis.get('heading_structure', {}).get('total', 0)}

# Based on this SPECIFIC analysis, create 4 targeted recommendations. DO NOT use generic examples. Analyze the actual content and issues.

# Return ONLY a JSON array with this structure:
# [
#   {{
#     "title": "Specific recommendation based on analysis",
#     "description": "Detailed explanation of the specific issue found and why fixing it will help this particular website",
#     "solution": "Concrete steps to fix this specific issue",
#     "priority": "High or Medium"
#   }}
# ]

# IMPORTANT: 
# - Base recommendations on the actual content sample provided
# - Address the specific missing elements and meta tags listed
# - Don't use generic placeholder text
# - Focus on the most impactful improvements for THIS website"""
    
#     return prompt

# Not used. Enable if running this file as main
# def extract_recommendations_from_response(response_text: str) -> List[dict]:
    # """
    # Extract structure recommendations from Gemini response.
    
    # Args:
    #     response_text: The raw response from Gemini
        
    # Returns:
    #     List of recommendation dictionaries
    # """
    # recommendations = []
    
    # try:
    #     # First, try to find JSON array in response
    #     json_pattern = r'\[[\s\S]*?\]'
    #     json_match = re.search(json_pattern, response_text, re.DOTALL)
        
    #     if json_match:
    #         json_str = json_match.group()
    #         try:
    #             # Clean up the JSON string
    #             json_str = json_str.strip()
    #             # Remove any markdown code block markers
    #             json_str = re.sub(r'^```json\s*', '', json_str)
    #             json_str = re.sub(r'\s*```$', '', json_str)
                
    #             parsed_recs = json.loads(json_str)
    #             if isinstance(parsed_recs, list):
    #                 for rec in parsed_recs:
    #                     if isinstance(rec, dict) and "title" in rec:
    #                         recommendations.append({
    #                             "title": rec.get("title", ""),
    #                             "description": rec.get("description", ""),
    #                             "solution": rec.get("solution", rec.get("code", "")),  # Support both new and old format
    #                             "priority": rec.get("priority", "Medium")
    #                         })
    #             return recommendations
    #         except json.JSONDecodeError as e:
    #             print(f"JSON decode error: {e}")
    #             print(f"Attempted to parse: {json_str[:200]}...")
        
    #     # Fallback: Parse structured text format
    #     # Look for patterns like "Title:" or "1. Title:"
    #     title_pattern = r'(?:^|\n)\s*(?:\d+\.\s*)?(?:Title|Recommendation):\s*(.+?)(?=\n|$)'
    #     titles = re.findall(title_pattern, response_text, re.MULTILINE | re.IGNORECASE)
        
    #     if titles:
    #         print(f"Found {len(titles)} recommendations in text format, converting to structured format")
    #         for i, title in enumerate(titles[:4]):  # Limit to 4 recommendations
    #             recommendations.append({
    #                 "title": title.strip(),
    #                 "description": f"Implementation recommendation {i+1}",
    #                 "solution": "Follow implementation guidelines",
    #                 "priority": "Medium"
    #             })
    #         return recommendations
        
    #     # If still no recommendations found
    #     print("Warning: Could not parse recommendations from AI response")
    #     print(f"Response preview: {response_text[:300]}...")
    #     return []
        
    # except Exception as e:
    #     print(f"Error extracting recommendations: {e}")
    #     return []


# Not used. Enable if running this file as main

# async def analyze_with_structure_recommendations(url: str) -> dict:
    # """
    # Complete analysis including queries, domain analysis, and structure recommendations.
    
    # Args:
    #     url: The URL to analyze
        
    # Returns:
    #     Complete analysis results
    # """
    # # Step 1: Crawl website
    # print(f"Crawling website: {url}")
    # crawled_data = await crawl_website(url)
    # if not crawled_data:
    #     print("Error: Cannot generate analysis - website crawling failed")
    #     return {}
    
    # # Step 2: Generate queries
    # print("Generating queries...")
    # queries = await generate_queries_from_url(url)
    # if not queries:
    #     print("Warning: No queries generated, proceeding with structure analysis only")
    #     queries = []
    
    # # Step 3: Perform domain analysis
    # print(f"Analyzing domains for {len(queries)} queries...")
    # analyzer = DomainAnalyzer()
    # domain_results = analyzer.analyze_queries(queries, resolve_urls=True) if queries else []
    
    # # Step 4: Analyze website structure
    
    # structure_analyzer = StructureAnalyzer()
    # structure_analysis = structure_analyzer.analyze_for_recommendations(crawled_data)
    
    # # Step 5: Get AI-powered structure recommendations
    
    # structure_recommendations = []
    # try:
    #     client = GeminiGroundedClient()
    #     rec_prompt = get_structure_recommendations_prompt(structure_analysis, crawled_data)
    #     rec_response = client.process_query(rec_prompt, resolve_urls=False)
    #     structure_recommendations = extract_recommendations_from_response(rec_response["response_text"])
    #     print(f"Generated {len(structure_recommendations)} structure recommendations")
    # except Exception as e:
    #     print(f"Warning: Could not generate AI recommendations - {e}")
    
    # # Step 6: Format results in the same format as domain_analysis_prompted.json
    # # Add structure analysis to each query result
    # for result in domain_results:
    #     result["structure_analysis"] = structure_analysis
    #     result["structure_recommendations"] = structure_recommendations
    
    # # If no queries were generated, create a single result with just structure data
    # if not domain_results:
    #     domain_results = [{
    #         "query": "Structure Analysis Only",
    #         "links": [],
    #         "complete_result": {
    #             "query": "Structure Analysis Only",
    #             "response_text": "No queries generated - structure analysis only",
    #             "web_search_queries": [],
    #             "grounding_metadata": [],
    #             "has_grounding": False
    #         },
    #         "structure_analysis": structure_analysis,
    #         "structure_recommendations": structure_recommendations,
    #         "website_url": url,
    #         "crawl_timestamp": crawled_data.get("timestamp", "")
    #     }]
    # else:
    #     # Add metadata to all results
    #     for result in domain_results:
    #         result["website_url"] = url
    #         result["crawl_timestamp"] = crawled_data.get("timestamp", "")
    
    # # Print summary
    # print(f"\nAnalysis completed:")
    # print(f"- Queries analyzed: {len(queries)}")
    # print(f"- Structure recommendations: {len(structure_recommendations)}")
    # print(f"- Critical structure issues: {len(structure_analysis.get('structural_issues', []))}")
    # print(f"- Website word count: {structure_analysis.get('content_metrics', {}).get('word_count', 0)}")
    
    # # Save results with timestamp
    # from datetime import datetime
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # filename = f"domain_analysis_with_structure_{timestamp}.json"
    
    # try:
    #     with open(filename, 'w', encoding='utf-8') as f:
    #         json.dump(domain_results, f, indent=2, ensure_ascii=False)
    #     print(f"\nResults saved to: {filename}")
    # except Exception as e:
    #     print(f"Warning: Could not save results - {e}")
    
    # # Print sample recommendations
    # if structure_recommendations:
    #     print(f"\nSample Structure Recommendations:")
    #     for i, rec in enumerate(structure_recommendations[:3], 1):
    #         print(f"{i}. {rec.get('title', 'No title')}")
    # else:
    #     print(f"\nNo structure recommendations generated")
    
    # return {
    #     "results": domain_results,
    #     "summary": {
    #         "queries_count": len(queries),
    #         "recommendations_count": len(structure_recommendations),
    #         "structure_issues_count": len(structure_analysis.get('structural_issues', [])),
    #         "word_count": structure_analysis.get('content_metrics', {}).get('word_count', 0)
    #     }
    # }



if __name__ == "__main__":
    import sys
    
    # Check if URL is provided as command line argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = DEFAULT_URL
    
    print(f"\nQuery Generator - Analyzing: {url}")
    
    # Run query generation
    try:
        queries = asyncio.run(generate_queries_from_url(url))
        print(f"\nGenerated {len(queries)} queries:")
        for i, query_obj in enumerate(queries, 1):
            print(f"{i}. [{query_obj['type']}] {query_obj['query']}")
        
        # Analyze domains
        analyzer = DomainAnalyzer()
        results = analyzer.analyze_queries(queries, resolve_urls=True)
        analyzer.save_analysis(results, "domain_analysis_prompted.json")
        print(f"\nDomain analysis complete and saved to domain_analysis_prompted.json")
            
    except KeyboardInterrupt:
        print("\n  Analysis interrupted by user")
    except Exception as e:
        print(f"\n Analysis failed with error: {e}")
