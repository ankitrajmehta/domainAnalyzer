"""
Output Handler Module - Handles saving and formatting output data
Single Responsibility: Save crawler results to files and format output
"""

import json
import os
from .utils import create_output_filename, ensure_output_directory


class OutputHandler:
    """Handles output formatting and file operations"""
    
    def __init__(self):
        pass
    
    def create_output_data(self, crawl_info, http_info, content_data, parsed_data, normalized_data, links, images, dom_diff, content_stats):
        """Create the final output data structure"""
        return {
            "crawl_info": crawl_info,
            "http_info": http_info,
            # Raw content exactly as LLMs would see it
            "raw_html": content_data["original_html"],
            "rendered_html": content_data["rendered_html"], 
            "clean_text": content_data["clean_text"],
            # DOM analysis
            "dom_diff": dom_diff,
            # Structured data (parsed for easy access)
            "structured_data": parsed_data["structured_data"],
            # Normalized structured data for GEO models
            "structured_data_normalized": normalized_data,
            # Meta data (parsed for easy access)
            "meta": parsed_data["meta_data"],
            # Language information
            "language": parsed_data["language_info"],
            # Links and images for GEO analysis
            "links": links[:100],  # Limit to first 100 links
            "images": images[:50],  # Limit to first 50 images
            # Content analysis stats
            "content_stats": content_stats
        }
    
    def save_output(self, output_data, url):
        """Save output data to JSON file"""
        output_dir = ensure_output_directory()
        filename = create_output_filename(url)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        file_size = os.path.getsize(filepath) / 1024  # KB
        
        return {
            "filepath": filepath,
            "filename": filename,
            "file_size_kb": file_size
        }
    
    def print_extraction_summary(self, crawl_info, http_info, structured_data, normalized_data, 
                                links, images, language_info, meta_data, content_data, dom_diff):
        """Print a summary of the extraction results"""
        extraction_time = crawl_info["extraction_time_seconds"]
        js_executed = crawl_info["javascript_executed"]
        js_modified_dom = crawl_info["javascript_modified_dom"]
        
        print(f"\nCONTENT EXTRACTED!")
        print(f"Time: {extraction_time:.2f}s")
        print(f"JavaScript: {' Executed' if js_executed else ' Failed'}")
        print(f"DOM Modified: {' Yes' if js_modified_dom else ' No'}")
        print(f"DOM Changes: {dom_diff['added_nodes_count']} nodes added")
        print(f"HTTP Status: {http_info.get('status_code', 'Unknown')}")
        print(f" Schema.org: {len(structured_data['schema_org'])} items found")
        print(f"Normalized: {len([k for k, v in normalized_data.items() if v])} GEO fields")
        print(f"Links: {len(links)} total")
        print(f"Images: {len(images)} found")
        print(f"Language: {language_info.get('html_lang', 'Not specified')}")
        print(f"Meta Title: {meta_data['title'][:50]}..." if meta_data['title'] else "Meta Title: Not found")
        print(f" Clean Text: {len(content_data['clean_text']):,} characters")
        print(f" Raw HTML: {len(content_data['original_html']):,} characters")
        print(f" Rendered HTML: {len(content_data['rendered_html']):,} characters")
    
    def print_save_summary(self, save_info):
        """Print summary of saved file"""
        print(f"\n CONTENT SAVED: {save_info['filepath']}")
        print(f" File size: {save_info['file_size_kb']:.1f} KB")
        
        
        
