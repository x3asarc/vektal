import requests
from bs4 import BeautifulSoup
import re

url = "https://www.itdcollection.com/Papier-do-decoupage-papier-ryzowy-R088L"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

print("H1:", soup.find('h1').get_text(strip=True))

ean_elem = soup.select_one('.pinfo-ean span') or soup.select_one('.pinfo-ean')
if ean_elem:
    print("EAN Element Found:", ean_elem.get_text(strip=True))
else:
    print("EAN Element NOT Found")

# Check all pinfo items
pinfo = soup.select('.pinfo-container-item')
for item in pinfo:
    print("PINFO Item:", item.get_text(strip=True))
