class PixPayload:
    def __init__(self, key, name, city, amount, order_id):
        self.key = key
        self.name = name
        self.city = city
        self.amount = "{:.2f}".format(float(amount))
        self.order_id = str(order_id)

    def _f(self, id, value):
        # Calculate length in BYTES, not characters (crucial for UTF-8)
        val_bytes = value.encode('utf-8')
        return f"{id}{len(val_bytes):02}{value}"

    def get_payload(self):
        # 00: Payload Format Indicator
        pfi = "000201"

        # 01: Point of Initiation Method (11: Static, 12: Dynamic)
        # We use 11 (Static) because we are not providing a callback URL (Field 25).
        # This makes it compatible with simple Manual Pix Keys.
        pom = "010211"

        # 26: Merchant Account Information
        gui = self._f("00", "br.gov.bcb.pix")
        key = self._f("01", self.key)
        mai = self._f("26", gui + key)

        # 52: Merchant Category Code
        # "0000" is general/undefined. MUST BE 4 DIGITS.
        mcc = "0000"

        # 53: Transaction Currency (986 = BRL)
        curr = "5303986"

        # 54: Transaction Amount
        amt = self._f("54", self.amount)

        # 58: Country Code
        cc = "5802BR"

        # 59: Merchant Name (MAX 25 characters)
        # Simplify to ensure acceptance, but match likely bank registration
        short_name = "YASMIM P F NASCIMENTO" 
        nm = self._f("59", short_name)

        # 60: Merchant City (MAX 15 characters)
        short_city = self.city.replace('é', 'e').replace('í', 'i')
        if len(short_city) > 15:
            short_city = short_city[:15].strip()
        ct = self._f("60", short_city.upper())

        # 62: Additional Data Field Template
        # Standard for Static Pix is '***'
        txid = self._f("05", "***") 
        adft = self._f("62", txid)

        payload = f"{pfi}{pom}{mai}{mcc}{curr}{amt}{cc}{nm}{ct}{adft}6304"
        
        # CRC16
        crc = self._crc16(payload)
        
        return f"{payload}{crc}"

    def _crc16(self, data):
        data = data.encode('utf-8')
        crc = 0xFFFF
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if (crc & 0x8000):
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = (crc << 1)
                crc &= 0xFFFF
        return hex(crc).upper()[2:].zfill(4)
