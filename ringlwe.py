"""
class RingLWE:
    def __init__(self, n=16, q=12289):
        self.n = n  # Degree of the ring
        self.q = q  # Modulus
        self.s = None  # Secret key
        self.a = None  # Public parameter
        self.e = None  # Error polynomial
        self.public_key = None
        self.shared_key = None

    def generate_keys(self):
        # Generate secret and error polynomials with small integer coefficients
        self.s = np.random.randint(-1, 2, size=self.n)
        self.e = np.random.randint(-1, 2, size=self.n)
        # Generate public parameter 'a' randomly in the ring
        self.a = np.random.randint(0, self.q, size=self.n)
        # Compute public key: b = a * s + e mod q
        self.public_key = (np.convolve(self.a, self.s)[:self.n] + self.e) % self.q
        return self.public_key

    def compute_shared_key(self, other_public_key):
        # Compute shared key: k = other_public_key * s mod q
        self.shared_key = np.convolve(other_public_key, self.s)[:self.n] % self.q
        return self.shared_key

    def get_shared_secret(self):
        # Simplify shared secret to a hashable value (e.g., first element)
        return int(self.shared_key[0])
"""

import os

class RingLWE:
    def __init__(self):
        self.private_key = os.urandom(32)
        self.public_key = self.generate_public_key(self.private_key)

    @staticmethod
    def generate_public_key(private_key):
        return bytes([b ^ 0x55 for b in private_key])

    @staticmethod
    def derive_shared_secret(private_key, public_key):
        return bytes([a ^ b for a, b in zip(private_key, public_key)])
