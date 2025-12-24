import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orders.utils import PixPayload
import django
from django.conf import settings

# Manual configuration mimicing settings.py
PIX_KEY = '+5581984086846'
PIX_NAME = 'YAS MIMOS'
PIX_CITY = 'RECIFE'

print(f"--- CONFIG ---")
print(f"Key: {PIX_KEY}")
print(f"Name: {PIX_NAME}")
print(f"City: {PIX_CITY}")

pix = PixPayload(key=PIX_KEY, name=PIX_NAME, city=PIX_CITY, amount=10.00, txt_id="***")
payload = pix.generate_payload()

print(f"\n--- PAYLOAD (With Amount 10.00) ---")
print(payload)

pix_fallback = PixPayload(key=PIX_KEY, name=PIX_NAME, city=PIX_CITY, amount=None, txt_id="***")
payload_fallback = pix_fallback.generate_payload()

print(f"\n--- FALLBACK PAYLOAD (No Amount) ---")
print(payload_fallback)
