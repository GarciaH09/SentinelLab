import re
import subprocess
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
NOME_EXECUTAVEL = "hashfile.exe" if sys.platform == "win32" else "hashfile"
EXECUTAVEL = RAIZ / "c_engine" / NOME_EXECUTAVEL


def calcular_hash(caminho):
    if not EXECUTAVEL.is_file():
        raise FileNotFoundError(
            f"Executável não encontrado: {EXECUTAVEL}\n"
            "Compile o programa C antes de continuar."
        )

    try:
        resultado = subprocess.run(
            [str(EXECUTAVEL), str(caminho)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired as erro:
        raise RuntimeError("O motor C excedeu o limite de 30 segundos.") from erro

    if resultado.returncode != 0:
        mensagem = resultado.stderr.strip() or resultado.stdout.strip()
        raise RuntimeError(mensagem or "O programa C falhou ao calcular o hash.")

    correspondencia = re.search(
        r"^SHA-256:\s*([0-9a-fA-F]{64})\s*$",
        resultado.stdout,
        re.MULTILINE,
    )
    if correspondencia is None:
        raise RuntimeError("O programa C não retornou um SHA-256 válido.")

    return correspondencia.group(1).lower()


def main():
    if len(sys.argv) > 2:
        print(f"Uso: python {Path(__file__).name} [caminho_do_arquivo]", file=sys.stderr)
        return 1

    caminho = (
        Path(sys.argv[1])
        if len(sys.argv) == 2
        else RAIZ / "lab" / "config.txt"
    )

    try:
        resultado = calcular_hash(caminho)
    except (FileNotFoundError, RuntimeError, OSError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    print("Arquivo:", caminho)
    print("SHA-256:", resultado)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
