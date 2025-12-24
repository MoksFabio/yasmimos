
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

# Exemplo de String Pix Válida (sem o CRC no final)
# Fonte: Exemplos de implementações open-source
# Chave: 12345678900
# Valor: 10.00
# Name: Fulano
# City: Cidade
# TxId: ***
test_payload = "00020126330014br.gov.bcb.pix011112345678900520400005303986540510.005802BR5906Fulano6006Cidade62070503***6304"
expected_crc = "1D3D" # Exemplo hipotético, vamos ver o que sai

# Vamos testar o algoritmo
calculated = calculate_crc16(test_payload)
print(f"Payload: {test_payload}")
print(f"Calculated CRC: {calculated}")

# Validando se o código atual corresponde a implementações online de CRC16 CCITT-FALSE
