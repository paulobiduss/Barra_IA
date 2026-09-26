"""
Testes do TLS das chamadas de uso (core/providers/base.py).

Regressao da v1.1.1: no .app empacotado o Python nao achava os certificados
da maquina de build e toda chamada virava "sem conexao". O contexto agora usa
o bundle do certifi. Nenhuma chamada de rede real e feita.
"""

import io
import json
import ssl
import unittest
import urllib.error
from unittest import mock

import certifi

from core.models import UsageState
from core.providers import base


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeUrlopen:
    """Substitui urllib.request.urlopen registrando o contexto TLS recebido."""

    def __init__(self, *, payload: dict | None = None, error: Exception | None = None):
        self.contexts: list[ssl.SSLContext | None] = []
        self._payload = payload or {}
        self._error = error

    def __call__(self, request, timeout=None, context=None):
        self.contexts.append(context)
        if self._error is not None:
            raise self._error
        return _FakeResponse(json.dumps(self._payload).encode("utf-8"))


class DefaultSslContextTests(unittest.TestCase):
    def test_loads_certifi_bundle(self):
        # Sem cafile explicito, o contexto padrao pode vir vazio no app empacotado.
        context = base.default_ssl_context()
        self.assertGreater(len(context.get_ca_certs()), 0)
        self.assertTrue(certifi.where().endswith("cacert.pem"))

    def test_keeps_verification_strict(self):
        context = base.default_ssl_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)


class HttpGetJsonTlsTests(unittest.TestCase):
    def test_uses_certifi_context_by_default(self):
        fake = _FakeUrlopen(payload={"ok": True})
        with mock.patch.object(base.urllib.request, "urlopen", fake):
            data, error = base.http_get_json("https://example.invalid/usage", "tok")
        self.assertEqual((data, error), ({"ok": True}, None))
        self.assertIsInstance(fake.contexts[0], ssl.SSLContext)
        self.assertGreater(len(fake.contexts[0].get_ca_certs()), 0)

    def test_certificate_failure_is_network_error(self):
        cert_error = ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED")
        fake = _FakeUrlopen(error=urllib.error.URLError(cert_error))
        with mock.patch.object(base.urllib.request, "urlopen", fake):
            with self.assertLogs("barra_uso_ia.providers", level="WARNING") as logs:
                data, error = base.http_get_json("https://example.invalid/usage", "tok")
        self.assertEqual((data, error), (None, UsageState.NETWORK_ERROR))
        self.assertIn("SSLCertVerificationError", logs.output[0])
        self.assertNotIn("tok", logs.output[0])


if __name__ == "__main__":
    unittest.main()
