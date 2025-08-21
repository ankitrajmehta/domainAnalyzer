"""
Simplified Structure Analyzer for GEO Optimization

Analyzes website structure and prepares data for AI-powered recommendations.
"""

import re
from typing import Dict, Any
from urllib.parse import urlparse


class StructureAnalyzer:
    """
    Simplified analyzer that extracts key structure metrics for AI analysis.
    """
    
    def analyze_for_recommendations(self, crawled_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze website structure and prepare summary for AI recommendations.
        
        Args:
            crawled_data: Dictionary containing crawled website data
            
        Returns:
            Dictionary containing key metrics for AI analysis
        """
        clean_text = crawled_data.get("clean_text", "")
        rendered_html = crawled_data.get("rendered_html", "")
        meta_data = crawled_data.get("meta_data", {})
        
        analysis = {
            "content_metrics": {
                "word_count": len(clean_text.split()),
                "paragraph_count": len([p for p in clean_text.split('\n\n') if p.strip()]),
                "content_length": len(clean_text)
            },
            "heading_structure": self._analyze_headings(rendered_html),
            "semantic_elements": self._analyze_semantic_elements(rendered_html),
            "meta_completeness": self._analyze_meta_tags(meta_data),
            "structural_issues": self._identify_issues(rendered_html, meta_data, clean_text)
        }
        
        return analysis
    
    def _analyze_headings(self, html: str) -> Dict[str, Any]:
        """Analyze heading structure."""
        headings = {}
        issues = []
        
        for i in range(1, 7):
            pattern = f'<h{i}[^>]*>(.*?)</h{i}>'
            matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
            headings[f"h{i}"] = len(matches)
        
        # Check for issues
        if headings.get("h1", 0) == 0:
            issues.append("missing_h1")
        elif headings.get("h1", 0) > 1:
            issues.append("multiple_h1")
        
        return {
            "distribution": headings,
            "total": sum(headings.values()),
            "issues": issues
        }
    
    def _analyze_semantic_elements(self, html: str) -> Dict[str, Any]:
        """Analyze semantic HTML elements."""
        elements = {
            "article": len(re.findall(r'<article[^>]*>', html, re.IGNORECASE)),
            "section": len(re.findall(r'<section[^>]*>', html, re.IGNORECASE)),
            "nav": len(re.findall(r'<nav[^>]*>', html, re.IGNORECASE)),
            "header": len(re.findall(r'<header[^>]*>', html, re.IGNORECASE)),
            "footer": len(re.findall(r'<footer[^>]*>', html, re.IGNORECASE)),
            "main": len(re.findall(r'<main[^>]*>', html, re.IGNORECASE))
        }
        
        present_count = sum(1 for v in elements.values() if v > 0)
        semantic_score = present_count / len(elements)
        
        return {
            "elements": elements,
            "semantic_score": semantic_score,
            "missing_elements": [k for k, v in elements.items() if v == 0]
        }
    
    def _analyze_meta_tags(self, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze meta tag completeness."""
        critical_tags = ["title", "description"]
        social_tags = ["og:title", "og:description", "og:image"]
        
        present_critical = sum(1 for tag in critical_tags if tag in meta_data)
        present_social = sum(1 for tag in social_tags if tag in meta_data)
        
        return {
            "critical_completeness": present_critical / len(critical_tags),
            "social_completeness": present_social / len(social_tags),
            "missing_critical": [tag for tag in critical_tags if tag not in meta_data],
            "missing_social": [tag for tag in social_tags if tag not in meta_data]
        }
    
    def _identify_issues(self, html: str, meta_data: Dict[str, Any], clean_text: str) -> list:
        """Identify key structural issues."""
        issues = []
        
        # Content issues
        word_count = len(clean_text.split())
        if word_count < 300:
            issues.append("insufficient_content")
        
        # Meta issues
        if "title" not in meta_data:
            issues.append("missing_title")
        if "description" not in meta_data:
            issues.append("missing_description")
        
        # Semantic issues
        if not re.search(r'<article[^>]*>', html, re.IGNORECASE):
            issues.append("missing_article_tags")
        if not re.search(r'<main[^>]*>', html, re.IGNORECASE):
            issues.append("missing_main_tag")
        
        return issues
