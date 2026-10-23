#include <stdio.h>
#include <openssl/evp.h>

int calcular_sha256(const char *caminho)
{
    FILE *arquivo = fopen(caminho, "rb");
    if (arquivo == NULL) {
        perror("Erro ao abrir o arquivo");
        return 1;
    }

    EVP_MD_CTX *contexto = EVP_MD_CTX_new();
    if (contexto == NULL) {
        fprintf(stderr, "Erro ao criar contexto SHA-256.\n");
        fclose(arquivo);
        return 1;
    }

    unsigned char bloco[4096];
    unsigned char hash[EVP_MAX_MD_SIZE];
    unsigned int tamanho_hash = 0;
    int resultado = 1;

    if (EVP_DigestInit_ex(contexto, EVP_sha256(), NULL) != 1) {
        fprintf(stderr, "Erro ao iniciar SHA-256.\n");
        goto limpeza;
    }

    size_t bytes_lidos;
    while ((bytes_lidos = fread(bloco, 1, sizeof(bloco), arquivo)) > 0) {
        if (EVP_DigestUpdate(contexto, bloco, bytes_lidos) != 1) {
            fprintf(stderr, "Erro ao processar o arquivo.\n");
            goto limpeza;
        }
    }

    if (ferror(arquivo)) {
        fprintf(stderr, "Erro ao ler o arquivo.\n");
        goto limpeza;
    }

    if (EVP_DigestFinal_ex(contexto, hash, &tamanho_hash) != 1) {
        fprintf(stderr, "Erro ao finalizar SHA-256.\n");
        goto limpeza;
    }

    printf("Arquivo: %s\n", caminho);
    printf("SHA-256: ");
    for (unsigned int i = 0; i < tamanho_hash; i++) {
        printf("%02x", hash[i]);
    }
    printf("\n");
    resultado = 0;

limpeza:
    EVP_MD_CTX_free(contexto);
    fclose(arquivo);
    return resultado;
}

int main(int argc, char *argv[])
{
    if (argc != 2) {
        fprintf(stderr, "Uso: hashfile.exe <caminho_do_arquivo>\n");
        return 1;
    }

    return calcular_sha256(argv[1]);
}
