import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import csv
import json
import logging
import re
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class ContentScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Removing extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Removing common unwanted patterns
        text = re.sub(r'Advertisement\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Subscribe\s*', '', text, flags=re.IGNORECASE)
        
        return text
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML, avoiding nav/footer/ads."""
        main_selectors = [
            'article', 'main', '[role="main"]', 
            '.content', '.post-content', '.entry-content',
            '.article-body', '.story-body'
        ]
        
        main_content = None
        for selector in main_selectors:
            elements = soup.select(selector)
            if elements:
                main_content = elements[0]
                break
        
        if not main_content:
            # Fall back to body but remove nav/footer
            main_content = soup.find('body')
            if main_content:
                # Removing navigation, footer, sidebar elements
                for unwanted in main_content.find_all(['nav', 'footer', 'aside', 'header']):
                    unwanted.decompose()
                
                # Removing elements with unwanted classes/ids
                unwanted_patterns = [
                    'nav', 'footer', 'sidebar', 'advertisement', 'ads',
                    'social', 'share', 'subscribe', 'newsletter'
                ]
                for pattern in unwanted_patterns:
                    for element in main_content.find_all(attrs={'class': re.compile(pattern, re.I)}):
                        element.decompose()
                    for element in main_content.find_all(attrs={'id': re.compile(pattern, re.I)}):
                        element.decompose()
        
        return main_content
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract metadata"""
        metadata = {
            'url': url,
            'title': '',
            'description': '',
            'author': '',
            'published_date': '',
            'tags': []
        }
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()
        
        # Meta description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            metadata['description'] = desc_tag.get('content', '').strip()
        
        # Author
        author_tag = soup.find('meta', attrs={'name': 'author'})
        if author_tag:
            metadata['author'] = author_tag.get('content', '').strip()
        
        # Published date
        date_selectors = [
            'meta[property="article:published_time"]',
            'meta[name="publish_date"]',
            'time[datetime]',
            '.published-date',
            '.post-date'
        ]
        
        for selector in date_selectors:
            date_element = soup.select_one(selector)
            if date_element:
                if date_element.name == 'meta':
                    metadata['published_date'] = date_element.get('content', '').strip()
                elif date_element.name == 'time':
                    metadata['published_date'] = date_element.get('datetime', '').strip()
                else:
                    metadata['published_date'] = date_element.get_text().strip()
                break
        
        # Tags/Keywords
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag:
            keywords = keywords_tag.get('content', '').strip()
            metadata['tags'] = [tag.strip() for tag in keywords.split(',') if tag.strip()]
        
        return metadata
    
    def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape content from a URL."""
        try:
            logger.info(f"Scraping URL: {url}")
            
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme:
                url = 'https://' + url
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract metadata
            metadata = self._extract_metadata(soup, url)
            
            # Extract main content
            main_content = self._extract_main_content(soup)
            
            if main_content:
                # Get text content
                text_content = main_content.get_text(separator=' ', strip=True)
                text_content = self._clean_text(text_content)
                
                # Get structured content (headings, paragraphs, lists)
                structured_content = []
                
                for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol']):
                    if element.name.startswith('h'):
                        structured_content.append({
                            'type': 'heading',
                            'level': int(element.name[1]),
                            'text': self._clean_text(element.get_text())
                        })
                    elif element.name == 'p':
                        text = self._clean_text(element.get_text())
                        if text and len(text) > 10:  # Avoiding very short paragraphs
                            structured_content.append({
                                'type': 'paragraph',
                                'text': text
                            })
                    elif element.name in ['ul', 'ol']:
                        items = []
                        for li in element.find_all('li'):
                            item_text = self._clean_text(li.get_text())
                            if item_text:
                                items.append(item_text)
                        if items:
                            structured_content.append({
                                'type': 'list',
                                'list_type': element.name,
                                'items': items
                            })
                
                return {
                    'success': True,
                    'metadata': metadata,
                    'text_content': text_content,
                    'structured_content': structured_content,
                    'word_count': len(text_content.split()),
                    'character_count': len(text_content)
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not extract main content from the page',
                    'metadata': metadata
                }
                
        except requests.RequestException as e:
            logger.error(f"Network error scraping {url}: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'url': url
            }
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }


def scrape_content(url: str, output_format: str) -> str:
    scraper = ContentScraper()
    result = scraper.scrape_url(url)
    
    if not result['success']:
        return f"Error scraping {url}: {result['error']}"
    
    if output_format.lower() == "text":
        return f"Title: {result['metadata']['title']}\n\n{result['text_content']}"
    
    elif output_format.lower() == "json":
        return json.dumps(result, indent=2, ensure_ascii=False)
    
    elif output_format.lower() == "csv":
        # CSV format for structured content
        output_lines = []
        output_lines.append("type,level,text")
        
        # Adding metadata
        output_lines.append(f"title,,\"{result['metadata']['title']}\"")
        output_lines.append(f"url,,\"{result['metadata']['url']}\"")
        output_lines.append(f"description,,\"{result['metadata']['description']}\"")
        
        # Add structured content
        for item in result['structured_content']:
            if item['type'] == 'heading':
                output_lines.append(f"heading,{item['level']},\"{item['text']}\"")
            elif item['type'] == 'paragraph':
                output_lines.append(f"paragraph,,\"{item['text']}\"")
            elif item['type'] == 'list':
                for list_item in item['items']:
                    output_lines.append(f"list_item,,\"{list_item}\"")
        
        return "\n".join(output_lines)
    
    else:
        return f"Title: {result['metadata']['title']}\n\n{result['text_content']}"


# Wrapper function to match your existing tool pattern
def scraper_tool(args: Dict[str, Any]) -> str:
    """Tool wrapper for scraping content."""
    url = args.get('url', '')
    output_format = args.get('format', 'text')
    
    if not url:
        return "Error: No URL provided for scraping."
    
    return scrape_content(url, output_format)