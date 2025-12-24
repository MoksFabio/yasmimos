import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orders.utils import PixPayload

# Test case using the user's key
key = "81983082595"
pix = PixPayload(key=key, name="YasMimos", city="Recife", amount=1.00, txt_id="TESTE")
payload = pix.generate_payload()

print(f"Key: {key}")
print(f"Payload generated:\n{payload}")

# Alternative with +55 (common issue for phone numbers)
key_formatted = "+55" + key
pix_formatted = PixPayload(key=key_formatted, name="YasMimos", city="Recife", amount=1.00, txt_id="TESTE")
payload_formatted = pix_formatted.generate_payload()

print(f"\nKey Formatted (+55): {key_formatted}")
print(f"Payload generated (+55):\n{payload_formatted}")
