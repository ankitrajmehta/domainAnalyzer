"""
Flask API for the Analysis Frontend
========================================

This API provides endpoints for the 4-page frontend:
1. URL input and analysis start
2. Loading/status check
3. Aggregate results view
4. Individual query details view
5. Structure analysis results
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time
import asyncio
from typing import Dict, Any

from analyzer import Analyzer
import crawler.modular_geo_crawler as modular_geo_crawler
from structure_recommendation.structure_analyzer import StructureAnalyzer
from geminiClient.gemini import GeminiGroundedClient

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Global analyzer instance
analyzer = Analyzer()
analysis_thread = None

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'message': 'API is running'}), 200

@app.route('/api/start-analysis', methods=['POST'])
def start_analysis():
    """
    Start analysis for a given URL.
    
    Expected JSON payload:
    {
        "url": "https://example.com",
        "numOfQueries": 8  // optional, defaults to 8
    }
    
    Returns:
    {
        "status": "started",
        "message": "Analysis started for URL",
        "url": "https://example.com",
        "numOfQueries": 8
    }
    """
    global analysis_thread, analyzer
    
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required in request body'}), 400
        
        url = data['url'].strip()
        if not url:
            return jsonify({'error': 'URL cannot be empty'}), 400
        
        # Get number of queries (optional, default to current setting)
        num_queries = data.get('numOfQueries', analyzer.queriesToRun)
        
        # Validate number of queries
        if not isinstance(num_queries, int) or num_queries < 1 or num_queries > 50:
            return jsonify({'error': 'numOfQueries must be an integer between 1 and 50'}), 400
        
        # Check if analysis is already running
        if analyzer.get_status() == 'analyzing':
            return jsonify({'error': 'Analysis is already running'}), 409
        
        # Update the number of queries in the analyzer
        analyzer.queriesToRun = num_queries
        
        # Start analysis in background thread
        def run_analysis():
            try:
                analyzer.run_analysis(url, saveResults=True)
            except Exception as e:
                print(f"Analysis failed: {e}")
        
        analysis_thread = threading.Thread(target=run_analysis)
        analysis_thread.start()
        
        return jsonify({
            'status': 'started',
            'message': f'Analysis started for URL: {url}',
            'url': url,
            'numOfQueries': num_queries
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to start analysis: {str(e)}'}), 500

@app.route('/api/status', methods=['GET'])
def get_analysis_status():
    """
    Get current analysis status.
    
    Returns:
    {
        "status": "idle" | "analyzing" | "complete" | "error",
        "url": "current_url",
        "num_queries": number_of_queries_generated,
        "queries_to_run": number_of_queries_configured
    }
    """
    try:
        status = analyzer.get_status()
        return jsonify({
            'status': status,
            'url': analyzer.url,
            'num_queries': len(analyzer.get_all_queries()) if status in ['complete', 'analyzing'] else 0,
            'queries_to_run': analyzer.queriesToRun
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500

@app.route('/api/aggregate-results', methods=['GET'])
def get_aggregate_results():
    """
    Get aggregate analysis results for page 3.
    
    Returns:
    {
        "status": "complete",
        "url": "analyzed_url",
        "queries": ["query1", "query2", ...],
        "domain_percentages": [
            {
                "domain": "example.com",
                "percentage": 75.0,
                "query_count": 6
            },
            ...
        ],
        "num_queries": 8
    }
    """
    try:
        if analyzer.get_status() != 'complete':
            return jsonify({'error': 'Analysis not complete yet'}), 400
        
        percentage_data = analyzer.get_percentage_analysis()
        queries = analyzer.get_all_queries()
        
        return jsonify({
            'status': 'complete',
            'url': analyzer.url,
            'queries': queries,
            'domain_percentages': percentage_data['domainPercentages'],
            'num_queries': percentage_data['numOfQueries']
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get aggregate results: {str(e)}'}), 500

@app.route('/api/query-details', methods=['POST'])
def get_query_details():
    """
    Get detailed results for a specific query (page 4).
    
    Expected JSON payload:
    {
        "query": "specific query text"
    }
    
    Returns:
    {
        "query": "query text",
        "gemini_response": "Full response from Gemini",
        "domains": [
            {
                "domain": "example.com",
                "count": 3
            },
            ...
        ],
        "grounding_metadata": [...] // Raw grounding data if needed
    }
    """
    try:
        if analyzer.get_status() != 'complete':
            return jsonify({'error': 'Analysis not complete yet'}), 400
        
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required in request body'}), 400
        
        query = data['query']
        query_details = analyzer.get_query_details(query)
        
        if not query_details:
            return jsonify({'error': 'Query not found in analysis results'}), 404
        
        return jsonify(query_details), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get query details: {str(e)}'}), 500

@app.route('/api/reset', methods=['POST'])
def reset_analysis():
    """
    Reset the analyzer to start a new analysis.
    
    Returns:
    {
        "status": "reset",
        "message": "Analyzer reset successfully"
    }
    """
    try:
        global analyzer
        analyzer = Analyzer()  # Create new instance
        
        return jsonify({
            'status': 'reset',
            'message': 'Analyzer reset successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to reset analyzer: {str(e)}'}), 500

@app.route('/api/analyze-structure', methods=['POST'])
def analyze_structure():
    """
    Analyze website structure and get recommendations.
    
    Expected JSON payload:
    {
        "url": "https://example.com"
    }
    
    Returns:
    {
        "status": "success",
        "url": "https://example.com",
        "structure_analysis": {...},
        "structure_recommendations": [...]
    }
    """
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required in request body'}), 400
        
        url = data['url'].strip()
        if not url:
            return jsonify({'error': 'URL cannot be empty'}), 400
        
        # Run the structure analysis
        result = asyncio.run(perform_structure_analysis(url))
        
        if result.get('error'):
            return jsonify({'error': result['error']}), 400
        
        return jsonify({
            'status': 'success',
            'url': url,
            'structure_analysis': result['structure_analysis'],
            'structure_recommendations': result['structure_recommendations']
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to analyze structure: {str(e)}'}), 500

async def perform_structure_analysis(url: str) -> Dict[str, Any]:
    """
    Perform structure analysis for a given URL.
    
    Args:
        url: The URL to analyze
        
    Returns:
        Dictionary containing analysis results or error
    """
    try:
        # Step 1: Crawl website
        crawled_data = await modular_geo_crawler.crawl_url(url)
        
        if not crawled_data or "clean_text" not in crawled_data:
            return {'error': 'Failed to crawl website - no content found'}
        
        # Step 2: Analyze website structure
        structure_analyzer = StructureAnalyzer()
        structure_analysis = structure_analyzer.analyze_for_recommendations(crawled_data)
        
        # Step 3: Get AI-powered structure recommendations  
        structure_recommendations = []
        try:
            client = GeminiGroundedClient()
            rec_prompt = get_structure_recommendations_prompt(structure_analysis, crawled_data)
            
            print(f"Sending prompt to AI: {rec_prompt[:200]}...")
            rec_response = client.process_query(rec_prompt, resolve_urls=False)
            print(f"AI response received: {rec_response['response_text']}")
            
            structure_recommendations = extract_recommendations_from_response(rec_response["response_text"])
            
            # If AI failed, ensure we have fallback
            if not structure_recommendations:
                print("Warning: AI returned no recommendations, using intelligent fallback")
                structure_recommendations = generate_fallback_recommendations(structure_analysis)
                
        except Exception as e:
            print(f"Error: AI recommendation generation failed - {e}")
            structure_recommendations = generate_fallback_recommendations(structure_analysis)
        
        return {
            'structure_analysis': structure_analysis,
            'structure_recommendations': structure_recommendations
        }
        
    except Exception as e:
        return {'error': f'Structure analysis failed: {str(e)}'}

def generate_fallback_recommendations(structure_analysis: dict) -> list:
    """
    Generate simple, direct GEO recommendations.
    """
    recommendations = []
    
    missing_meta = structure_analysis.get('meta_completeness', {}).get('missing_critical', [])
    headings = structure_analysis.get('heading_structure', {})
    word_count = structure_analysis.get('content_metrics', {}).get('word_count', 0)
    h1_count = headings.get('distribution', {}).get('h1', 0)
    h2_count = headings.get('distribution', {}).get('h2', 0)
    total_headings = headings.get('total', 0)
    missing_elements = structure_analysis.get('semantic_elements', {}).get('missing_elements', [])
    faq_data = structure_analysis.get('faq_structure', {})
    schema_data = structure_analysis.get('schema_markup', {})
    
    # 1. Meta tags
    if missing_meta:
        recommendations.append({
            "title": "Add Missing Meta Tags",
            "description": f"Add these missing meta tags: {', '.join(missing_meta)}. Include title, description, and Open Graph tags.",
            "priority": "High"
        })
    
    # 2. Heading structure
    if h1_count == 0:
        recommendations.append({
            "title": "Add H1 Heading",
            "description": "Add one clear H1 heading that describes your main topic.",
            "priority": "High"
        })
    elif h1_count > 1:
        recommendations.append({
            "title": "Fix Multiple H1 Tags",
            "description": f"Use only one H1 tag. Convert the other {h1_count-1} H1 tags to H2 or H3.",
            "priority": "High"
        })
    elif total_headings < 3:
        recommendations.append({
            "title": "Add More Headings",
            "description": f"Add more H2 and H3 headings to organize your content better (currently {total_headings}).",
            "priority": "Medium"
        })
    
    # 3. Content length
    if word_count < 300:
        recommendations.append({
            "title": "Expand Content",
            "description": f"Increase content from {word_count} to at least 300-500 words for better authority.",
            "priority": "Medium"
        })
    
    # 4. Semantic structure
    if 'article' in missing_elements or 'section' in missing_elements:
        recommendations.append({
            "title": "Add Semantic HTML",
            "description": "Use semantic HTML5 tags like <article>, <section>, <header>, and <main>.",
            "priority": "Medium"
        })
    
    # 5. Schema markup - prioritize JSON-LD for AI systems
    json_ld_count = schema_data.get('types', {}).get('json_ld', 0)
    if json_ld_count == 0:
        recommendations.append({
            "title": "Add JSON-LD Schema",
            "description": "Implement JSON-LD structured data markup for optimal AI understanding and citation.",
            "priority": "High"
        })
    
    # 6. FAQ structure
    if not faq_data.get('has_faq', False) and word_count > 500:
        recommendations.append({
            "title": "Add FAQ Section",
            "description": "Create a FAQ section with structured Q&A format for common questions.",
            "priority": "Low"
        })
    
    # Fill to exactly 4 recommendations
    while len(recommendations) < 4:
        if len(recommendations) == 0:
            recommendations.append({
                "title": "Add Meta Description",
                "description": "Create a 150-160 character meta description for this page.",
                "priority": "High"
            })
        elif len(recommendations) == 1:
            recommendations.append({
                "title": "Improve Page Structure",
                "description": "Organize content with proper headings and semantic HTML elements.",
                "priority": "Medium"
            })
        elif len(recommendations) == 2:
            recommendations.append({
                "title": "Add Schema Markup",
                "description": "Implement JSON-LD structured data for AI citation optimization.",
                "priority": "Medium"
            })
        else:
            recommendations.append({
                "title": "Enhance Content Structure",
                "description": "Add FAQ sections and improve content organization for better AI understanding.",
                "priority": "Low"
            })
    
    return recommendations[:4]

def get_structure_recommendations_prompt(structure_analysis: dict, crawled_data: dict) -> str:
    """
    Generate a simple, direct prompt for GEO() recommendations.
    """
    # Get key issues
    missing_meta = structure_analysis.get('meta_completeness', {}).get('missing_critical', [])
    word_count = structure_analysis.get('content_metrics', {}).get('word_count', 0)
    headings = structure_analysis.get('heading_structure', {})
    h1_count = headings.get('distribution', {}).get('h1', 0)
    h2_count = headings.get('distribution', {}).get('h2', 0)
    total_headings = headings.get('total', 0)
    missing_elements = structure_analysis.get('semantic_elements', {}).get('missing_elements', [])
    faq_data = structure_analysis.get('faq_structure', {})
    schema_data = structure_analysis.get('schema_markup', {})
    
    prompt = f"""Analyze this website for GEO (Generative Engine Optimization) and give 4 direct recommendations.

GEO is about optimizing content for AI systems Gemini that cite and reference web content. Not about geographic or local SEO.

ISSUES FOUND:
- Missing meta tags: {missing_meta}
- Word count: {word_count}
- H1 tags: {h1_count}
- Total headings: {total_headings}
- Missing elements: {missing_elements}
- FAQ structure: {faq_data.get('has_faq', False)}
- Schema markup: {schema_data.get('has_structured_data', False)}

Give 4 short, direct recommendations for AI citation optimization. Focus on what AI systems need to understand and cite your content.

Format:
[
  {{
    "title": "Add Meta Description",
    "description": "Create a 150-160 character meta description for this page.",
    "priority": "High"
  }},
  {{
    "title": "Fix Heading Structure", 
    "description": "Add proper H1 tag and organize content with H2/H3 headings.",
    "priority": "High"
  }},
  {{
    "title": "Add Schema Markup",
    "description": "Implement JSON-LD structured data for better content understanding.",
    "priority": "Medium"
  }},
  {{
    "title": "Improve Content Structure",
    "description": "Use semantic HTML tags like article, section, and header.",
    "priority": "Medium"
  }}
]

Return ONLY the JSON array, nothing else."""
    
    return prompt

def extract_recommendations_from_response(response_text: str) -> list:
    """
    Extract structure recommendations from Gemini response with enhanced debugging.
    """
    import json
    import re
    
    recommendations = []
    
    try:
        print(f"AI Response length: {len(response_text)} characters")
        # print(f"First 200 chars: {response_text[:200]}")
        
        # Clean the response more thoroughly
        cleaned_response = response_text.strip()
        
        # Remove markdown code blocks
        cleaned_response = re.sub(r'^```json\s*', '', cleaned_response, flags=re.MULTILINE)
        cleaned_response = re.sub(r'^```\s*', '', cleaned_response, flags=re.MULTILINE)
        cleaned_response = re.sub(r'\s*```$', '', cleaned_response, flags=re.MULTILINE)
        
        # Remove any leading/trailing text that's not JSON
        lines = cleaned_response.split('\n')
        start_idx = -1
        end_idx = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('['):
                start_idx = i
                break
        
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().endswith(']'):
                end_idx = i
                break
        
        if start_idx != -1 and end_idx != -1:
            json_lines = lines[start_idx:end_idx + 1]
            cleaned_response = '\n'.join(json_lines)
        
        print(f"Cleaned response: {cleaned_response}")
        
        # Try to parse as JSON directly
        try:
            parsed_data = json.loads(cleaned_response)
            if isinstance(parsed_data, list):
                print(f"Successfully parsed {len(parsed_data)} recommendations from AI")
                for rec in parsed_data:
                    if isinstance(rec, dict) and "title" in rec and "description" in rec:
                        # Clean up text and remove unwanted characters
                        title = str(rec.get("title", "")).replace(",,", "").replace("  ", " ").strip()
                        description = str(rec.get("description", "")).replace(",,", "").replace("  ", " ").strip()
                        priority = str(rec.get("priority", "Medium")).strip()
                        
                        # Remove incomplete sentences that end abruptly
                        if description.endswith(" an") or description.endswith(" the") or description.endswith(" a"):
                            description = description.rsplit(' ', 1)[0] + "."
                        
                        if title and description and len(description) > 20:  # Ensure meaningful content
                            recommendations.append({
                                "title": title,
                                "description": description,
                                "priority": priority
                            })
                
                if recommendations:
                    print(f"Extracted {len(recommendations)} valid recommendations")
                    return recommendations[:4]
            
        except json.JSONDecodeError as e:
            print(f"Direct JSON parsing failed: {e}")
            
            # Try to find JSON array pattern as fallback
            json_pattern = r'\[[\s\S]*?\]'
            json_matches = re.findall(json_pattern, cleaned_response, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    parsed_recs = json.loads(json_str)
                    if isinstance(parsed_recs, list) and len(parsed_recs) > 0:
                        print(f"Found valid JSON array with {len(parsed_recs)} items")
                        for rec in parsed_recs:
                            if isinstance(rec, dict) and "title" in rec and "description" in rec:
                                title = str(rec.get("title", "")).replace(",,", "").strip()
                                description = str(rec.get("description", "")).replace(",,", "").strip()
                                priority = str(rec.get("priority", "Medium")).strip()
                                
                                if title and description:
                                    recommendations.append({
                                        "title": title,
                                        "description": description,
                                        "priority": priority
                                    })
                        
                        if recommendations:
                            return recommendations[:4]
                            
                except json.JSONDecodeError as e2:
                    print(f"Fallback JSON parsing failed: {e2}")
                    continue
        
        print("Warning: AI response parsing failed - using fallback recommendations")
        return []
        
    except Exception as e:
        print(f"Error extracting recommendations: {e}")
        return []

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Analysis API...")
    print("Available endpoints:")
    print("  POST /api/start-analysis - Start analysis for a URL")
    print("  GET  /api/status - Get current analysis status")
    print("  GET  /api/aggregate-results - Get aggregate results")
    print("  POST /api/query-details - Get details for specific query")
    print("  POST /api/reset - Reset analyzer")
    print("  GET  /api/health - Health check")
    print("\nAPI running on http://localhost:8000")
    
    app.run(host='0.0.0.0', port=8000, debug=True)
