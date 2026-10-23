import hashlib
import json
import sys
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import Mock, patch


RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "python"))

import c_hash
import inventory
import menu
import web_app
from hash_file import calcular_hash as calcular_hash_python
from detect_changes import comparar_inventarios, registrar_eventos
from detect_changes import carregar_inventario


class TestHTTPServer(ThreadingHTTPServer):
    daemon_threads = False


class TestIntegridade(unittest.TestCase):
    def test_sem_alteracoes(self):
        anterior = {"config.txt": "abc123", "exemplo.txt": "def456"}
        atual = {"config.txt": "abc123", "exemplo.txt": "def456"}

        self.assertEqual(comparar_inventarios(anterior, atual), [])

    def test_arquivo_novo(self):
        anterior = {"config.txt": "abc123"}
        atual = {"config.txt": "abc123", "novo.txt": "xyz789"}

        self.assertIn(
            {"tipo": "NOVO", "arquivo": "novo.txt"},
            comparar_inventarios(anterior, atual),
        )

    def test_arquivo_removido(self):
        anterior = {"config.txt": "abc123", "exemplo.txt": "def456"}
        atual = {"config.txt": "abc123"}

        self.assertIn(
            {"tipo": "REMOVIDO", "arquivo": "exemplo.txt"},
            comparar_inventarios(anterior, atual),
        )

    def test_arquivo_modificado(self):
        anterior = {"config.txt": "abc123"}
        atual = {"config.txt": "xyz789"}

        self.assertIn(
            {"tipo": "MODIFICADO", "arquivo": "config.txt"},
            comparar_inventarios(anterior, atual),
        )

    def test_inventario_usa_caminhos_relativos_e_hash_c(self):
        with tempfile.TemporaryDirectory() as diretorio:
            pasta = Path(diretorio)
            (pasta / "subpasta").mkdir()
            (pasta / "config.txt").write_text("config", encoding="utf-8")
            (pasta / "subpasta" / "exemplo.txt").write_text("exemplo", encoding="utf-8")

            with patch.object(
                inventory,
                "calcular_hash",
                side_effect=["hash-a", "hash-b"],
            ) as calcular:
                resultado = inventory.criar_inventario(pasta)

        self.assertEqual(
            resultado,
            {"config.txt": "hash-a", "subpasta/exemplo.txt": "hash-b"},
        )
        self.assertEqual(calcular.call_count, 2)

    def test_hash_python_processa_arquivo_em_blocos(self):
        conteudo = bytes(range(256)) * 40
        with tempfile.TemporaryDirectory() as diretorio:
            arquivo = Path(diretorio) / "dados.bin"
            arquivo.write_bytes(conteudo)

            resultado = calcular_hash_python(arquivo)

        self.assertEqual(resultado, hashlib.sha256(conteudo).hexdigest())

    def test_ponte_c_extrai_hash_valido(self):
        hash_esperado = "a" * 64
        executavel_simulado = Path(c_hash.__file__)
        resultado_simulado = Mock(
            returncode=0,
            stdout=f"Arquivo: config.txt\nSHA-256: {hash_esperado}\n",
            stderr="",
        )

        with patch.object(c_hash, "EXECUTAVEL", executavel_simulado):
            with patch.object(
                c_hash.subprocess,
                "run",
                return_value=resultado_simulado,
            ) as executar:
                resultado = c_hash.calcular_hash(Path("config.txt"))

        self.assertEqual(resultado, hash_esperado)
        self.assertEqual(
            executar.call_args.args[0],
            [str(executavel_simulado), "config.txt"],
        )
        self.assertFalse(executar.call_args.kwargs.get("shell", False))
        self.assertEqual(executar.call_args.kwargs["timeout"], 30)

    def test_ponte_c_informa_falha_do_motor(self):
        executavel_simulado = Path(c_hash.__file__)
        resultado_simulado = Mock(returncode=1, stdout="", stderr="falha de leitura")

        with patch.object(c_hash, "EXECUTAVEL", executavel_simulado):
            with patch.object(
                c_hash.subprocess,
                "run",
                return_value=resultado_simulado,
            ):
                with self.assertRaisesRegex(RuntimeError, "falha de leitura"):
                    c_hash.calcular_hash("config.txt")

    def test_ponte_c_rejeita_saida_invalida(self):
        executavel_simulado = Path(c_hash.__file__)
        resultado_simulado = Mock(
            returncode=0,
            stdout=f"SHA-256: {'a' * 65}\n",
            stderr="",
        )

        with patch.object(c_hash, "EXECUTAVEL", executavel_simulado):
            with patch.object(c_hash.subprocess, "run", return_value=resultado_simulado):
                with self.assertRaisesRegex(RuntimeError, "SHA-256 válido"):
                    c_hash.calcular_hash("config.txt")

    def test_ponte_c_reporta_timeout(self):
        executavel_simulado = Path(c_hash.__file__)

        with patch.object(c_hash, "EXECUTAVEL", executavel_simulado):
            with patch.object(
                c_hash.subprocess,
                "run",
                side_effect=c_hash.subprocess.TimeoutExpired("hashfile.exe", 30),
            ):
                with self.assertRaisesRegex(RuntimeError, "30 segundos"):
                    c_hash.calcular_hash("config.txt")

    def test_carregar_inventario_valida_e_normaliza_hashes(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "inventario.json"
            caminho.write_text(json.dumps({"config.txt": "A" * 64}), encoding="utf-8")

            inventario = carregar_inventario(caminho)

        self.assertEqual(inventario, {"config.txt": "a" * 64})

        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "inventario.json"
            caminho.write_text('{"config.txt": "hash-invalido"}', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "hashes SHA-256 válidos"):
                carregar_inventario(caminho)

    def test_salvar_inventario_preserva_baseline_em_falha(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "inventario.json"
            baseline = '{"baseline": "preservada"}\n'
            caminho.write_text(baseline, encoding="utf-8")

            with patch.object(inventory.json, "dump", side_effect=OSError("disco cheio")):
                with self.assertRaisesRegex(OSError, "disco cheio"):
                    inventory.salvar_inventario({"novo.txt": "a" * 64}, caminho)

            self.assertEqual(caminho.read_text(encoding="utf-8"), baseline)
            self.assertEqual(list(Path(diretorio).iterdir()), [caminho])

    def test_eventos_sao_acrescentados_em_jsonl(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho_log = Path(diretorio) / "reports" / "eventos.jsonl"
            caminho_log.parent.mkdir()
            caminho_log.write_text('{"anterior": true}\n', encoding="utf-8")

            registrar_eventos(
                [{"tipo": "MODIFICADO", "arquivo": "configuração.txt"}],
                caminho_log,
            )

            linhas = caminho_log.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(linhas), 2)
        registro = json.loads(linhas[1])
        self.assertEqual(registro["tipo"], "MODIFICADO")
        self.assertEqual(registro["arquivo"], "configuração.txt")
        data_hora = datetime.fromisoformat(registro["data_hora"])
        self.assertIsNotNone(data_hora.utcoffset())

    def test_lista_vazia_nao_cria_arquivo_de_log(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho_log = Path(diretorio) / "reports" / "eventos.jsonl"

            registrar_eventos([], caminho_log)

            self.assertFalse(caminho_log.exists())

    def test_menu_so_atualiza_baseline_apos_confirmacao(self):
        with patch("builtins.input", side_effect=["2", "não", "0"]):
            with patch.object(menu, "executar_comando") as executar:
                self.assertEqual(menu.main(), 0)

        executar.assert_not_called()

    def test_menu_executa_atualizacao_confirmada(self):
        with patch("builtins.input", side_effect=["2", "ATUALIZAR", "0"]):
            with patch.object(menu, "executar_comando", return_value=0) as executar:
                self.assertEqual(menu.main(), 0)

        executar.assert_called_once_with(
            [str(menu.RAIZ / "python" / "inventory.py")]
        )

    def test_interface_web_serve_pagina_e_hash_com_seguranca_local(self):
        servidor = TestHTTPServer(
            ("127.0.0.1", 0),
            web_app.SentinelLabHandler,
        )
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{servidor.server_address[1]}"
        try:
            with urlopen(base_url, timeout=5) as resposta:
                pagina = resposta.read().decode("utf-8")
                csp = resposta.headers["Content-Security-Policy"]
            self.assertIn("Integridade sob controle.", pagina)
            self.assertIn("https://sites.google.com", csp)

            with urlopen(f"{base_url}/health", timeout=5) as resposta:
                self.assertEqual(json.loads(resposta.read()), {"status": "ok"})

            caminho = str(Path("config.txt"))
            corpo = json.dumps({"path": caminho}).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "Origin": base_url,
            }
            with patch.object(web_app, "calcular_hash", return_value="a" * 64):
                requisicao = Request(
                    f"{base_url}/api/hash",
                    data=corpo,
                    headers=headers,
                    method="POST",
                )
                with urlopen(requisicao, timeout=5) as resposta:
                    payload = json.loads(resposta.read().decode("utf-8"))
            self.assertEqual(payload, {"path": "config.txt", "sha256": "a" * 64})

            headers["Origin"] = "http://site-malicioso.example"
            requisicao = Request(
                f"{base_url}/api/hash",
                data=corpo,
                headers=headers,
                method="POST",
            )
            with self.assertRaises(HTTPError) as erro:
                urlopen(requisicao, timeout=5)
            self.assertEqual(erro.exception.code, 403)
            erro.exception.close()
        finally:
            servidor.shutdown()
            servidor.server_close()
            thread.join(timeout=5)

    def test_interface_web_nao_permite_sair_da_pasta_lab(self):
        with self.assertRaisesRegex(ValueError, "permanecer dentro de lab"):
            web_app.obter_arquivo_lab("../README.md")

    def test_modo_publico_bloqueia_baseline_e_nao_grava_logs(self):
        servidor = TestHTTPServer(
            ("127.0.0.1", 0),
            web_app.SentinelLabHandler,
        )
        thread = threading.Thread(target=servidor.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{servidor.server_address[1]}"
        try:
            with patch.object(web_app, "READ_ONLY", True):
                corpo = json.dumps({"confirm": True}).encode("utf-8")
                requisicao = Request(
                    f"{base_url}/api/baseline",
                    data=corpo,
                    headers={
                        "Content-Type": "application/json",
                        "Origin": base_url,
                    },
                    method="POST",
                )
                with self.assertRaises(HTTPError) as erro:
                    urlopen(requisicao, timeout=5)
                self.assertEqual(erro.exception.code, 403)
                erro.exception.close()

                with patch.object(web_app, "ARQUIVO_INVENTARIO", Path("baseline.json")):
                    with patch.object(web_app, "PASTA_LAB", Path("lab")):
                        with patch.object(
                            web_app,
                            "carregar_inventario",
                            return_value={"config.txt": "a" * 64},
                        ):
                            with patch.object(
                                web_app,
                                "criar_inventario",
                                return_value={"config.txt": "b" * 64},
                            ):
                                with patch.object(
                                    web_app,
                                    "registrar_eventos",
                                ) as registrar:
                                    requisicao = Request(
                                        f"{base_url}/api/detect",
                                        data=b"{}",
                                        headers={
                                            "Content-Type": "application/json",
                                            "Origin": base_url,
                                        },
                                        method="POST",
                                    )
                                    with urlopen(requisicao, timeout=5) as resposta:
                                        payload = json.loads(
                                            resposta.read().decode("utf-8")
                                        )
                self.assertEqual(
                    payload["events"],
                    [{"tipo": "MODIFICADO", "arquivo": "config.txt"}],
                )
                registrar.assert_not_called()
        finally:
            servidor.shutdown()
            servidor.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
