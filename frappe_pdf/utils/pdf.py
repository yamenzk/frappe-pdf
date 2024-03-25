import os
import re
import asyncio
import tempfile
import frappe
from frappe.utils import get_url
from pyppeteer import launch
import subprocess

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

async def generate_pdf(html, pdf_file_path):
    browser = await launch(executablePath=chrome_path)
    page = await browser.newPage()
    await page.setContent(html)
    await page.pdf({'path': pdf_file_path, 'format': 'A4'})
    await browser.close()

def get_pdf(html, *a, **b):
    pdf_file_path = f'/tmp/{frappe.generate_hash()}.pdf'
    html = scrub_urls(html)

    # Get Chrome path
    chrome_path_result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
    chrome_path = chrome_path_result.stdout.strip()

    # Use Pyppeteer to generate PDF
    asyncio.get_event_loop().run_until_complete(generate_pdf(html, pdf_file_path))

    if not os.path.exists(pdf_file_path):
        print(f"PDF file not generated at {pdf_file_path}")
        return None

    with open(pdf_file_path, 'rb') as f:
        content = f.read()

    os.remove(pdf_file_path)

    return content
