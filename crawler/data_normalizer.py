"""
Data Normalizer Module - Handles structured data normalization for GEO analysis
Single Responsibility: Normalize and extract GEO-relevant fields from structured data
"""


class DataNormalizer:
    """Normalizes structured data for easy GEO model consumption"""
    
    def __init__(self):
        pass
    
    def normalize_structured_data(self, structured_data):
        """Extract and normalize key fields from JSON-LD for easy GEO model access"""
        normalized = {
            "datePublished": None,
            "dateModified": None,
            "author": None,
            "publisher": None,
            "geo": None,
            "breadcrumbs": [],
            "faq": [],
            "contact": None,
            "place": None,
            "address": None
        }
        
        for item in structured_data.get("schema_org", []):
            data = item.get("data", {})
            if isinstance(data, dict):
                self._extract_from_schema_item(data, normalized)
        
        return normalized
    
    def _extract_from_schema_item(self, data, normalized):
        """Extract fields from a single schema.org item"""
        schema_type = data.get("@type", "")
        
        # Extract dates
        if "datePublished" in data:
            normalized["datePublished"] = data["datePublished"]
        if "dateModified" in data:
            normalized["dateModified"] = data["dateModified"]
        
        # Extract author
        if "author" in data:
            normalized["author"] = self._extract_author(data["author"])
        
        # Extract publisher
        if "publisher" in data:
            normalized["publisher"] = self._extract_publisher(data["publisher"])
        
        # Extract geo data
        if "geo" in data or schema_type in ["Place", "LocalBusiness"]:
            geo_data = self._extract_geo_coordinates(data, schema_type)
            if geo_data:
                normalized["geo"] = geo_data
        
        # Extract address
        if "address" in data:
            normalized["address"] = data["address"]
        
        # Extract place info
        if schema_type in ["Place", "LocalBusiness", "Organization"]:
            normalized["place"] = self._extract_place_info(data, schema_type)
        
        # Extract breadcrumbs
        if schema_type == "BreadcrumbList" and "itemListElement" in data:
            normalized["breadcrumbs"].extend(self._extract_breadcrumbs(data["itemListElement"]))
        
        # Extract FAQ
        if schema_type == "FAQPage" and "mainEntity" in data:
            normalized["faq"].extend(self._extract_faq(data["mainEntity"]))
        
        # Extract contact info
        if schema_type == "ContactPoint" or "contactPoint" in data:
            contact_data = self._extract_contact_info(data)
            if contact_data:
                normalized["contact"] = contact_data
    
    def _extract_author(self, author_data):
        """Extract author information"""
        if isinstance(author_data, dict):
            return author_data.get("name", str(author_data))
        return str(author_data)
    
    def _extract_publisher(self, publisher_data):
        """Extract publisher information"""
        if isinstance(publisher_data, dict):
            return publisher_data.get("name", str(publisher_data))
        return str(publisher_data)
    
    def _extract_geo_coordinates(self, data, schema_type):
        """Extract geographic coordinates"""
        geo_data = data.get("geo", data)
        if isinstance(geo_data, dict):
            if "@type" in geo_data and "GeoCoordinates" in geo_data["@type"]:
                return {
                    "latitude": geo_data.get("latitude"),
                    "longitude": geo_data.get("longitude")
                }
            elif "latitude" in geo_data and "longitude" in geo_data:
                return {
                    "latitude": geo_data.get("latitude"),
                    "longitude": geo_data.get("longitude")
                }
        return None
    
    def _extract_place_info(self, data, schema_type):
        """Extract place/business information"""
        return {
            "name": data.get("name"),
            "type": schema_type,
            "address": data.get("address"),
            "telephone": data.get("telephone"),
            "url": data.get("url")
        }
    
    def _extract_breadcrumbs(self, breadcrumb_items):
        """Extract breadcrumb navigation"""
        breadcrumbs = []
        for item in breadcrumb_items:
            if isinstance(item, dict):
                breadcrumbs.append({
                    "name": item.get("name"),
                    "url": item.get("item", item.get("url")),
                    "position": item.get("position")
                })
        return breadcrumbs
    
    def _extract_faq(self, faq_items):
        """Extract FAQ questions and answers"""
        faq = []
        for faq_item in faq_items:
            if isinstance(faq_item, dict):
                question = faq_item.get("name", "")
                answer = self._extract_faq_answer(faq_item.get("acceptedAnswer"))
                faq.append({
                    "question": question,
                    "answer": answer
                })
        return faq
    
    def _extract_faq_answer(self, answer_data):
        """Extract FAQ answer text"""
        if not answer_data:
            return ""
        if isinstance(answer_data, dict):
            return answer_data.get("text", str(answer_data))
        return str(answer_data)
    
    def _extract_contact_info(self, data):
        """Extract contact information"""
        contact_data = data.get("contactPoint", data)
        if isinstance(contact_data, dict):
            return {
                "telephone": contact_data.get("telephone"),
                "email": contact_data.get("email"),
                "contactType": contact_data.get("contactType"),
                "areaServed": contact_data.get("areaServed")
            }
        return None
    
    def calculate_content_stats(self, clean_text, links, images):
        """Calculate basic content statistics"""
        return {
            "word_count": len(clean_text.split()) if clean_text else 0,
            "link_count": len(links),
            "image_count": len(images),
            "internal_link_count": len([l for l in links if l.get("is_internal")]),
            "external_link_count": len([l for l in links if not l.get("is_internal")])
        }
