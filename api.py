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


from analyzer import Analyzer

import structureAnalyzer

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

DEMO_MODE = False  # Enable demo mode if True

# Global analyzer instance 
analyzer = Analyzer(demo_mode=DEMO_MODE)
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
        "queries_structured": [
            {
                "query": "query text",
                "type": "Direct" | "Generic"
            },
            ...
        ],
        "query_types": {
            "total": 8,
            "direct": 3,
            "generic": 5,
            "direct_percentage": 37.5,
            "generic_percentage": 62.5
        },
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
        queries_structured = analyzer.get_all_queries_structured()
        query_types = analyzer.get_query_types_summary()
        domain_breakdown = analyzer.get_domain_breakdown_by_type()
        
        return jsonify({
            'status': 'complete',
            'url': analyzer.url,
            'queries': queries,
            'queries_structured': queries_structured,
            'query_types': query_types,  
            'domain_percentages': percentage_data['domainPercentages'],
            'domain_breakdown': domain_breakdown,
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
        "query_type": "Direct" | "Generic",
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
        analyzer = Analyzer(demo_mode=DEMO_MODE)

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
        result = asyncio.run(structureAnalyzer.perform_structure_analysis(url))
        
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
