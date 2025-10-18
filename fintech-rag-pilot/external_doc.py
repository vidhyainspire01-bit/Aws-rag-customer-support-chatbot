import requests
from pathlib import Path

pdf_urls = [
    ("rbi_exchange_notes.pdf", "https://www.rbi.org.in/commonman/Upload/English/Notification/PDFs/03MC020718.pdf"),
    ("rbi_customer_service.pdf", "https://www.rbi.org.in/commonman/Upload/English/Notification/PDFs/69BC290613FC.pdf"),
    ("sample_invoice_wmaccess.pdf", "https://www.wmaccess.com/downloads/sample-invoice.pdf"),
    ("sample_bank_statement.pdf","https://www.bankofengland.co.uk/-/media/boe/files/statistics/research-datasets/sovereign-default-database-methodology-assumptions-sources.pdf"),
]

output_folder = Path("data/external_pdfs")
output_folder.mkdir(parents=True, exist_ok=True)

for fname, url in pdf_urls:
    resp = requests.get(url)
    if resp.status_code == 200:
        with open(output_folder / fname, "wb") as f:
            f.write(resp.content)
        print(f"Downloaded {fname}")
    else:
        print(f"Failed to download {url}")
