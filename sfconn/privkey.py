"Private key"

import os
from functools import cached_property
from pathlib import Path

import cryptography.hazmat.primitives.serialization as Serde
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey


class PrivateKey:
    "class to extract various pieces of information from private-key file"

    def __init__(
        self,
        private_key_file: Path,
        pass_phrase: str | None = None,
        pass_phrase_var: str | None = "SNOWSQL_PRIVATE_KEY_PASSPHRASE",
    ):
        if not private_key_file.is_file():
            raise FileNotFoundError(f"Invalid private Key file '{private_key_file}'")

        self.private_key_file = private_key_file
        self.pass_phrase = os.environ.get(pass_phrase_var) if pass_phrase is None and pass_phrase_var is not None else pass_phrase

    @cached_property
    def key(self) -> RSAPrivateKey:
        with self.private_key_file.open("rb") as fh:
            return Serde.load_pem_private_key(  # type: ignore
                fh.read(), password=self.pass_phrase.encode() if self.pass_phrase is not None else None, backend=default_backend()
            )

    @property
    def pri_bytes(self) -> bytes:
        return self.key.private_bytes(
            encoding=Serde.Encoding.DER, format=Serde.PrivateFormat.PKCS8, encryption_algorithm=Serde.NoEncryption()
        )

    @property
    def pub_bytes(self) -> bytes:
        return self.key.public_key().public_bytes(Serde.Encoding.DER, Serde.PublicFormat.SubjectPublicKeyInfo)
