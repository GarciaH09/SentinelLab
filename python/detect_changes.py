import json
from datetime import datetime
import re
from pathlib import Path


_HASH_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")

if __package__:
    from .inventory import criar_inventario
else:
    from inventory import criar_inventario


def carregar_inventario(caminho):
    with caminho.open("r", encoding="utf-8") as arquivo:
        inventario = json.load(arquivo)

    if not isinstance(inventario, dict) or not all(
        isinstance(nome, str)
        and bool(nome)
        and isinstance(hash_sha256, str)
        and _HASH_SHA256.fullmatch(hash_sha256)
        for nome, hash_sha256 in inventario.items()
    ):
        raise ValueError(
            "o inventário deve ser um objeto JSON com caminhos e hashes SHA-256 válidos."
        )

    return {nome: hash_sha256.lower() for nome, hash_sha256 in inventario.items()}


def comparar_inventarios(anterior, atual):
    eventos = []
    arquivos_anteriores = set(anterior.keys())
    arquivos_atuais = set(atual.keys())

    novos = arquivos_atuais - arquivos_anteriores
    for nome in sorted(novos):
        eventos.append({"tipo": "NOVO", "arquivo": nome})

    removidos = arquivos_anteriores - arquivos_atuais
    for nome in sorted(removidos):
        eventos.append({"tipo": "REMOVIDO", "arquivo": nome})

    existentes = arquivos_anteriores & arquivos_atuais
    for nome in sorted(existentes):
        if anterior[nome] != atual[nome]:
            eventos.append({"tipo": "MODIFICADO", "arquivo": nome})

    return eventos


def registrar_eventos(eventos, caminho_log):
    if not eventos:
        return

    caminho_log.parent.mkdir(parents=True, exist_ok=True)
    with caminho_log.open("a", encoding="utf-8") as arquivo:
        for evento in eventos:
            registro = {
                **evento,
                "data_hora": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
            arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def main():
    raiz = Path(__file__).resolve().parent.parent
    pasta_lab = raiz / "lab"
    arquivo_inventario = raiz / "data" / "inventario.json"
    caminho_log = raiz / "reports" / "eventos.jsonl"

    if not pasta_lab.is_dir():
        print("Erro: pasta lab não encontrada.")
        return 1

    try:
        inventario_anterior = carregar_inventario(arquivo_inventario)
    except FileNotFoundError:
        print("Erro: inventário não encontrado. Crie a baseline com python python/inventory.py.")
        return 1
    except json.JSONDecodeError as erro:
        print(f"Erro: inventário JSON inválido: {erro}")
        return 1
    except (OSError, ValueError) as erro:
        print(f"Erro ao carregar o inventário: {erro}")
        return 1

    try:
        inventario_atual = criar_inventario(pasta_lab)
    except (OSError, RuntimeError) as erro:
        print(f"Erro ao verificar a integridade: {erro}")
        return 1

    eventos = comparar_inventarios(inventario_anterior, inventario_atual)
    try:
        registrar_eventos(eventos, caminho_log)
    except OSError as erro:
        print(f"Erro ao registrar eventos em {caminho_log}: {erro}")
        return 1

    print("=== SentinelLab: verificação de integridade ===")
    if not eventos:
        print("Nenhuma alteração detectada.")
    else:
        for evento in eventos:
            print(f"[{evento['tipo']}] {evento['arquivo']}")
        print(f"\nTotal de alterações: {len(eventos)}")

    print("\nInventário original preservado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
