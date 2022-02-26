import unittest
from src.eques_elf import eques_local


class TestCryptographyMethods(unittest.TestCase):
    """
    Tests the cryptography methods, using test cases from outputs of the
    original implementation.

    See: https://github.com/iamckn/eques/blob/master/exploit/equeslocal.go
    """

    PLAINTEXT = "lan_phone%mac%nopassword%2022-01-29-22:09:31%heart"
    CIPHERTEXT_HEX = bytes.fromhex(
        "671b8cf3f49c5491825235b44936543f3bf0ab71fb34830e73acbe0934edb34887deb88cb4b28c83ec00ed9cc329c98d001936a1237339ce3dcf36dfb138f9f8"
    )

    def test_encrypt(self):
        ciphertext = eques_local.encrypt(self.PLAINTEXT)
        self.assertEqual(ciphertext.hex(), self.CIPHERTEXT_HEX.hex())

    def test_decrypt(self):
        plaintext = eques_local.decrypt(self.CIPHERTEXT_HEX)
        self.assertEqual(plaintext, self.PLAINTEXT)
