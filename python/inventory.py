import json
import os
import tempfile
from pathlib import Path

if __package__:
    from .c_hash import calcular_hash
else:
    from c_hash import calcular_hash


def criar_inventario(pasta):
    inventario = {}
    for caminho in sorted(pasta.rglob("*")):
        if not caminho.is_file():
            continue
        caminho_relativo = caminho.relative_to(pasta).as_posix()
        inventario[caminho_relativo] = calcular_hash(caminho)
    return inventario


def salvar_inventario(inventario, destino):
    destino = Path(destino)
    caminho_temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destino.parent,
            prefix=f".{destino.name}.",
            suffix=".tmp",
            delete=False,
        ) as arquivo:
            caminho_temporario = Path(arquivo.name)
            json.dump(inventario, arquivo, indent=4, ensure_ascii=False)
            arquivo.write("\n")

        os.replace(caminho_temporario, destino)
    finally:
        if caminho_temporario is not None:
            try:
                caminho_temporario.unlink()
            except FileNotFoundError:
                pass


def main():
    raiz = Path(__file__).resolve().parent.parent
    pasta_lab = raiz / "lab"
    pasta_data = raiz / "data"
    arquivo_inventario = pasta_data / "inventario.json"

    if not pasta_lab.is_dir():
        print("Erro: pasta lab não encontrada.")
        return 1

    try:
        pasta_data.mkdir(parents=True, exist_ok=True)
        inventario = criar_inventario(pasta_lab)
        salvar_inventario(inventario, arquivo_inventario)
    except (OSError, RuntimeError) as erro:
        print(f"Erro ao criar o inventário: {erro}")
        return 1

    print(f"Inventário criado: {arquivo_inventario}")
    print(f"Arquivos registrados: {len(inventario)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
