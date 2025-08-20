"""
Utility functions for the GEO crawler
"""

import os
import re
from datetime import datetime
from urllib.parse import urlparse


def create_output_filename(url):
    """Create a clean filename for the extracted content"""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace('www.', '')
    path = parsed_url.path.strip('/').replace('/', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if path:
        filename = f"crawled_content_{domain}_{path}_{timestamp}.json"
    else:
        filename = f"crawled_content_{domain}_{timestamp}.json"

    # Clean filename
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return filename


def ensure_output_directory():
    """Ensure the output_json directory exists"""
    output_dir = "output_json"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir


def is_internal_link(href, base_domain):
    """Check if a link is internal to the domain"""
    try:
        link_domain = urlparse(href).netloc
        return link_domain == base_domain or link_domain == ''
    except:
        return False


def clean_text_for_analysis(text, max_length=200):
    """Clean and truncate text for analysis"""
    if not text:
        return ""
    return text.strip()[:max_length]


def extract_domain(url):
    """Extract domain from URL"""
    try:
        return urlparse(url).netloc
    except:
        return ""
