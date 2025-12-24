
def calculate_crc16(payload_str):
    crc = 0xFFFF
    polynomial = 0x1021
    for byte in payload_str.encode('utf-8'):
        crc ^= (byte << 8)
        for _ in range(8):
            if (crc & 0x8000):
                crc = (crc << 1) ^ polynomial
            else:
                crc = crc << 1
        crc &= 0xFFFF
    return f"{crc:04X}"

vector = "123456789"
result = calculate_crc16(vector)
print(f"Input: {vector}")
print(f"Result: {result}")
print(f"Expected: 29B1")
print(f"Match: {result == '29B1'}")
