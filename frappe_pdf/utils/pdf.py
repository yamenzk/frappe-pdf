import os
import re
import subprocess
import tempfile
import frappe
from frappe.utils import get_url

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

def get_pdf(html, *a, **b):
    pdf_file_path = f'/tmp/{frappe.generate_hash()}.pdf'
    html = scrub_urls(html)

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".html", delete=False) as html_file:
        html_file.write(html)
        html_file_path = html_file.name

    chrome_path_result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
    chrome_path = chrome_path_result.stdout.strip()

    if not chrome_path:
        print("Error: Google Chrome not found.")
        return None

    print(f"Using Google Chrome at: {chrome_path}")

    chrome_command = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_file_path}",
        "--print-to-pdf-no-header",
        "--print-to-pdf-no-footer",
        "--print-to-pdf-header-template=<div style='font-size: 10px; text-align: center;'><span class='pageNumber'></span> of <span class='totalPages'></span></div>",
        "--print-to-pdf-footer-template=<div style='font-size: 10px; text-align: center;'><span class='pageNumber'></span> of <span class='totalPages'></span></div>",
        html_file_path
    ]

    result = subprocess.run(chrome_command, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error executing Chrome command: {result.stderr}")
        return None

    if not os.path.exists(pdf_file_path):
        print(f"PDF file not generated at {pdf_file_path}")
        return None

    with open(pdf_file_path, 'rb') as f:
        content = f.read()

    os.remove(pdf_file_path)
    os.remove(html_file_path)

    return content

