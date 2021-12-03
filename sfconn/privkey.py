"Private key"
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cached_property, cache
from os.path import expanduser
from pathlib import Path
from typing import Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import (
	Encoding, NoEncryption, PrivateFormat, PublicFormat, load_pem_private_key
)


@dataclass(frozen=True)
class PrivateKey:
	"class to extract various pieces of information from private-key file"
	private_key_file: Path
	pass_phrase: Optional[str]

	@cached_property
	def key(self) -> RSAPrivateKey:
		with self.private_key_file.open("rb") as fh:
			return load_pem_private_key(  # type: ignore
				fh.read(),
				password=self.pass_phrase.encode() if self.pass_phrase is not None else None,
				backend=default_backend()
			)

	@property
	def pri_bytes(self) -> bytes:
		return self.key.private_bytes(
			encoding=Encoding.DER,
			format=PrivateFormat.PKCS8,
			encryption_algorithm=NoEncryption()
		)

	@property
	def pub_bytes(self) -> bytes:
		return self.key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)

	@staticmethod
	@cache
	def from_file(
		filepath: str,
		pass_phrase: Optional[str] = None,
		pass_phrase_var: Optional[str] = "SNOWSQL_PRIVATE_KEY_PASSPHRASE"
	) -> PrivateKey:
		"return PrivateKey instance from the file and pass phrase or pass-phrase variable (defaults to SNOWSQL_PRIVATE_KEY_PASSPHRASE)"
		if not (fp := Path(expanduser(filepath))).exists():
			raise FileNotFoundError(f"Private Key file '{filepath}' does not exist")

		if pass_phrase is None and pass_phrase_var is not None:
			pass_phrase = os.environ.get(pass_phrase_var)

		return PrivateKey(fp, pass_phrase)
