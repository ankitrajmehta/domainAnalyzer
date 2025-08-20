"""

Extracts content exactly as modern LLMs would see it for GEO analysis
"""

from .core_crawler import GEOCrawler
from .html_parser import HTMLParser
from .data_normalizer import DataNormalizer
from .output_handler import OutputHandler
from .utils import create_output_filename, ensure_output_directory

__version__ = "1.0.0"
__all__ = [
    "GEOCrawler",
    "HTMLParser", 
    "DataNormalizer",
    "OutputHandler",
    "create_output_filename",
    "ensure_output_directory"
]
