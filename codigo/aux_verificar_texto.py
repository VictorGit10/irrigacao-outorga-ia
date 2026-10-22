"""
Verificador de texto corrompido.

Proposito: a IA pode emitir caracteres CJK (chines/japones/coreanos) ou outros
blocos de script estranhos no meio de texto em portugues. Num documento, isso
aparece como erro na tela e tira a credibilidade. Este script varre os
arquivos de texto do projeto e reporta qualquer ocorrencia.

Uso:  python aux_verificar_texto.py
Saida: 0 se tudo limpo, 1 se houver ocorrencias.
"""
import re, sys, os, glob

AQUI = os.path.dirname(os.path.abspath(__file__))
# Blocos de script que nao aparecem em portugues tecnico.
# CJK (chinês/japonês/coreano), cirilico, hebraico, arabe, devanagari, thai.
PADROES = {
    "CJK (chines/japones/coreano)": r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]",
    "Cirilico":                    r"[\u0400-\u04ff]",
    "Hebraico":                   r"[\u0590-\u05ff]",
    "Arabe":                      r"[\u0600-\u06ff]",
    "Devanagari":                 r"[\u0900-\u097f]",
    "Thai":                       r"[\u0e00-\u0e7f]",
    "Sublinhado em caixa alta (marcador de erro)": r"__[A-Z_]+__",
}

ALVO = ["*.md", "*.py", "*.csv", "*.txt"]

def varrer(raiz):
    achados = []
    arquivos = []
    for pat in ALVO:
        arquivos += glob.glob(os.path.join(raiz, pat))
    for arq in sorted(arquivos):
        try:
            with open(arq, "r", encoding="utf-8") as fh:
                texto = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        for nome, pad in PADROES.items():
            for m in re.finditer(pad, texto):
                linha = texto[:m.start()].count("\n") + 1
                trecho = texto[max(0, m.start()-30):m.end()+30].replace("\n", " ")
                achados.append((os.path.relpath(arq, raiz), linha, nome, trecho))
    return achados

if __name__ == "__main__":
    achados = varrer(AQUI)
    if not achados:
        print("OK: nenhum caractere corrompido encontrado nos arquivos de texto.")
        sys.exit(0)
    print(f"{len(achados)} ocorrencia(s) encontrada(s):\n")
    atual = None
    for arq, linha, nome, trecho in achados:
        if arq != atual:
            print(f"  {arq}"); atual = arq
        print(f"     linha {linha:>5}  [{nome}]  ...{trecho}...")
    print("\nCorrigir antes de usar o material.")
    sys.exit(1)
