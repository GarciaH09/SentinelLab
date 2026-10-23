import json
import io
import os
import sys
import unittest
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

if __package__:
    from .c_hash import calcular_hash
    from .detect_changes import (
        carregar_inventario,
        comparar_inventarios,
        registrar_eventos,
    )
    from .inventory import criar_inventario, salvar_inventario
else:
    from c_hash import calcular_hash
    from detect_changes import carregar_inventario, comparar_inventarios, registrar_eventos
    from inventory import criar_inventario, salvar_inventario


RAIZ = Path(__file__).resolve().parent.parent
PASTA_LAB = RAIZ / "lab"
ARQUIVO_INVENTARIO = RAIZ / "data" / "inventario.json"
ARQUIVO_LOG = RAIZ / "reports" / "eventos.jsonl"
HOST = "127.0.0.1"
PORTA = 8765
MAX_REQUEST_BYTES = 4096
READ_ONLY = os.environ.get("SENTINELLAB_READ_ONLY", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0b1220">
  <title>SentinelLab | Integridade de arquivos</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #080d18;
      --panel: #101827;
      --panel-2: #141f31;
      --line: #233149;
      --text: #e7edf7;
      --muted: #95a3b8;
      --accent: #47e0ad;
      --accent-dark: #102b29;
      --blue: #82aaff;
      --red: #ff7d87;
      --yellow: #ffd479;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(ellipse at 15% 0%, #15243a 0, var(--bg) 48%);
      color: var(--text);
      font: 15px/1.55 "Segoe UI", system-ui, sans-serif;
    }
    button, input { font: inherit; }
    .shell { width: min(1100px, calc(100% - 36px)); margin: 0 auto; padding: 38px 0 56px; }
    header { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 30px; }
    .brand { display: flex; align-items: center; gap: 14px; }
    .mark {
      width: 44px; height: 44px; display: grid; place-items: center;
      border: 1px solid #286554; border-radius: 13px;
      color: var(--accent); background: #0c2827; font-size: 21px; font-weight: 800;
    }
    h1 { margin: 0; font-size: 21px; letter-spacing: -.02em; }
    .subtitle, .muted { color: var(--muted); }
    .subtitle { margin: 3px 0 0; font-size: 13px; }
    .local-badge {
      border: 1px solid var(--line); border-radius: 999px; padding: 7px 11px;
      color: var(--muted); font-size: 12px; white-space: nowrap;
    }
    .local-badge span { color: var(--accent); padding-right: 5px; }
    .hero { margin-bottom: 22px; }
    .eyebrow { color: var(--accent); text-transform: uppercase; letter-spacing: .14em; font-size: 11px; font-weight: 700; }
    h2 { font-size: clamp(26px, 4vw, 38px); line-height: 1.15; letter-spacing: -.04em; margin: 8px 0; }
    .hero p { max-width: 660px; margin: 0; color: var(--muted); }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
    .card { background: linear-gradient(145deg, #121c2b, #0e1725); border: 1px solid var(--line); border-radius: 16px; padding: 21px; }
    .card h3 { margin: 0 0 5px; font-size: 16px; }
    .card p { color: var(--muted); font-size: 13px; margin: 0 0 17px; }
    .wide { grid-column: 1 / -1; }
    .row { display: flex; gap: 9px; align-items: center; }
    input {
      min-width: 0; flex: 1; color: var(--text); background: #09111e;
      border: 1px solid var(--line); border-radius: 9px; padding: 10px 12px; outline: none;
    }
    input:focus { border-color: #3e927e; box-shadow: 0 0 0 3px #47e0ad1c; }
    button {
      border: 1px solid #29715e; border-radius: 9px; padding: 10px 13px;
      background: #12352f; color: #b4ffe2; font-weight: 650; cursor: pointer;
      transition: background .15s ease, transform .15s ease;
    }
    button:hover { background: #19473e; transform: translateY(-1px); }
    button:disabled { opacity: .55; cursor: wait; transform: none; }
    button.secondary { background: #172338; border-color: #30435e; color: #d1def2; }
    button.warning { background: #35291b; border-color: #70522b; color: var(--yellow); }
    .result {
      margin-top: 13px; border-radius: 9px; padding: 12px; background: #09111e;
      border: 1px solid var(--line); min-height: 44px; color: var(--muted); overflow-wrap: anywhere;
    }
    .result.success { color: var(--accent); border-color: #285e53; }
    .result.error { color: var(--red); border-color: #713844; }
    code { color: #b8c9e5; font-family: Consolas, "SFMono-Regular", monospace; font-size: 12px; }
    .actions { display: flex; flex-wrap: wrap; gap: 9px; }
    .status-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .status-pill { color: var(--muted); background: #182438; border-radius: 999px; padding: 5px 10px; font-size: 12px; }
    .status-pill.ready { color: var(--accent); background: var(--accent-dark); }
    .events { margin: 12px 0 0; padding: 0; list-style: none; }
    .events li { display: flex; justify-content: space-between; gap: 12px; padding: 10px 0; border-top: 1px solid #1e2a3d; }
    .event-name { overflow-wrap: anywhere; }
    .event-type { font-size: 11px; font-weight: 750; letter-spacing: .06em; }
    .NOVO { color: var(--accent); } .MODIFICADO { color: var(--yellow); } .REMOVIDO { color: var(--red); }
    .empty { padding: 11px 0 0; color: var(--muted); font-size: 13px; }
    .notice { margin-top: 18px; padding: 12px 14px; border: 1px solid #69522c; border-radius: 11px; background: #211b12; color: #d8c69f; font-size: 12px; }
    footer { color: #6f7d92; font-size: 12px; text-align: center; margin-top: 24px; }
    @media (max-width: 700px) {
      .shell { width: min(100% - 24px, 560px); padding-top: 24px; }
      header { align-items: flex-start; }
      .local-badge { font-size: 0; }
      .local-badge span { font-size: 12px; }
      .grid { grid-template-columns: 1fr; }
      .wide { grid-column: auto; }
      .row { align-items: stretch; flex-direction: column; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div class="brand">
        <div class="mark" aria-hidden="true">S</div>
        <div><h1>SentinelLab</h1><p class="subtitle">Monitoramento de integridade de arquivos</p></div>
      </div>
      <div class="local-badge"><span>●</span> Serviço local</div>
    </header>
    <section class="hero">
      <div class="eyebrow">Blue Team · File Integrity Monitoring</div>
      <h2>Integridade sob controle.</h2>
      <p>Calcule hashes SHA-256, compare os arquivos de laboratório com a baseline e consulte os eventos registrados.</p>
    </section>
    <section class="grid" aria-label="Ações do SentinelLab">
      <article class="card">
        <h3>Calcular SHA-256</h3>
        <p>Use o motor C/OpenSSL em um arquivo dentro de <code>lab/</code>.</p>
        <form id="hash-form">
          <div class="row">
            <input id="hash-path" name="path" value="config.txt" aria-label="Caminho relativo do arquivo em lab">
            <button type="submit">Calcular hash</button>
          </div>
        </form>
        <div id="hash-result" class="result" aria-live="polite">Informe um caminho relativo a <code>lab/</code>.</div>
      </article>
      <article class="card">
        <h3>Baseline</h3>
        <p>Crie ou atualize a referência de confiança com o estado atual de <code>lab/</code>.</p>
        <div class="actions"><button id="baseline-button" class="warning">Atualizar baseline</button></div>
        <div id="baseline-result" class="result" aria-live="polite">A baseline não é alterada pela detecção.</div>
      </article>
      <article class="card">
        <h3>Verificação de integridade</h3>
        <p>Detecte arquivos novos, modificados ou removidos. Os eventos são acrescentados ao histórico JSONL.</p>
        <div class="actions"><button id="detect-button">Verificar agora</button><button id="refresh-button" class="secondary">Atualizar painel</button></div>
        <div id="detect-result" class="result" aria-live="polite">Pronto para verificar os arquivos.</div>
      </article>
      <article class="card">
        <h3>Testes automatizados</h3>
        <p>Execute a suíte do projeto sem sair da interface.</p>
        <div class="actions"><button id="tests-button" class="secondary">Executar testes</button></div>
        <div id="tests-result" class="result" aria-live="polite">A suíte testa comparação, logs e integração.</div>
      </article>
      <article class="card wide">
        <div class="status-head"><h3>Estado do laboratório</h3><span id="baseline-status" class="status-pill">Carregando…</span></div>
        <p id="status-summary">Consultando baseline e histórico de eventos.</p>
        <ul id="events" class="events"></ul>
      </article>
    </section>
    <div class="notice"><strong>Importante:</strong> atualizar a baseline substitui a referência existente. A interface exige confirmação. O serviço escuta apenas neste computador.</div>
    <footer>SentinelLab · Ferramenta educacional de monitoramento defensivo</footer>
  </main>
  <script>
    const $ = (selector) => document.querySelector(selector);
    const setResult = (selector, message, kind = "") => {
      const element = $(selector);
      element.className = `result ${kind}`;
      element.textContent = message;
    };
    async function api(path, body) {
      const options = { headers: { "Accept": "application/json" } };
      if (body !== undefined) {
        options.method = "POST";
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
      }
      const response = await fetch(path, options);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `Erro HTTP ${response.status}`);
      return data;
    }
    function withBusy(button, action) {
      return async (...args) => {
        if (!button) return action(...args);
        button.disabled = true;
        try { await action(...args); }
        catch (error) { return error; }
        finally { button.disabled = false; }
      };
    }
    async function refreshStatus() {
      const status = await api("/api/status");
      const pill = $("#baseline-status");
      $("#baseline-button").disabled = status.read_only;
      $("#baseline-result").textContent = status.read_only
        ? "Modo público somente leitura: baseline protegida."
        : "A baseline não é alterada pela detecção.";
      $("#tests-button").disabled = status.read_only;
      $("#tests-result").textContent = status.read_only
        ? "Testes disponíveis apenas no modo local."
        : "A suíte testa comparação, logs e integração.";
      pill.textContent = status.baseline_exists ? "Baseline ativa" : "Baseline ausente";
      pill.className = `status-pill ${status.baseline_exists ? "ready" : ""}`;
      $("#status-summary").textContent =
        `${status.file_count} arquivo(s) registrados · Log: ${status.event_count} evento(s)`;
      const list = $("#events");
      list.replaceChildren();
      if (!status.recent_events.length) {
        const empty = document.createElement("li");
        empty.className = "empty";
        empty.textContent = "Nenhum evento no histórico.";
        list.append(empty);
        return;
      }
      for (const event of status.recent_events) {
        const item = document.createElement("li");
        const label = document.createElement("span");
        label.className = "event-name";
        const type = document.createElement("strong");
        type.className = `event-type ${event.tipo}`;
        type.textContent = `[${event.tipo}] `;
        label.append(type, document.createTextNode(event.arquivo));
        const time = document.createElement("code");
        time.textContent = event.data_hora;
        item.append(label, time);
        list.append(item);
      }
    }
    $("#hash-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const result = await withBusy(event.submitter, async () => {
        setResult("#hash-result", "Calculando hash…");
        try {
          const data = await api("/api/hash", { path: $("#hash-path").value });
          setResult("#hash-result", `${data.path}\nSHA-256: ${data.sha256}`, "success");
        } catch (error) { setResult("#hash-result", error.message, "error"); }
      })();
      if (result instanceof Error) setResult("#hash-result", result.message, "error");
    });
    $("#baseline-button").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      if (!window.confirm("Atualizar a baseline? A referência atual será substituída.")) return;
      button.disabled = true;
      setResult("#baseline-result", "Criando baseline…");
      try {
        const data = await api("/api/baseline", { confirm: true });
        setResult("#baseline-result", `Baseline atualizada. ${data.file_count} arquivo(s) registrados.`, "success");
        await refreshStatus();
      } catch (error) { setResult("#baseline-result", error.message, "error"); }
      finally { button.disabled = false; }
    });
    $("#detect-button").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      setResult("#detect-result", "Verificando arquivos…");
      try {
        const data = await api("/api/detect", {});
        const message = data.events.length
          ? data.events.map((item) => `[${item.tipo}] ${item.arquivo}`).join("\n") +
            `\n\nTotal de alterações: ${data.events.length}`
          : "Nenhuma alteração detectada.";
        setResult("#detect-result", `${message}\n\nBaseline preservada.`, data.events.length ? "" : "success");
        await refreshStatus();
      } catch (error) { setResult("#detect-result", error.message, "error"); }
      finally { button.disabled = false; }
    });
    $("#tests-button").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      setResult("#tests-result", "Executando testes…");
      try {
        const data = await api("/api/tests", {});
        setResult("#tests-result", data.output || "Testes concluídos.", data.success ? "success" : "error");
      } catch (error) { setResult("#tests-result", error.message, "error"); }
      finally { button.disabled = false; }
    });
    $("#refresh-button").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      try { await refreshStatus(); }
      catch (error) { $("#status-summary").textContent = error.message; }
      finally { button.disabled = false; }
    });
    refreshStatus().catch((error) => {
      $("#baseline-status").textContent = "Erro";
      $("#status-summary").textContent = error.message;
    });
  </script>
</body>
</html>
"""


def obter_arquivo_lab(caminho):
    if not isinstance(caminho, str) or not caminho.strip():
        raise ValueError("Informe um caminho relativo a lab/.")

    arquivo = (PASTA_LAB / caminho).resolve()
    try:
        arquivo.relative_to(PASTA_LAB.resolve())
    except ValueError as erro:
        raise ValueError("O caminho deve permanecer dentro de lab/.") from erro

    if not arquivo.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado em lab/: {caminho}")
    return arquivo


def obter_status():
    baseline_exists = ARQUIVO_INVENTARIO.is_file()
    file_count = 0
    if baseline_exists:
        file_count = len(carregar_inventario(ARQUIVO_INVENTARIO))

    recent_events = []
    event_count = 0
    if ARQUIVO_LOG.is_file():
        with ARQUIVO_LOG.open("r", encoding="utf-8") as arquivo:
            for linha in arquivo:
                if not linha.strip():
                    continue
                evento = json.loads(linha)
                event_count += 1
                recent_events.append(evento)
        recent_events = recent_events[-10:]

    return {
        "read_only": READ_ONLY,
        "baseline_exists": baseline_exists,
        "file_count": file_count,
        "event_count": event_count,
        "recent_events": recent_events,
    }


class SentinelLabHandler(BaseHTTPRequestHandler):
    server_version = "SentinelLab"
    sys_version = ""

    def log_message(self, format_string, *args):
        print(f"[SentinelLab] {self.address_string()} {format_string % args}")

    def _send_json(self, status, body):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self):
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            raise ValueError("Corpo JSON obrigatório.")
        try:
            tamanho = int(content_length)
        except ValueError as erro:
            raise ValueError("Content-Length inválido.") from erro
        if tamanho < 0 or tamanho > MAX_REQUEST_BYTES:
            raise ValueError("Requisição excede o tamanho permitido.")

        try:
            return json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as erro:
            raise ValueError("Corpo JSON inválido.") from erro

    def _validar_origem(self):
        origem = self.headers.get("Origin")
        if not origem:
            return

        parsed = urlparse(origem)
        host = self.headers.get("Host", "")
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.netloc.lower() != host.lower()
        ):
            raise PermissionError("Origem da requisição não permitida.")

    def do_GET(self):
        caminho = urlparse(self.path).path
        if caminho == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if caminho == "/":
            conteudo = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(conteudo)))
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self' 'unsafe-inline'; connect-src 'self'; "
                "base-uri 'none'; frame-ancestors 'self' "
                "https://sites.google.com https://*.googleusercontent.com",
            )
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(conteudo)
            return

        if caminho == "/api/status":
            try:
                self._send_json(200, obter_status())
            except (OSError, ValueError, json.JSONDecodeError) as erro:
                self._send_json(500, {"error": f"Não foi possível ler o estado: {erro}"})
            return

        self._send_json(404, {"error": "Rota não encontrada."})

    def do_POST(self):
        try:
            self._validar_origem()
            corpo = self._read_json()
            if not isinstance(corpo, dict):
                raise ValueError("O corpo deve ser um objeto JSON.")

            caminho = urlparse(self.path).path
            if caminho == "/api/hash":
                arquivo = obter_arquivo_lab(corpo.get("path"))
                resultado = calcular_hash(arquivo)
                relativo = arquivo.relative_to(PASTA_LAB.resolve()).as_posix()
                self._send_json(200, {"path": relativo, "sha256": resultado})
                return

            if caminho == "/api/baseline":
                if READ_ONLY:
                    raise PermissionError(
                        "A baseline está protegida no modo público somente leitura."
                    )
                if corpo.get("confirm") is not True:
                    raise ValueError("Confirmação obrigatória para atualizar a baseline.")
                inventario = criar_inventario(PASTA_LAB)
                ARQUIVO_INVENTARIO.parent.mkdir(parents=True, exist_ok=True)
                salvar_inventario(inventario, ARQUIVO_INVENTARIO)
                self._send_json(200, {"file_count": len(inventario)})
                return

            if caminho == "/api/detect":
                anterior = carregar_inventario(ARQUIVO_INVENTARIO)
                atual = criar_inventario(PASTA_LAB)
                eventos = comparar_inventarios(anterior, atual)
                if not READ_ONLY:
                    registrar_eventos(eventos, ARQUIVO_LOG)
                self._send_json(200, {"events": eventos})
                return

            if caminho == "/api/tests":
                if READ_ONLY:
                    raise PermissionError(
                        "Os testes estão disponíveis apenas no modo local."
                    )
                suite = unittest.defaultTestLoader.discover(
                    str(RAIZ / "tests"),
                    pattern="test*.py",
                )
                stream = io.StringIO()
                resultado = unittest.TextTestRunner(
                    stream=stream,
                    verbosity=2,
                ).run(suite)
                self._send_json(
                    200,
                    {
                        "success": resultado.wasSuccessful(),
                        "output": stream.getvalue(),
                    },
                )
                return

            self._send_json(404, {"error": "Rota não encontrada."})
        except PermissionError as erro:
            self._send_json(403, {"error": str(erro)})
        except FileNotFoundError as erro:
            self._send_json(404, {"error": str(erro)})
        except (ValueError, json.JSONDecodeError) as erro:
            self._send_json(400, {"error": str(erro)})
        except (OSError, RuntimeError) as erro:
            self._send_json(500, {"error": str(erro)})


def main():
    host = os.environ.get("HOST", HOST)
    try:
        porta = int(os.environ.get("PORT", str(PORTA)))
    except ValueError:
        print("A variável PORT deve conter um número de porta válido.", file=sys.stderr)
        return 1

    try:
        servidor = ThreadingHTTPServer((host, porta), SentinelLabHandler)
    except OSError as erro:
        print(f"Não foi possível iniciar a interface web: {erro}", file=sys.stderr)
        return 1

    endereco_navegador = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{endereco_navegador}:{porta}/"
    print(f"SentinelLab disponível em {url}")
    print("Pressione Ctrl+C neste terminal para encerrar o servidor.")
    try:
        if host in {"127.0.0.1", "localhost"}:
            webbrowser.open(url)
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor SentinelLab encerrado.")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
