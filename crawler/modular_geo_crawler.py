#!/usr/bin/env python3
"""

Extracts content exactly as modern LLMs would see it for GEO analysis

Modular Architecture:
- core_crawler: Handles web crawling and JavaScript execution
- html_parser: Parses HTML and extracts structured information  
- data_normalizer: Normalizes structured data for GEO models
- output_handler: Formats and saves output data
- utils: Utility functions
"""

import asyncio
import sys
from urllib.parse import urlparse

from crawler import GEOCrawler, HTMLParser, DataNormalizer, OutputHandler


class GEOCrawlerOrchestrator:
    """Main orchestrator that coordinates all crawler modules"""
    
    def __init__(self):
        self.crawler = GEOCrawler()
        self.parser = HTMLParser()
        self.normalizer = DataNormalizer()
        self.output_handler = OutputHandler()
    
    async def crawl_url(self, url):
        """Main crawling workflow - coordinates all modules"""
        
        print(f" Target: {url}")
        print(f" Extracting raw content  ")
        print("=" * 70)
        
        try:
            # Step 1: Get HTTP metadata
            print("🌐 Gathering HTTP metadata...")
            http_info = await self.crawler.get_http_metadata(url)
            
            # Step 2: Fetch and render page content
            content_data = await self.crawler.fetch_page_content(url)
            
            # Step 3: Detect JavaScript execution
            js_executed, js_modified_dom = self.crawler.detect_javascript_execution(
                content_data["original_html"],
                content_data["rendered_html"], 
                content_data["result"]
            )
            
            # Step 4: Update HTTP info with crawl results
            if hasattr(content_data["result"], 'url') and content_data["result"].url:
                http_info["final_url"] = content_data["result"].url
            if content_data["result"].success:
                http_info["status_code"] = http_info.get("status_code") or 200
            
            # Step 5: Parse HTML content
            print("  Parsing structured data...")
            structured_data = self.parser.parse_structured_data(content_data["rendered_html"])
            
            print(" Extracting meta data...")
            meta_data = self.parser.extract_meta_data(content_data["rendered_html"])
            
            print(" Extracting language info...")
            language_info = self.parser.extract_language_info(content_data["rendered_html"], http_info)
            
            print(" Extracting links and images...")
            links, images = self.parser.extract_links_and_images(content_data["rendered_html"], http_info["final_url"])
            
            print(" Analyzing DOM changes...")
            dom_diff = self.parser.calculate_dom_diff(content_data["original_html"], content_data["rendered_html"])
            
            # Step 6: Normalize data for GEO analysis
            print(" Normalizing GEO-relevant data...")
            normalized_data = self.normalizer.normalize_structured_data(structured_data)
            content_stats = self.normalizer.calculate_content_stats(content_data["clean_text"], links, images)
            
            # Step 7: Create crawl info
            crawl_info = self.crawler.create_crawl_info(
                url=url,
                final_url=http_info["final_url"],
                extraction_time=content_data["extraction_time"],
                js_executed=js_executed,
                js_modified_dom=js_modified_dom,
                content_length=len(content_data["clean_text"]),
                html_length=len(content_data["original_html"]),
                rendered_html_length=len(content_data["rendered_html"])
            )
            
            # Step 8: Create output data structure
            parsed_data = {
                "structured_data": structured_data,
                "meta_data": meta_data,
                "language_info": language_info
            }
            
            output_data = self.output_handler.create_output_data(
                crawl_info=crawl_info,
                http_info=http_info,
                content_data=content_data,
                parsed_data=parsed_data,
                normalized_data=normalized_data,
                links=links,
                images=images,
                dom_diff=dom_diff,
                content_stats=content_stats
            )
            
            # # Step 9: Print summary and save results
            # self.output_handler.print_extraction_summary(
            #     crawl_info, http_info, structured_data, normalized_data,
            #     links, images, language_info, meta_data, content_data, dom_diff
            # )
            
            save_info = self.output_handler.save_output(output_data, url)
            self.output_handler.print_save_summary(save_info)
            
            return output_data
            
        except Exception as e:
            print(f" Crawling failed: {e}")
            return None




async def crawl_url(url: str):

    # Initialize the orchestrator
    orchestrator = GEOCrawlerOrchestrator()
    
    
    if not url:
        print(" URL cannot be empty.")
    
    # Add https:// if no protocol specified
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        print(f" Corrected to: {url}")
    
    # Basic URL validation
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception:
        print(f" Invalid URL. Please enter a valid URL.")
    
    # Execute the crawl
    result = await orchestrator.crawl_url(url)   

    if result:
        print("Crawl successful!")
    else:
        print("Crawl failed.")

    return result

async def main():
    """Main entry point"""
    
    # Initialize the orchestrator
    orchestrator = GEOCrawlerOrchestrator()
    
    # Check if URL was provided as command line argument
    if len(sys.argv) == 2:
        url = sys.argv[1]
        print(f" URL: {url}")
    else:
        # Interactive mode
        while True:
            url = input("\n Enter URL to crawl (raw LLM content): ").strip()
            
            if not url:
                print(" URL cannot be empty.")
                continue
            
            # Add https:// if no protocol specified
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                print(f"🔧 Corrected to: {url}")
            
            # Basic URL validation
            try:
                result = urlparse(url)
                if not all([result.scheme, result.netloc]):
                    raise ValueError("Invalid URL format")
                break
            except Exception:
                print(f" Invalid URL. Please enter a valid URL.")
                continue
    
    # Execute the crawl
    await orchestrator.crawl_url(url)


if __name__ == "__main__":
    asyncio.run(main())
