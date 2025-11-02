from bs4 import BeautifulSoup, Comment
from bs4.element import NavigableString
import re


def clean_html(html: str, preserve_structure: bool = True) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, 'lxml')
    for script in soup.find_all('script'):
        script.decompose()
    for style in soup.find_all('style'):
        style.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for meta in soup.find_all('meta'):
        meta.decompose()
    for link in soup.find_all('link'):
        link.decompose()
    for noscript in soup.find_all('noscript'):
        noscript.decompose()
    for tag in soup.find_all(True):
        event_attrs = [attr for attr in tag.attrs if attr.startswith('on')]
        for attr in event_attrs:
            del tag.attrs[attr]
        for attr_name, attr_value in tag.attrs.items():
            if isinstance(attr_value, str) and attr_value.startswith('javascript:'):
                del tag.attrs[attr_name]
    if preserve_structure:
        for element in soup.find_all(string=True):
            if isinstance(element, NavigableString) and element.parent.name not in ['script', 'style']:
                cleaned_text = ' '.join(element.split())
                element.replace_with(cleaned_text)
    else:
        return soup.get_text(separator=' ', strip=True)
    return str(soup)


def get_html_stats(html: str) -> dict:
    if not html:
        return {
            'element_count': 0,
            'text_length': 0,
            'link_count': 0,
            'image_count': 0,
            'table_count': 0
        }
    soup = BeautifulSoup(html, 'lxml')
    all_elements = soup.find_all(True)
    links = soup.find_all('a')
    images = soup.find_all('img')
    tables = soup.find_all('table')
    text_content = soup.get_text()
    return {
        'element_count': len(all_elements),
        'text_length': len(text_content),
        'link_count': len(links),
        'image_count': len(images),
        'table_count': len(tables),
        'cleaned_html_length': len(str(soup))
    }


def extract_text_content(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, 'lxml')
    for script in soup(['script', 'style']):
        script.decompose()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    return text
