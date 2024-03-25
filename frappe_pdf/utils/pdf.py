import os
import re
import subprocess
import tempfile
import frappe
from frappe.utils import get_url
import asyncio
from pyppeteer import launch

URLS_NOT_HTTP_TAG_PATTERN = re.compile(
    r'(href|src){1}([\s]*=[\s]*[\'"]?)((?!http)[^\'">]+)([\'"]?)'
)
URL_NOT_HTTP_NOTATION_PATTERN = re.compile(
    r'(:[\s]?url)(\([\'"]?)((?!http)[^\'">]+)([\'"]?\))'
)

def scrub_urls(html: str) -> str:
    return expand_relative_urls(html)

def expand_relative_urls(html: str) -> str:
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

async def get_pdf(html):
    pdf_file_path = f'/tmp/{frappe.generate_hash()}.pdf'
    html = scrub_urls(html)

    browser = await launch()
    page = await browser.newPage()
    await page.setContent(html)

    # Set up PDF options
    pdf_options = {
        'path': pdf_file_path,
        'format': 'A4',
        'printBackground': True,
        'displayHeaderFooter': True,
        'headerTemplate': '<div style="font-size:10px;text-align:center;width:100%"><b>Header content here</b></div>',
        'footerTemplate': '<div style="font-size:10px;text-align:center;width:100%"><b>Footer content here</b></div>',
        'margin': {
            'top': '30px',
            'right': '30px',
            'bottom': '70px',
            'left': '30px'
        }
    }

    # Generate PDF
    await page.pdf(pdf_options)
    await browser.close()

    # Read and return the PDF content
    with open(pdf_file_path, 'rb') as f:
        content = f.read()

    os.remove(pdf_file_path)

    return content

# Run the async function
pdf_content = asyncio.get_event_loop().run_until_complete(get_pdf(html))
