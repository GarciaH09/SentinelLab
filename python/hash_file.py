import hashlib
from pathlib import Path


def calcular_hash(caminho):
    sha256 = hashlib.sha256()
    with Path(caminho).open("rb") as arquivo:
        while True:
            bloco = arquivo.read(4096)
            if not bloco:
                break
            sha256.update(bloco)
    return sha256.hexdigest()


def main():
    caminho = Path(__file__).resolve().parent.parent / "lab" / "config.txt"
    if not caminho.is_file():
        print("Arquivo não encontrado:", caminho)
        return 1

    try:
        resultado = calcular_hash(caminho)
    except OSError as erro:
        print(f"Erro ao ler o arquivo {caminho}: {erro}")
        return 1

    print("Arquivo:", caminho.name)
    print("SHA-256:", resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
