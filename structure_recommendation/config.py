"""
Configuration settings for the Structure Recommendation System.
"""

# Analysis Configuration
ANALYSIS_CONFIG = {
    "min_word_count": 300,
    "target_word_count": 500,
    "min_readability_score": 60,
    "target_readability_score": 80,
    "min_semantic_score": 0.6,
    "target_semantic_score": 0.8,
}

# Content Gap Priority Mapping
CONTENT_GAP_PRIORITIES = {
    "faq": "high",
    "how_to": "high", 
    "benefits": "medium",
    "features": "medium",
    "comparison": "medium",
    "pricing": "low",
    "testimonials": "low",
    "about": "low"
}

# Semantic Element Priorities
SEMANTIC_ELEMENT_PRIORITIES = {
    "article": "high",
    "main": "high",
    "header": "medium",
    "nav": "medium",
    "section": "medium",
    "aside": "low",
    "footer": "low"
}

# Critical Meta Tags
CRITICAL_META_TAGS = ["title", "description", "keywords"]
SOCIAL_META_TAGS = ["og:title", "og:description", "og:image", "og:url"]
TWITTER_META_TAGS = ["twitter:card", "twitter:title", "twitter:description"]

# Report Configuration
REPORT_CONFIG = {
    "max_recommendations_per_category": 10,
    "max_key_findings": 5,
    "max_top_priorities": 5
}

# GEO Optimization Guidelines
GEO_GUIDELINES = {
    "content": {
        "min_words": 300,
        "recommended_words": 500,
        "max_sentence_length": 20,
        "min_readability": 60
    },
    "structure": {
        "max_h1_tags": 1,
        "require_semantic_elements": ["article", "main"],
        "recommended_semantic_elements": ["header", "nav", "section"]
    },
    "meta": {
        "required_tags": ["title", "description"],
        "recommended_tags": ["og:title", "og:description", "og:image"]
    }
}
