#!/usr/bin/env python3
"""
Contador de linhas de código (Python) que ignora:
- linhas de comentário (começando com '#')
- docstrings de módulo/função/classe
- linhas completamente vazias

Conceitos usados: módulo `os`, leitura de arquivos, condicionais, contadores, `tokenize`, `ast`.

Uso:
    python loc_counter.py <caminho>    # caminho é arquivo .py ou diretório

Opções:
    --json    : saída em JSON

"""
import os
import sys
import argparse
import tokenize
import io
import ast
import json
from typing import Set, Tuple, List

# Observações rápidas sobre dependências:
# - `os`/`sys` para manipular caminhos e argumentos.
# - `tokenize` para detectar comentários linha a linha.
# - `ast` para identificar docstrings (strings que aparecem como primeiro nó do corpo).
# - `json` para saída estruturada quando solicitado.


def find_py_files(path: str) -> List[str]:
    """Retorna lista de arquivos .py a partir de um caminho (arquivo ou diretório recursivo)."""
    # Se o usuário passou um arquivo .py, retorna apenas esse arquivo
    if os.path.isfile(path) and path.endswith('.py'):
        return [os.path.abspath(path)]
    files = []
    for root, dirs, filenames in os.walk(path):
        for fn in filenames:
            if fn.endswith('.py'):
                files.append(os.path.join(root, fn))
    return files


def interactive_choose(start_dir: str) -> str:
    """Navegador simples de diretórios para escolher arquivo ou pasta.

    - Mostra subdiretórios e arquivos `.py` no diretório atual.
    - `0` seleciona o diretório atual.
    - número seleciona o item correspondente (diretório ou arquivo).
    - `u` sobe um nível, `e` permite digitar um caminho manualmente.
    Retorna o caminho absoluto escolhido.
    """
    cur = os.path.abspath(start_dir)
    while True:
        try:
            entries = sorted(os.listdir(cur))
        except Exception as e:
            print(f"Não foi possível listar '{cur}': {e}")
            cur = os.path.dirname(cur)
            continue

        dirs = [e for e in entries if os.path.isdir(os.path.join(cur, e))]
        pythons = [e for e in entries if os.path.isfile(os.path.join(cur, e)) and e.endswith('.py')]

        print(f"\nDiretório: {cur}")
        print("0) Selecionar este diretório")
        print("u) Subir para o diretório pai")
        print("e) Digitar caminho manualmente")

        mapping = {}
        idx = 1
        for d in dirs:
            print(f"{idx}) [DIR] {d}/")
            mapping[str(idx)] = os.path.join(cur, d)
            idx += 1
        for f in pythons:
            print(f"{idx}) {f}")
            mapping[str(idx)] = os.path.join(cur, f)
            idx += 1

        choice = input("Escolha número (ou 0/u/e): ").strip()
        if choice == '0':
            return cur
        if choice.lower() == 'u':
            parent = os.path.dirname(cur)
            if parent == cur:
                print("Já no diretório raiz.")
            else:
                cur = parent
            continue
        if choice.lower() == 'e':
            p = input("Digite caminho absoluto ou relativo: ").strip()
            if not p:
                continue
            p_abs = os.path.abspath(p)
            if os.path.exists(p_abs):
                return p_abs
            print("Caminho não existe. Tente novamente.")
            continue
        if choice in mapping:
            selected = mapping[choice]
            if os.path.isdir(selected):
                # Perguntar ao usuário se deseja analisar o diretório agora ou entrar nele
                sub = input(f"'{selected}' é um diretório — (a)nalisar recursivamente / (e)ntrar? [a/e]: ").strip().lower()
                if sub == 'e':
                    cur = selected
                    continue
                # por padrão ou se escolheu 'a', retorna o diretório para análise recursiva
                return selected
            return selected
        print("Opção inválida. Tente novamente.")


def docstring_line_numbers(source: str) -> Set[int]:
    """Retorna um conjunto de números de linha que pertencem a docstrings de
    módulo, classes e funções.

    A função analisa o AST e, quando encontra um nó cujo primeiro elemento do
    corpo é uma expressão com uma string (docstring), marca as linhas
    correspondentes à docstring.
    """
    lines = source.splitlines()
    doc_lines: Set[int] = set()
    # Tenta construir o AST do código fonte. Se não for possível (arquivo inválido),
    # retornamos conjunto vazio — não consideramos docstrings nesse caso.
    try:
        tree = ast.parse(source)
    except Exception:
        return doc_lines

    # Percorre a árvore AST buscando nós que podem ter docstrings
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, 'body', None)
            if not body:
                continue
            first = body[0]
            # Em Python 3.8+, uma docstring aparece como ast.Expr com ast.Constant contendo uma str
            if isinstance(first, ast.Expr) and isinstance(getattr(first, 'value', None), ast.Constant) and isinstance(first.value.value, str):
                start = first.lineno
                # Calcula quantas linhas a docstring ocupa e marca cada linha
                docstring_value = first.value.value
                span = docstring_value.count('\n') + 1
                for i in range(start, start + span):
                    doc_lines.add(i)
    return doc_lines


def count_lines_in_file(path: str) -> Tuple[int, int, int, int]:
    """Conta linhas do arquivo Python ignorando comentários e linhas vazias.

    Retorna tupla: (total, code, comments, blanks)
    """
    # Lê todo o conteúdo do arquivo como texto (UTF-8). Se houver erro aqui,
    # deixamos a exceção propagar para que o chamador possa decidir o que fazer.
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        raise

    lines = source.splitlines()
    total = len(lines)

    # Detecta comentários de linha usando o gerador de tokens. Cada token do tipo
    # COMMENT fornece a linha onde o comentário está — marcamos essas linhas.
    comment_lines: Set[int] = set()
    try:
        token_gen = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok_type, tok_string, start, end, _ in token_gen:
            if tok_type == tokenize.COMMENT:
                lineno = start[0]
                comment_lines.add(lineno)
    except Exception:
        # Em casos raros (arquivos malformados), tokenize pode falhar; ignoramos
        # e continuamos sem marcar comentários via tokenize.
        pass

    # Detecta docstrings analisando o AST (linhas ocupadas pelas docstrings)
    doc_lines = docstring_line_numbers(source)

    code = 0
    comments = 0
    blanks = 0

    # Percorre todas as linhas e classifica cada uma em código, comentário ou vazia
    for idx, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if stripped == '':
            blanks += 1
        elif idx in comment_lines or idx in doc_lines:
            comments += 1
        else:
            code += 1

    return total, code, comments, blanks


def analyze(path: str) -> dict:
    """Analisa um caminho (arquivo ou diretório) e agrega estatísticas."""
    files = find_py_files(path)
    results = {}
    agg = {'files': 0, 'total': 0, 'code': 0, 'comments': 0, 'blanks': 0}
    # Para cada arquivo Python encontrado, conta as linhas e acumula os totais
    for f in sorted(files):
        try:
            total, code, comments, blanks = count_lines_in_file(f)
        except Exception as e:
            # Se não conseguimos ler/parsear um arquivo, apenas o ignoramos
            continue
        results[f] = {'total': total, 'code': code, 'comments': comments, 'blanks': blanks}
        agg['files'] += 1
        agg['total'] += total
        agg['code'] += code
        agg['comments'] += comments
        agg['blanks'] += blanks
    return {'files': results, 'aggregate': agg}


def main(argv=None):
    # Parser de argumentos: aceita um caminho opcional e a flag --json
    parser = argparse.ArgumentParser(description='Conta linhas de código Python (ignora comentários e linhas vazias).')
    parser.add_argument('path', nargs='?', default=None, help='Arquivo .py ou diretório a analisar (se omitido, modo interativo)')
    parser.add_argument('--json', action='store_true', help='Imprime saída em JSON')
    args = parser.parse_args(argv)

    path = args.path
    # Se o usuário não informou caminho, usamos o seletor interativo
    if path is None:
        print("Nenhum caminho informado — entrando em modo interativo para escolha do arquivo/pasta.")
        path = interactive_choose(os.getcwd())

    # Valida que o caminho existe antes de prosseguir
    if not os.path.exists(path):
        print(f"Caminho não encontrado: {path}")
        sys.exit(2)

    # Executa a análise e exibe o resultado em JSON ou em formato legível
    res = analyze(path)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    # Impressão legível: por arquivo e agregados ao final
    agg = res['aggregate']
    for f, stats in res['files'].items():
        print(f"Arquivo: {f}")
        print(f"  Total: {stats['total']}  Código: {stats['code']}  Comentários: {stats['comments']}  Vazias: {stats['blanks']}")
    print('---')
    print(f"Arquivos analisados: {agg['files']}")
    print(f"Total linhas: {agg['total']}  Código: {agg['code']}  Comentários: {agg['comments']}  Vazias: {agg['blanks']}")


if __name__ == '__main__':
    main()
