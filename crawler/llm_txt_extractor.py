"""
LLM.txt Extractor Module - Handles extraction of llm.txt files for GEO analysis
Single Responsibility: Detect and extract llm.txt files from websites
"""

import aiohttp
import asyncio
from urllib.parse import urljoin, urlparse
from typing import Dict, Optional, List


class LLMTxtExtractor:
    """Handles detection and extraction of llm.txt files for GEO optimization"""
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.common_llm_txt_paths = [
            '/llms.txt',           # Standard LLMs.txt path
            '/llm.txt',            # Alternative path
            '/.well-known/llms.txt', # Well-known location for llms.txt
            '/.well-known/llm.txt',  # Alternative well-known
            '/ai.txt',
            '/robots/llm.txt',
            '/public/llm.txt',
            '/docs/llms.txt',      # Documentation subdirectory
            '/docs/llm.txt'        # Documentation subdirectory alternative
        ]
        
        # Common subdomains where LLM.txt files are often hosted
        self.common_subdomains = [
            'docs',         # docs.example.com
            'developer',    # developer.example.com  
            'developers',   # developers.example.com
            'platform',     # platform.example.com
            'api',          # api.example.com
            'support',      # support.example.com
            'help',         # help.example.com
            'www'           # www.example.com (fallback)
        ]
    
    async def extract_llm_txt_data(self, base_url: str, html_content: str = None) -> Dict:
        """
        Main method to extract llm.txt data from a website
        Returns comprehensive llm.txt information for GEO analysis
        """
        llm_txt_data = {
            "llm_txt_found": False,
            "llm_txt_url": None,
            "llm_txt_content": None,
            "llm_txt_size_bytes": 0,
            "extraction_method": None,
            "attempts": [],
            "embedded_content": {},
            "parsed_sections": {},
            "geo_relevance_score": 0
        }
        
        # Method 1: Extract from HTML content (how LLMs actually see it)
        if html_content:
            embedded_content = self._extract_from_html(html_content)
            if embedded_content["found"]:
                llm_txt_data.update({
                    "llm_txt_found": True,
                    "llm_txt_content": embedded_content["content"],
                    "llm_txt_size_bytes": len(embedded_content["content"].encode('utf-8')),
                    "extraction_method": embedded_content["method"],
                    "embedded_content": embedded_content
                })
                # Parse the content for GEO analysis
                llm_txt_data["parsed_sections"] = self._parse_llm_txt_content(embedded_content["content"])
                llm_txt_data["geo_relevance_score"] = self._calculate_geo_relevance(llm_txt_data["parsed_sections"])
                return llm_txt_data
        
        # Method 2: Try to find separate llm.txt files (fallback)
        llm_txt_info = await self._find_llm_txt_file(base_url)
        llm_txt_data["attempts"] = llm_txt_info["attempts"]
        
        if llm_txt_info["found"]:
            llm_txt_data.update({
                "llm_txt_found": True,
                "llm_txt_url": llm_txt_info["llm_txt_url"],
                "llm_txt_content": llm_txt_info["llm_txt_content"],
                "llm_txt_size_bytes": llm_txt_info["llm_txt_size_bytes"],
                "extraction_method": llm_txt_info["extraction_method"]
            })
            # Parse the content for GEO analysis
            llm_txt_data["parsed_sections"] = self._parse_llm_txt_content(llm_txt_info["llm_txt_content"])
            llm_txt_data["geo_relevance_score"] = self._calculate_geo_relevance(llm_txt_data["parsed_sections"])
        
        return llm_txt_data
    
    async def _find_llm_txt_file(self, base_url: str) -> Dict:
        """Try multiple common locations for llm.txt files"""
        result = {
            "found": False,
            "llm_txt_found": False,
            "llm_txt_url": None,
            "llm_txt_content": None,
            "llm_txt_size_bytes": 0,
            "extraction_method": None,
            "attempts": []
        }
        
        # Normalize base URL
        if not base_url.startswith(('http://', 'https://')):
            base_url = 'https://' + base_url
        
        parsed_url = urlparse(base_url)
        domain_parts = parsed_url.netloc.split('.')
        
        # Extract root domain (e.g., "example.com" from "www.example.com")
        if len(domain_parts) >= 2:
            root_domain = '.'.join(domain_parts[-2:])  # Get last 2 parts (domain.tld)
        else:
            root_domain = parsed_url.netloc
        
        # Build list of domains to check (main domain + subdomains)
        domains_to_check = [
            f"{parsed_url.scheme}://{parsed_url.netloc}",  # Original domain
        ]
        
        # Add subdomain variations if we're not already on a subdomain
        if not any(sub in parsed_url.netloc for sub in self.common_subdomains):
            for subdomain in self.common_subdomains:
                subdomain_url = f"{parsed_url.scheme}://{subdomain}.{root_domain}"
                if subdomain_url not in domains_to_check:
                    domains_to_check.append(subdomain_url)
        
        # Try each domain + path combination
        for domain in domains_to_check:
            for path in self.common_llm_txt_paths:
                llm_txt_url = urljoin(domain, path)
                attempt_result = await self._fetch_llm_txt(llm_txt_url)
                
                result["attempts"].append({
                    "url": llm_txt_url,
                    "success": attempt_result["success"],
                    "status_code": attempt_result.get("status_code"),
                    "error": attempt_result.get("error")
                })
                
                if attempt_result["success"]:
                    result.update({
                        "found": True,
                        "llm_txt_found": True,
                        "llm_txt_url": llm_txt_url,
                        "llm_txt_content": attempt_result["content"],
                        "llm_txt_size_bytes": len(attempt_result["content"].encode('utf-8')),
                        "extraction_method": f"direct_fetch_{path.replace('/', '_')}_on_{domain.split('//')[1]}"
                    })
                    print(f"Found llm.txt at: {llm_txt_url}")
                    return result
        
        if not result["found"]:
            print("No llm.txt file found at common locations")
        
        return result
    
    def _extract_from_html(self, html_content: str) -> Dict:
        """Extract LLM.txt content embedded in HTML as LLMs would see it"""
        from bs4 import BeautifulSoup
        
        result = {
            "found": False,
            "content": "",
            "method": None,
            "sources": []
        }
        
        if not html_content:
            return result
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            extracted_content = []
            sources = []
            
            # Method 1: Look for HTML comments containing LLM instructions
            from bs4 import Comment
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            for comment in comments:
                comment_text = str(comment).strip()
                if any(keyword in comment_text.lower() for keyword in ['llm', 'ai:', 'gpt', 'assistant', 'model:', 'instructions']):
                    if self._validate_llm_txt_content(comment_text):
                        extracted_content.append(comment_text)
                        sources.append("html_comment")
            
            # Method 2: Look for meta tags with LLM instructions
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                content = meta.get('content', '')
                name = meta.get('name', '').lower()
                property_attr = meta.get('property', '').lower()
                
                if any(keyword in name for keyword in ['llm', 'ai', 'assistant', 'model']) or \
                   any(keyword in property_attr for keyword in ['llm', 'ai', 'assistant', 'model']) or \
                   any(keyword in content.lower() for keyword in ['ai:', 'llm:', 'model:', 'assistant:']):
                    if self._validate_llm_txt_content(content):
                        extracted_content.append(content.strip())
                        sources.append(f"meta_tag_{name or property_attr}")
            
            # Method 3: Look for specific elements with LLM-related classes or IDs
            llm_selectors = [
                '[class*="llm"]', '[class*="ai-"]', '[class*="assistant"]',
                '[id*="llm"]', '[id*="ai-"]', '[id*="assistant"]',
                '[data-llm]', '[data-ai]', '[data-assistant]'
            ]
            
            for selector in llm_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text_content = element.get_text().strip()
                    if text_content and self._validate_llm_txt_content(text_content):
                        extracted_content.append(text_content)
                        sources.append(f"element_{selector}")
            
            # Method 4: Look for JSON-LD with AI/LLM context
            scripts = soup.find_all('script', {'type': 'application/ld+json'})
            for script in scripts:
                try:
                    if script.string:
                        import json
                        data = json.loads(script.string.strip())
                        # Check if JSON contains AI/LLM related fields
                        json_str = json.dumps(data).lower()
                        if any(keyword in json_str for keyword in ['llm', 'ai', 'assistant', 'model', 'gpt']):
                            # Validate the content before accepting it as LLM.txt
                            if self._validate_llm_txt_content(script.string.strip()):
                                extracted_content.append(script.string.strip())
                                sources.append("json_ld")
                except:
                    continue
            
            # Method 5: Look for invisible text (hidden divs that might contain LLM instructions)
            hidden_elements = soup.find_all(['div', 'span', 'p'], 
                                          style=lambda x: x and any(hide in x.lower() for hide in ['display:none', 'visibility:hidden', 'opacity:0']))
            for element in hidden_elements:
                text_content = element.get_text().strip()
                if text_content and self._validate_llm_txt_content(text_content):
                    extracted_content.append(text_content)
                    sources.append("hidden_element")
            
            # Method 6: Search for LLM.txt content in regular text
            all_text = soup.get_text()
            # Look for patterns that suggest LLM instructions
            import re
            llm_patterns = [
                r'(?i)(?:^|\n)\s*(?:ai|llm|model|assistant):\s*.+',
                r'(?i)(?:^|\n)\s*#\s*(?:ai|llm|model|assistant)\s+.+',
                r'(?i)instructions?\s+for\s+(?:ai|llm|model|assistant)',
                r'(?i)(?:ai|llm|model|assistant)\s+(?:instructions?|guidelines?|rules?)'
            ]
            
            for pattern in llm_patterns:
                matches = re.findall(pattern, all_text, re.MULTILINE)
                for match in matches:
                    if self._validate_llm_txt_content(match):
                        extracted_content.append(match.strip())
                        sources.append("text_pattern")
            
            # Combine all found content
            if extracted_content:
                combined_content = "\n\n".join(extracted_content)
                #  Validate the final combined content to ensure it's actually LLM.txt
                if self._validate_llm_txt_content(combined_content):
                    result["found"] = True
                    result["content"] = combined_content
                    result["method"] = f"html_embedded_{len(extracted_content)}_sources"
                    result["sources"] = sources
                else:
                    result["found"] = False
                
        except Exception as e:
            # Silent fail - this is a fallback method
            pass
        
        return result
    
    async def _fetch_llm_txt(self, url: str) -> Dict:
        """Fetch llm.txt content from a specific URL"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, allow_redirects=True) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        
                        # Check if it's likely a text file
                        if 'text' in content_type or content_type == 'application/octet-stream':
                            content = await response.text(encoding='utf-8')
                            
                            # Basic validation - should look like llm.txt format
                            if self._validate_llm_txt_content(content):
                                return {
                                    "success": True,
                                    "content": content,
                                    "content_type": content_type,
                                    "status_code": response.status
                                }
                    
                    return {
                        "success": False,
                        "status_code": response.status,
                        "error": f"HTTP {response.status}"
                    }
        
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout"}
        except aiohttp.ClientError as e:
            return {"success": False, "error": f"Client error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def _validate_llm_txt_content(self, content: str) -> bool:
        """validation to check if content has a valid llm.txt file"""
        if not content or len(content.strip()) < 30:
            return False
        
        content_lower = content.lower().strip()
        
        # Reject Schema.org JSON-LD content (this is NOT LLM.txt!)
        if '"@context"' in content_lower and 'schema.org' in content_lower:
            return False
        
        # Reject other structured data formats that are not LLM.txt
        if content_lower.strip().startswith('{') and content_lower.strip().endswith('}'):
            # If it looks like JSON, check if it's actually LLM.txt JSON or just regular JSON
            json_indicators = ['"@type":', '"@context":', '"name":', '"url":', '"logo":', '"contactpoint":']
            if any(indicator in content_lower for indicator in json_indicators):
                return False
        
        # Check for LLM.txt file format indicators (more inclusive)
        llm_file_indicators = [
            # Header patterns
            'llms.txt', 'llm.txt', '# llms.txt', '# llm.txt',
            # Explicit AI/LLM content
            'ai:', 'llm:', 'model:', 'assistant:', 'chatgpt:', 'gpt:',
            'for ai systems', 'for llm', 'for language models', 'for ai models',
            'ai instructions', 'llm instructions', 'model instructions',
            'when citing this site', 'when summarizing this site', 'ai guidelines',
            # Bot access policies
            'user-agent:', 'allow-training:', 'allow-retrieval:', 'bot access',
            # Common LLM.txt sections
            'sitemap:', 'main navigation:', 'languages supported:',
            # Domain-specific headers
            '.com llms.txt', '.org llms.txt', '.net llms.txt', '.ai llms.txt',
            # Standard LLM.txt content patterns
            '## docs', '## web', '## api', '## documentation',
            '- [', ']('  # Markdown link pattern common in LLM.txt files
        ]
        
        # Check if it has LLM.txt format indicators
        has_llm_indicator = any(indicator in content_lower for indicator in llm_file_indicators)
        
        # Additional check: if it starts with a domain header followed by llms.txt
        lines = content.strip().split('\n')
        if lines and ('llms.txt' in lines[0].lower() or 'llm.txt' in lines[0].lower()):
            has_llm_indicator = True
        
        # Check for standard LLM.txt format: starts with # CompanyName
        if lines and lines[0].strip().startswith('#') and not lines[0].lower().endswith('.txt'):
            # Check if it has typical LLM.txt structure (markdown links to documentation)
            link_count = content.count('](')
            if link_count >= 5:  # Has multiple documentation links
                has_llm_indicator = True
        
        # Check for served from /llms.txt or /llm.txt URL pattern
        # This is inferred from the URL context if available
        if not has_llm_indicator:
            # If content has structured documentation links, likely an LLM.txt file
            if ('](http' in content or '](/') and content.count('\n') > 10:
                has_llm_indicator = True
        
        if not has_llm_indicator:
            return False
        
        # Additional verification - content should not be just regular website text
        # But be more lenient for legitimate LLM.txt files
        website_content_indicators = [
            'copyright', '©', 'all rights reserved', 'privacy policy', 'terms of service',
            'home', 'about us', 'contact us', 'buy now',
            'subscribe', 'newsletter', 'follow us', 'social media'
        ]
        
        website_content_count = sum(1 for indicator in website_content_indicators if indicator in content_lower)
        
        # If it has too many website-like terms AND no clear LLM.txt structure, reject it
        if website_content_count > 3 and not any(term in content_lower for term in ['sitemap:', 'user-agent:', 'allow-training:']):
            return False
        
        return True
    
    def _parse_llm_txt_content(self, content: str) -> Dict:
        """Parse llm.txt content into structured sections for GEO analysis"""
        sections = {
            "headers": [],
            "ai_instructions": [],
            "knowledge_base": [],
            "context_info": [],
            "model_specifications": [],
            "geo_optimization_hints": []
        }
        
        if not content:
            return sections
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect headers
            if line.startswith('#'):
                sections["headers"].append(line)
                current_section = line.lower()
            
            # Detect AI/model related instructions
            elif any(keyword in line.lower() for keyword in ['model:', 'ai:', 'llm:', 'gpt:', 'assistant:']):
                sections["ai_instructions"].append(line)
            
            # Detect knowledge base information
            elif any(keyword in line.lower() for keyword in ['knowledge:', 'training:', 'data:', 'information:']):
                sections["knowledge_base"].append(line)
            
            # Detect context information
            elif any(keyword in line.lower() for keyword in ['context:', 'about:', 'description:', 'purpose:']):
                sections["context_info"].append(line)
            
            # Detect GEO optimization hints
            elif any(keyword in line.lower() for keyword in ['seo:', 'optimization:', 'search:', 'ranking:', 'visibility:']):
                sections["geo_optimization_hints"].append(line)
            
            # General model specifications
            elif any(keyword in line.lower() for keyword in ['version:', 'parameters:', 'capabilities:', 'limitations:']):
                sections["model_specifications"].append(line)
        
        return sections
    
    def _calculate_geo_relevance(self, parsed_sections: Dict) -> int:
        """Calculate a relevance score for GEO analysis (0-100)"""
        score = 0
        
        # Base score for having any content
        if any(sections for sections in parsed_sections.values()):
            score += 20
        
        # Additional points for specific sections
        if parsed_sections["ai_instructions"]:
            score += 25
        
        if parsed_sections["knowledge_base"]:
            score += 20
        
        if parsed_sections["context_info"]:
            score += 15
        
        if parsed_sections["geo_optimization_hints"]:
            score += 20
        
        # Bonus for comprehensive content
        total_items = sum(len(sections) for sections in parsed_sections.values())
        if total_items > 10:
            score += 10
        elif total_items > 5:
            score += 5
        
        return min(score, 100)
