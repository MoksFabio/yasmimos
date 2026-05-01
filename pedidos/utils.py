import unicodedata

def normalize_text(text):
    if not text:
        return ""
    # Normalize to ASCII (remove accents) and upper case
    return unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('ASCII').upper()

def calculate_crc16(payload):
    crc = 0xFFFF
    polynomial = 0x1021
    for byte in payload.encode('utf-8'):
        crc ^= (byte << 8)
        for _ in range(8):
            if (crc & 0x8000):
                crc = (crc << 1) ^ polynomial
            else:
                crc = crc << 1
        crc &= 0xFFFF
    return f"{crc:04X}"

def generate_pix_payload(key, name, city, amount=None, txt_id="***", minimal=False):
    """
    Gera o payload "Copia e Cola" do Pix (EMV QRCPS-MPM).
    Ref: Manual de Padrões para Iniciação do Pix (BR Code).
    
    Args:
        minimal (bool): Se True, gera o payload mais simples possível (sem TxID, sem Initiation Method).
    """
    key = normalize_text(key)
    name = normalize_text(name)[0:25]
    city = normalize_text(city)[0:15]
    txt_id = normalize_text(txt_id)[0:25]
    
    if not txt_id:
        txt_id = "***"

    def format_field(id, value):
        return f"{id}{len(value):02}{value}"

    # 00 - Payload Format Indicator (Fixed "01")
    # 26 - Merchant Account Information (GUI + Key)
    # 52 - Merchant Category Code (Fixed "0000" for static)
    # 53 - Transaction Currency (Fixed "986" - BRL)
    # 54 - Transaction Amount (Optional)
    # 58 - Country Code (Fixed "BR")
    # 59 - Merchant Name
    # 60 - Merchant City
    # 62 - Additional Data Field Template (TxID)
    # 63 - CRC16

    # 00 - Payload Format
    p_00 = format_field("00", "01")

    # 26 - Merchant Account Info
    p_26_00 = format_field("00", "br.gov.bcb.pix")
    p_26_01 = format_field("01", key)
    p_26 = format_field("26", p_26_00 + p_26_01)

    # 52 - MCC
    p_52 = format_field("52", "0000")

    # 53 - Currency
    p_53 = format_field("53", "986")

    # 54 - Amount
    p_54 = ""
    if amount is not None:
        p_54 = format_field("54", f"{amount:.2f}")

    # 58 - Country
    p_58 = format_field("58", "BR")

    # 59 - Name
    p_59 = format_field("59", name)

    # 60 - City
    p_60 = format_field("60", city)

    # Assembly Lists
    payload_parts = [p_00]
    
    # 01 - Point of Initiation
    # Only include if not minimal. Some ultra-strict readers prefer without it for static key-only payloads.
    if not minimal:
        p_01 = format_field("01", "11") 
        payload_parts.append(p_01)

    payload_parts.extend([p_26, p_52, p_53])
    
    if p_54:
        payload_parts.append(p_54)

    payload_parts.extend([p_58, p_59, p_60])

    # 62 - Additional Data (TxID)
    # Skip for minimal payload
    if not minimal:
        p_62_05 = format_field("05", txt_id)
        p_62 = format_field("62", p_62_05)
        payload_parts.append(p_62)

    # 63 - CRC16 Placeholder
    payload_parts.append("6304")
    
    raw_payload = "".join(payload_parts)

    crc = calculate_crc16(raw_payload)
    return raw_payload + crc

# Wrapper class for compatibility with existing view calls
class PixPayload:
    def __init__(self, key, name, city, amount=None, txt_id="***"):
        self.key = key
        self.name = name
        self.city = city
        self.amount = amount
        self.txt_id = txt_id

    def generate_payload(self, minimal=False):
        return generate_pix_payload(self.key, self.name, self.city, self.amount, self.txt_id, minimal=minimal)

