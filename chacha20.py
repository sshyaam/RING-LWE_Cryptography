import struct

class ChaCha20:
    def __init__(self, key, nonce, counter=1):
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes")
        if len(nonce) != 12:
            raise ValueError("Nonce must be 12 bytes")
        self.state = [
            0x61707865,
            0x3320646e,
            0x79622d32,
            0x6b206574,
            *struct.unpack('<8L', key),
            counter,
            *struct.unpack('<3L', nonce)
        ]

    def quarter_round(self, x, a, b, c, d):
        x[a] = (x[a] + x[b]) & 0xffffffff
        x[d] ^= x[a]
        x[d] = ((x[d] << 16) | (x[d] >> 16)) & 0xffffffff
        x[c] = (x[c] + x[d]) & 0xffffffff
        x[b] ^= x[c]
        x[b] = ((x[b] << 12) | (x[b] >> 20)) & 0xffffffff
        x[a] = (x[a] + x[b]) & 0xffffffff
        x[d] ^= x[a]
        x[d] = ((x[d] << 8) | (x[d] >> 24)) & 0xffffffff
        x[c] = (x[c] + x[d]) & 0xffffffff
        x[b] ^= x[c]
        x[b] = ((x[b] << 7) | (x[b] >> 25)) & 0xffffffff

    def chacha_block(self):
        x = self.state.copy()
        for _ in range(10):
            self.quarter_round(x, 0, 4, 8, 12)
            self.quarter_round(x, 1, 5, 9, 13)
            self.quarter_round(x, 2, 6, 10, 14)
            self.quarter_round(x, 3, 7, 11, 15)
            self.quarter_round(x, 0, 5, 10, 15)
            self.quarter_round(x, 1, 6, 11, 12)
            self.quarter_round(x, 2, 7, 8, 13)
            self.quarter_round(x, 3, 4, 9, 14)
        return [(x[i] + self.state[i]) & 0xffffffff for i in range(16)]

    def keystream(self, length):
        stream = b''
        while len(stream) < length:
            block = self.chacha_block()
            self.state[12] = (self.state[12] + 1) & 0xffffffff
            for word in block:
                stream += struct.pack('<L', word)
        return stream[:length]

    def encrypt(self, plaintext):
        return bytes([p ^ k for p, k in zip(plaintext, self.keystream(len(plaintext)))])

    def decrypt(self, ciphertext):
        return bytes([p ^ k for p, k in zip(ciphertext, self.keystream(len(ciphertext)))])
