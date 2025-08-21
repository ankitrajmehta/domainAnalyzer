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
            rec_response = client.process_query(rec_prompt, resolve_urls=False)
            structure_recommendations = extract_recommendations_from_response(rec_response["response_text"])
        except Exception as e:
            print(f"Warning: Could not generate AI recommendations - {e}")
            # Continue without AI recommendations
        
        return {
            'structure_analysis': structure_analysis,
            'structure_recommendations': structure_recommendations
        }
        
    except Exception as e:
        return {'error': f'Structure analysis failed: {str(e)}'}

def get_structure_recommendations_prompt(structure_analysis: dict, crawled_data: dict) -> str:
    """
    Generate a prompt for getting structure recommendations from Gemini.
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

def extract_recommendations_from_response(response_text: str) -> list:
    """
    Extract structure recommendations from Gemini response.
    """
    import json
    import re
    
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
        
        # Fallback: Create default recommendations if AI response failed
        if not recommendations:
            recommendations = [
                {
                    "title": "Add Semantic HTML Structure",
                    "description": "Implement proper semantic HTML5 tags for better content organization",
                    "reason": "AI systems parse semantic HTML more effectively for content understanding",
                    "implementation": "Use <article>, <section>, <header>, and <main> tags appropriately",
                    "priority": "high"
                },
                {
                    "title": "Optimize Meta Tags",
                    "description": "Add missing critical meta tags for better AI comprehension",
                    "reason": "Meta tags provide structured information that AI systems rely on",
                    "implementation": "Add meta description, title, and Open Graph tags",
                    "priority": "high"
                }
            ]
        
        return recommendations
        
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
