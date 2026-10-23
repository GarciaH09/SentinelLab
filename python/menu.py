import subprocess
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent


def executar_comando(argumentos):
    try:
        resultado = subprocess.run(
            [sys.executable, *argumentos],
            cwd=RAIZ,
            check=False,
        )
    except OSError as erro:
        print(f"Não foi possível iniciar o comando: {erro}")
        return 1

    if resultado.returncode != 0:
        print(f"Comando finalizado com erro (código {resultado.returncode}).")
    return resultado.returncode


def main():
    while True:
        print(
            "\n=== SentinelLab ===\n"
            "1. Calcular SHA-256 com o motor C\n"
            "2. Criar ou atualizar a baseline\n"
            "3. Detectar alterações\n"
            "4. Executar testes\n"
            "0. Sair"
        )

        try:
            opcao = input("Escolha uma opção: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nMenu encerrado.")
            return 0

        if opcao == "0":
            print("SentinelLab encerrado.")
            return 0

        if opcao == "1":
            try:
                caminho = input(
                    "Arquivo para analisar [lab/config.txt]: "
                ).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nOperação cancelada.")
                continue

            caminho = caminho or "lab/config.txt"
            executar_comando(
                [str(RAIZ / "python" / "c_hash.py"), caminho]
            )
        elif opcao == "2":
            print("Atenção: esta operação substitui a baseline atual.")
            try:
                confirmacao = input("Digite ATUALIZAR para confirmar: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAtualização cancelada.")
                continue

            if confirmacao == "ATUALIZAR":
                executar_comando([str(RAIZ / "python" / "inventory.py")])
            else:
                print("Baseline preservada.")
        elif opcao == "3":
            executar_comando([str(RAIZ / "python" / "detect_changes.py")])
        elif opcao == "4":
            executar_comando(
                ["-m", "unittest", "discover", "-s", "tests", "-v"]
            )
        else:
            print("Opção inválida. Escolha 0, 1, 2, 3 ou 4.")


if __name__ == "__main__":
    raise SystemExit(main())
