
import os
import json
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from google import genai
from google.genai import types
from dotenv import load_dotenv


class GeminiGroundedClient:
    """
    A client for Gemini AI with Google Search grounding capabilities.
    Handles response generation and metadata parsing.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        """
        Initialize the Gemini client with grounding capabilities.
        
        Args:
            api_key: Google API key. If None, reads from environment variables.
            model: Gemini model to use for generation.
        """
        self.model = model
        self.api_key = self._get_api_key(api_key)
        self.client = genai.Client(api_key=self.api_key)
        self.grounding_tool = types.Tool(google_search=types.GoogleSearch())
        self.config = types.GenerateContentConfig(tools=[self.grounding_tool])
    
    def _get_api_key(self, api_key: Optional[str]) -> str:
        """Get API key from parameter or environment variables."""
        if api_key:
            return api_key
        
        # Load environment variables from .env file if present
        load_dotenv()
        
        env_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
        if not env_key:
            raise RuntimeError(
                "Missing API key. Provide it as parameter or set GOOGLE_API_KEY "
                "(or GOOGLE_GENAI_API_KEY) in your environment."
            )
        return env_key
    
    def resolve_actual_url(self, redirect_url: str, timeout: int = 5) -> Optional[str]:
        """
        Resolve the actual URL from a redirect URL.
        
        Args:
            redirect_url: The redirect URL from Gemini grounding metadata.
            timeout: Request timeout in seconds.
            
        Returns:
            The actual URL if successfully resolved, None otherwise.
        """
        try:
            # Make a HEAD request to follow redirects without downloading content
            response = requests.head(redirect_url, allow_redirects=True, timeout=timeout)
            return response.url
        except Exception as e:
            print(f"Warning: Could not resolve URL {redirect_url}: {e}")
            return None
    
    def extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL for comparison with title."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '')
        except:
            return url
    
    def generate_response(self, prompt: str, use_grounding: bool = True):
        """
        Generate a response with optional grounding.
        
        Args:
            prompt: The input prompt/question.
            use_grounding: Whether to enable Google Search grounding.
            
        Returns:
            The response object from Gemini API.
        """
        config = self.config if use_grounding else None
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response
    
    def parse_grounding_metadata(self, candidate, resolve_urls: bool = True) -> Dict[str, Any]:
        """
        Parse grounding metadata into structured format with text segments and their supporting links.
        
        Args:
            candidate: The response candidate containing grounding metadata.
            resolve_urls: Whether to resolve actual URLs from redirect URLs.
            
        Returns:
            List of segments, each containing:
            {
                "text": str,           # The actual text segment from the response that has been grounded
                "links": [            # List of sources supporting this text segment
                    {
                        "title": str,        # Domain/site title (e.g., "wikipedia.org")
                        "redirect_url": str, # Google's redirect URL 
                        "actual_url": str    # Resolved destination URL
                    }
                ],
                "start_index": int,   # Character position where this segment starts in response
                "end_index": int      # Character position where this segment ends in response
            }
        """
        if not hasattr(candidate, 'grounding_metadata') or not candidate.grounding_metadata:
            return {}
        
        grounding_metadata = candidate.grounding_metadata
        grounding_chunks = grounding_metadata.grounding_chunks or []
        grounding_supports = grounding_metadata.grounding_supports or []
        
        # If no grounding supports, return empty dict
        if not grounding_supports:
            return {}
        
        # Pre-process all grounding chunks to resolve URLs only once
        resolved_chunks = {}  # Cache for resolved chunk data
        url_resolution_cache = {}  # Cache for URL resolutions
        
        for chunk_index, chunk in enumerate(grounding_chunks):
            if hasattr(chunk, 'web') and chunk.web:
                redirect_url = chunk.web.uri
                
                link_info = {
                    "title": chunk.web.title,        # Website domain/title (e.g., "tradingview.com")
                    "redirect_url": redirect_url      # Google's redirect URL
                }
                
                if resolve_urls:
                    if redirect_url not in url_resolution_cache:
                        url_resolution_cache[redirect_url] = self.resolve_actual_url(redirect_url)
                    link_info["actual_url"] = url_resolution_cache[redirect_url]
                
                resolved_chunks[chunk_index] = link_info
        
        result = []

        # Process supports
        for i, support in enumerate(grounding_supports, 1):
            segment = support.segment
            
            # Get the supporting links for this segment
            links = []
            for chunk_index in support.grounding_chunk_indices:
                if chunk_index in resolved_chunks:
                    links.append(resolved_chunks[chunk_index])
            
            result.append({
                "text": segment.text,                                    # The text segment that was grounded
                "links": links,                                          # Sources that support this text
                "start_index": getattr(segment, 'start_index', 0),      # Where this text starts in full response
                "end_index": segment.end_index                           # Where this text ends in full response
            })
        
        return result
    
    def process_query(self, prompt: str, resolve_urls: bool = True) -> Dict[str, Any]:
        """
        Process a query end-to-end: generate response and parse grounding metadata.
        
        Args:
            prompt: The input question/prompt.
            resolve_urls: Whether to resolve actual URLs from redirect URLs.
            
        Returns:
            Complete result structure:
            {
                "query": str,                    # Original user question
                "response_text": str,            # Full AI-generated response text
                "web_search_queries": [str],     # Search queries the AI used (for debugging)
                "grounding_metadata": [          # Parsed segments with sources (see parse_grounding_metadata)
                    {
                        "text": str,
                        "links": [...],
                        "start_index": int,
                        "end_index": int
                    }
                ],
                "has_grounding": bool            # True if AI used web search, False if answered from knowledge
            }
        """
        # Generate response
        response = self.generate_response(prompt)
        
        # Extract text
        response_text = response.text
        
        # Parse grounding metadata
        print("Resolving actual URLs..." if resolve_urls else "Using redirect URLs only...")
        parsed_metadata = self.parse_grounding_metadata(response.candidates[0], resolve_urls=resolve_urls)
        
        # Prepare complete result structure
        result = {
            "query": prompt,                                                                                                                    # Original user question
            "response_text": response_text,                                                                                                     # Full AI response
            "web_search_queries": response.candidates[0].grounding_metadata.web_search_queries if hasattr(response.candidates[0].grounding_metadata, 'web_search_queries') else [],  # AI's search queries
            "grounding_metadata": parsed_metadata,                                                                                             # Parsed text segments with sources
            "has_grounding": bool(parsed_metadata)                                                                                             # Whether web search was used
        }
        
        # Print results
        print(f"Query: {prompt}")
        print(f"Response: {response_text}")
        
        if parsed_metadata:
            print("\nParsed Grounding Metadata:")
            print(json.dumps(parsed_metadata, indent=2))
        else:
            print("\nNo grounding metadata available (model answered from its own knowledge)")
        
        return result




def main():
    """Main function demonstrating the GeminiGroundedClient usage."""
    client = GeminiGroundedClient()
    
    #DEfine and processing the queries
    queries = [
        "What's the latest price of Apple stock?"
    ]
    
    all_results = []
    for i, query in enumerate(queries):
        print(f"\n{'='*60}")
        print(f"QUERY {i+1}")
        print('='*60)
        
        result = client.process_query(query)
        all_results.append(result)


# saving the outputs
    output_file = "gemini_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nAll results saved to {output_file}")


if __name__ == "__main__":
    main()
