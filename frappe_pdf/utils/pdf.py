import os
import re
import asyncio
import frappe
from pyppeteer import launch
from frappe.utils import get_url

# Regular expressions for expanding URLs in HTML content
URLS_NOT_HTTP_TAG_PATTERN = re.compile(
    r'(href|src){1}([\s]*=[\s]*[\'"]?)((?!http)[^\'">]+)([\'"]?)'
)
URL_NOT_HTTP_NOTATION_PATTERN = re.compile(
    r'(:[\s]?url)(\([\'"]?)((?!http)[^\'">]+)([\'"]?\))'
)

async def scrub_urls(html: str) -> str:
    """Expands relative URLs in HTML content to absolute URLs."""
    return await expand_relative_urls(html)

async def expand_relative_urls(html: str) -> str:
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

async def get_pdf(html: str, **kwargs) -> bytes:
    """Generates a PDF from HTML using pyppeteer with custom header and footer.
    
    Args:
        html (str): The HTML content to convert to PDF.
        **kwargs: Arbitrary keyword arguments. Can be used to pass extra options for PDF generation.

    Returns:
        bytes: The generated PDF content.
    """
    browser = await launch(headless=True, args=['--no-sandbox'])
    page = await browser.newPage()

    # Set content with expanded URLs
    html = await scrub_urls(html)
    await page.setContent(html)

    # Specify PDF options, including custom header and footer
    pdf_path = f'/tmp/{frappe.generate_hash()}.pdf'
    pdf_options = {
        'path': pdf_path,
        'format': 'A4',
        'printBackground': True,
        'margin': {'top': '60px', 'right': '40px', 'bottom': '60px', 'left': '40px'},
        'displayHeaderFooter': True,
        'headerTemplate': '<span style="font-size: 10px; width: 100%; text-align: center;">My Custom Header</span>',
        'footerTemplate': '<span style="font-size: 10px; width: 100%; text-align: center;"><span class="pageNumber"></span> of <span class="totalPages"></span></span>',
    }

    # Here, you could check for any relevant kwargs and adjust pdf_options accordingly.
    # For example:
    # if 'margin' in kwargs:
    #     pdf_options['margin'] = kwargs['margin']

    await page.pdf(pdf_options)
    await browser.close()

    # Read and return PDF content
    with open(pdf_path, 'rb') as f:
        content = f.read()

    # Cleanup
    os.remove(pdf_path)

    return content
