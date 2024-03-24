import os
import re
import tempfile
import frappe
from frappe.utils import get_url
from weasyprint import HTML

URLS_NOT_HTTP_TAG_PATTERN = re.compile(
    r'(href|src){1}([\s]*=[\s]*[\'"]?)((?!http)[^\'">]+)([\'"]?)'
)
URL_NOT_HTTP_NOTATION_PATTERN = re.compile(
    r'(:[\s]?url)(\([\'"]?)((?!http)[^\'">]+)([\'"]?\))'
)

def scrub_urls(html: str) -> str:
    """Expands relative URLs in HTML content to absolute URLs."""
    return expand_relative_urls(html)

def expand_relative_urls(html: str) -> str:
    """Helper function to expand relative URLs to absolute URLs."""
    url = get_url().rstrip("/")
    
    URLS_HTTP_TAG_PATTERN = re.compile(
        r'(href|src)([\s]*=[\s]*[\'"]?)((?:{0})[^\'">]+)([\'"]?)'.format(re.escape(url.replace("https://", "http://")))
    )
    URL_HTTP_NOTATION_PATTERN = re.compile(
        r'(:[\s]?url)(\([\'"]?)((?:{0})[^\'">]+)([\'"]?\))'.format(re.escape(url.replace("https://", "http://")))
    )
    
    def _expand_relative_urls(match):
        to_expand = list(match.groups())
        if not to_expand[2].startswith(("mailto", "data:", "tel:")):
            if not to_expand[2].startswith(url):
                to_expand[2] = "/" + to_expand[2] if not to_expand[2].startswith("/") else to_expand[2]
                to_expand.insert(2, url)
        return "".join(to_expand)

    html = URLS_HTTP_TAG_PATTERN.sub(_expand_relative_urls, html)
    html = URLS_NOT_HTTP_TAG_PATTERN.sub(_expand_relative_urls, html)
    html = URL_NOT_HTTP_NOTATION_PATTERN.sub(_expand_relative_urls, html)
    html = URL_HTTP_NOTATION_PATTERN.sub(_expand_relative_urls, html)

    return html

def get_pdf(html: str, *args, **kwargs):
    """Generates a PDF from HTML content using WeasyPrint."""
    # Generate a unique file path for the output PDF
    pdf_file_path = f'/tmp/{frappe.generate_hash()}.pdf'
    html = scrub_urls(html)  # Process HTML to expand URLs

    # Use WeasyPrint to generate the PDF
    HTML(string=html).write_pdf(target=pdf_file_path)

    # Read and return the PDF file content
    try:
        with open(pdf_file_path, 'rb') as pdf_file:
            content = pdf_file.read()
        # Cleanup: Remove the PDF file after reading its content
        os.remove(pdf_file_path)
        return content
    except Exception as e:
        print(f"Error reading or cleaning up PDF file: {str(e)}")
        return None
