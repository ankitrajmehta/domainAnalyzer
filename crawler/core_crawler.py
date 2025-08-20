"""
Core Crawler Module - Handles web crawling and JavaScript execution
Single Responsibility: Fetch content using crawl4ai and manage HTTP requests
"""

import time
import aiohttp
from datetime import datetime, timezone
from crawl4ai import AsyncWebCrawler


class GEOCrawler:
    """Main crawler engine for GEO content extraction"""
    
    def __init__(self):
        self.timeout = 60000  # 60 seconds
        self.delay_before_return = 3.0
        self.js_code = [
            # Scroll to trigger lazy loading
            "window.scrollTo(0, document.body.scrollHeight);",
            "await new Promise(resolve => setTimeout(resolve, 2000));",
            
            # Trigger common dynamic content patterns
            "document.querySelectorAll('[data-lazy]').forEach(el => el.click());",
            "document.querySelectorAll('[data-toggle]').forEach(el => el.click());",
            
            # Wait for dynamic content to load
            "await new Promise(resolve => setTimeout(resolve, 3000));",
            
            # Scroll back to top and wait
            "window.scrollTo(0, 0);",
            "await new Promise(resolve => setTimeout(resolve, 1000));",
            
            # Return the final HTML state
            "document.documentElement.outerHTML"
        ]
    
    async def get_http_metadata(self, url):
        """Get HTTP headers and metadata via preflight request"""
        http_info = {
            "final_url": url,
            "status_code": None,
            "response_headers": {},
            "redirects": [],
            "content_language": None,
            "last_modified": None,
            "content_type": None
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True, timeout=10) as response:
                    http_info["status_code"] = response.status
                    http_info["final_url"] = str(response.url)
                    http_info["response_headers"] = dict(response.headers)
                    http_info["content_language"] = response.headers.get('Content-Language')
                    http_info["last_modified"] = response.headers.get('Last-Modified')
                    http_info["content_type"] = response.headers.get('Content-Type')
                    
                    # Track redirects
                    if response.history:
                        for redirect in response.history:
                            http_info["redirects"].append({
                                "from": str(redirect.url),
                                "to": str(redirect.headers.get('Location', '')),
                                "status": redirect.status
                            })
        except Exception as e:
            print(f"  HTTP metadata warning: {e}")
        
        return http_info
    
    async def fetch_page_content(self, url):
        """Fetch and render page content with JavaScript execution"""
        print(" Extracting with full JavaScript ...")
        
        start_time = time.time()
        
        async with AsyncWebCrawler(verbose=True) as crawler:
            result = await crawler.arun(
                url=url,
                js_code=self.js_code,
                wait_for="css:body",
                page_timeout=self.timeout,
                delay_before_return_html=self.delay_before_return,
                
                # LLM-like settings
                simulate_user=True,
                magic=True,
                bypass_cache=True,
                word_count_threshold=0,
                
                # Additional settings for dynamic content
                remove_overlay_elements=True,
                mean_delay=1.0,
                max_delay=3.0
            )
        
        extraction_time = time.time() - start_time
        
        if not result.success:
            raise Exception("Content extraction failed")
        
        return {
            "result": result,
            "extraction_time": extraction_time,
            "original_html": result.html or "",
            "clean_text": result.markdown or "",
            "rendered_html": self._get_rendered_html(result)
        }
    
    def _get_rendered_html(self, result):
        """Extract rendered HTML from crawl result"""
        if hasattr(result, 'rendered_html') and result.rendered_html:
            return result.rendered_html
        elif result.html:
            # Assume result.html is post-render since we used JS
            return result.html
        return ""
    
    def detect_javascript_execution(self, original_html, rendered_html, result):
        """Detect if JavaScript was executed and modified the DOM"""
        js_executed = False
        js_modified_dom = False
        
        # Method 1: Check crawl4ai result attributes
        if hasattr(result, 'js_execution_success'):
            js_executed = result.js_execution_success
        elif hasattr(result, 'screenshot'):
            js_executed = True
        elif hasattr(result, 'metadata') and result.metadata:
            js_executed = result.metadata.get('javascript_executed', False)
        
        # Method 2: Logical inference (we requested JS execution)
        if not js_executed and original_html:
            js_executed = True  # We know we requested JS execution
        
        # Method 3: Analyze HTML for JavaScript execution evidence
        if original_html:
            script_count = original_html.lower().count('<script')
            has_scripts = script_count > 0
            
            # Look for JS framework indicators
            js_indicators = [
                'data-react', 'ng-', 'v-', 'data-vue', '__NEXT_DATA__', 
                'react-root', 'angular', 'vue', 'data-reactroot',
                'data-hydrated', 'data-server-rendered', 'spa-',
                'window.', 'document.', 'addEventListener'
            ]
            has_js_framework = any(indicator in original_html.lower() for indicator in js_indicators)
            
            # Look for dynamic loading indicators
            dynamic_indicators = [
                'async', 'defer', 'data-lazy', 'lazy-load',
                'intersection-observer', 'data-src'
            ]
            has_dynamic_content = any(indicator in original_html.lower() for indicator in dynamic_indicators)
            
            # Determine if DOM was modified
            if has_scripts and (has_js_framework or has_dynamic_content):
                js_modified_dom = True
            
            # Enhanced detection for heavy JS sites
            if script_count > 5:
                js_executed = True
                js_modified_dom = True
        
        return js_executed, js_modified_dom
    
    def create_crawl_info(self, url, final_url, extraction_time, js_executed, js_modified_dom, content_length, html_length, rendered_html_length):
        """Create crawl information metadata"""
        return {
            "url": url,
            "final_url": final_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "extraction_time_seconds": round(extraction_time, 2),
            "javascript_executed": js_executed,
            "javascript_modified_dom": js_modified_dom,
            "content_length": content_length,
            "html_length": html_length,
            "rendered_html_length": rendered_html_length,
            "extraction_method": "enhanced_llm_mimic_with_geo"
        }
