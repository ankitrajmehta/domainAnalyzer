"""
HTML Parser Module - Handles all HTML parsing and data extraction
Single Responsibility: Parse HTML and extract structured information
"""

import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from .utils import is_internal_link, clean_text_for_analysis, extract_domain


class HTMLParser:
    """Handles all HTML parsing operations for GEO analysis"""
    
    def __init__(self):
        self.parser = 'html.parser'
    
    def parse_structured_data(self, html_content):
        """Extract and parse schema.org structured data from HTML"""
        structured_data = {
            "schema_org": [],
            "json_ld_count": 0,
            "microdata_count": 0
        }
        
        if not html_content:
            return structured_data
        
        try:
            soup = BeautifulSoup(html_content, self.parser)
            
            # Find all JSON-LD scripts
            json_ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
            structured_data["json_ld_count"] = len(json_ld_scripts)
            
            for script in json_ld_scripts:
                try:
                    if script.string:
                        json_data = json.loads(script.string.strip())
                        structured_data["schema_org"].append({
                            "type": "JSON-LD",
                            "data": json_data
                        })
                except json.JSONDecodeError:
                    continue
            
            # Count microdata elements
            microdata_elements = soup.find_all(attrs={"itemscope": True})
            structured_data["microdata_count"] = len(microdata_elements)
            
        except Exception as e:
            print(f"  Schema.org parsing warning: {e}")
        
        return structured_data
    
    def extract_meta_data(self, html_content):
        """Extract key meta tags and OpenGraph data"""
        meta_data = {
            "title": "",
            "description": "",
            "canonical": "",
            "robots": "",
            "hreflang": [],
            "open_graph": {},
            "twitter": {},
            "viewport": ""
        }
        
        if not html_content:
            return meta_data
        
        try:
            soup = BeautifulSoup(html_content, self.parser)
            
            # Title
            title_tag = soup.find('title')
            if title_tag:
                meta_data["title"] = title_tag.get_text().strip()
            
            # Meta description
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                meta_data["description"] = desc_tag.get('content', '')
            
            # Canonical URL
            canonical_tag = soup.find('link', attrs={'rel': 'canonical'})
            if canonical_tag:
                meta_data["canonical"] = canonical_tag.get('href', '')
            
            # Robots meta
            robots_tag = soup.find('meta', attrs={'name': 'robots'})
            if robots_tag:
                meta_data["robots"] = robots_tag.get('content', '')
            
            # Viewport
            viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
            if viewport_tag:
                meta_data["viewport"] = viewport_tag.get('content', '')
            
            # Hreflang links
            hreflang_tags = soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True})
            for tag in hreflang_tags:
                meta_data["hreflang"].append({
                    "hreflang": tag.get('hreflang'),
                    "href": tag.get('href')
                })
            
            # OpenGraph tags
            og_tags = soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')})
            for tag in og_tags:
                prop = tag.get('property', '').replace('og:', '')
                content = tag.get('content', '')
                if prop and content:
                    meta_data["open_graph"][prop] = content
            
            # Twitter tags
            twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
            for tag in twitter_tags:
                name = tag.get('name', '').replace('twitter:', '')
                content = tag.get('content', '')
                if name and content:
                    meta_data["twitter"][name] = content
            
        except Exception as e:
            print(f"  Meta data parsing warning: {e}")
        
        return meta_data
    
    def extract_links_and_images(self, html_content, base_url):
        """Extract all links and images from HTML for GEO analysis"""
        links = []
        images = []
        
        if not html_content:
            return links, images
        
        try:
            soup = BeautifulSoup(html_content, self.parser)
            base_domain = extract_domain(base_url)
            
            # Extract links
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href', '').strip()
                if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue
                
                # Resolve relative URLs
                full_url = urljoin(base_url, href)
                
                links.append({
                    "href": full_url,
                    "text": clean_text_for_analysis(a_tag.get_text()),
                    "rel": a_tag.get('rel', []),
                    "is_internal": is_internal_link(full_url, base_domain),
                    "anchor_hash": href.split('#')[-1] if '#' in href else None,
                    "title": a_tag.get('title', '')
                })
            
            # Extract images
            for img_tag in soup.find_all('img'):
                src = img_tag.get('src', '').strip()
                if not src:
                    continue
                
                # Resolve relative URLs
                if not src.startswith(('data:', 'http')):
                    src = urljoin(base_url, src)
                
                images.append({
                    "src": src,
                    "alt": img_tag.get('alt', ''),
                    "width": img_tag.get('width'),
                    "height": img_tag.get('height'),
                    "title": img_tag.get('title', ''),
                    "is_data_uri": src.startswith('data:')
                })
        
        except Exception as e:
            print(f"  Link/image extraction warning: {e}")
        
        return links, images
    
    def extract_language_info(self, html_content, http_info):
        """Extract language information from HTML and headers"""
        lang_info = {
            "html_lang": None,
            "content_language_header": http_info.get("content_language"),
            "hreflang_alternatives": []
        }
        
        if not html_content:
            return lang_info
        
        try:
            soup = BeautifulSoup(html_content, self.parser)
            
            # Extract HTML lang attribute
            html_tag = soup.find('html')
            if html_tag and html_tag.get('lang'):
                lang_info["html_lang"] = html_tag.get('lang')
            
            # Extract hreflang alternatives
            hreflang_tags = soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True})
            for tag in hreflang_tags:
                lang_info["hreflang_alternatives"].append({
                    "hreflang": tag.get('hreflang'),
                    "href": tag.get('href')
                })
        
        except Exception as e:
            print(f" Language extraction warning: {e}")
        
        return lang_info
    
    def calculate_dom_diff(self, original_html, rendered_html):
        """Calculate difference between original and rendered HTML"""
        diff_summary = {
            "added_nodes_count": 0,
            "removed_nodes_count": 0,
            "sample_added_selectors": [],
            "has_significant_changes": False
        }
        
        if not original_html or not rendered_html or original_html == rendered_html:
            return diff_summary
        
        try:
            original_soup = BeautifulSoup(original_html, self.parser)
            rendered_soup = BeautifulSoup(rendered_html, self.parser)
            
            # Simple heuristic: count elements with IDs
            original_ids = set([elem.get('id') for elem in original_soup.find_all(id=True)])
            rendered_ids = set([elem.get('id') for elem in rendered_soup.find_all(id=True)])
            
            added_ids = rendered_ids - original_ids
            removed_ids = original_ids - rendered_ids
            
            diff_summary["added_nodes_count"] = len(added_ids)
            diff_summary["removed_nodes_count"] = len(removed_ids)
            diff_summary["sample_added_selectors"] = list(added_ids)[:10]
            diff_summary["has_significant_changes"] = len(added_ids) > 0 or len(removed_ids) > 0
            
            # Also check for script-injected content
            original_scripts = len(original_soup.find_all('script'))
            rendered_scripts = len(rendered_soup.find_all('script'))
            if rendered_scripts > original_scripts:
                diff_summary["has_significant_changes"] = True
                
        except Exception as e:
            print(f"  DOM diff calculation warning: {e}")
        
        return diff_summary
