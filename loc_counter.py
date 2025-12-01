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


def find_py_files(path: str) -> List[str]:
    """Retorna lista de arquivos .py a partir de um caminho (arquivo ou diretório recursivo)."""
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
    try:
        tree = ast.parse(source)
    except Exception:
        return doc_lines

    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, 'body', None)
            if not body:
                continue
            first = body[0]
            # Docstring é um ast.Expr com ast.Constant (string) em Python 3.8+
            if isinstance(first, ast.Expr) and isinstance(getattr(first, 'value', None), ast.Constant) and isinstance(first.value.value, str):
                start = first.lineno
                # Conte quantas linhas a string tem
                docstring_value = first.value.value
                span = docstring_value.count('\n') + 1
                for i in range(start, start + span):
                    doc_lines.add(i)
    return doc_lines


def count_lines_in_file(path: str) -> Tuple[int, int, int, int]:
    """Conta linhas do arquivo Python ignorando comentários e linhas vazias.

    Retorna tupla: (total, code, comments, blanks)
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        raise

    lines = source.splitlines()
    total = len(lines)

    # detectar comentários via tokenize
    comment_lines: Set[int] = set()
    try:
        token_gen = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok_type, tok_string, start, end, _ in token_gen:
            if tok_type == tokenize.COMMENT:
                lineno = start[0]
                comment_lines.add(lineno)
    except Exception:
        pass

    # detectar docstrings via ast
    doc_lines = docstring_line_numbers(source)

    code = 0
    comments = 0
    blanks = 0

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
    for f in sorted(files):
        try:
            total, code, comments, blanks = count_lines_in_file(f)
        except Exception as e:
            # pular arquivos que não podem ser lidos
            continue
        results[f] = {'total': total, 'code': code, 'comments': comments, 'blanks': blanks}
        agg['files'] += 1
        agg['total'] += total
        agg['code'] += code
        agg['comments'] += comments
        agg['blanks'] += blanks
    return {'files': results, 'aggregate': agg}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Conta linhas de código Python (ignora comentários e linhas vazias).')
    parser.add_argument('path', nargs='?', default=None, help='Arquivo .py ou diretório a analisar (se omitido, modo interativo)')
    parser.add_argument('--json', action='store_true', help='Imprime saída em JSON')
    args = parser.parse_args(argv)

    path = args.path
    if path is None:
        print("Nenhum caminho informado — entrando em modo interativo para escolha do arquivo/pasta.")
        path = interactive_choose(os.getcwd())

    if not os.path.exists(path):
        print(f"Caminho não encontrado: {path}")
        sys.exit(2)

    res = analyze(path)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    agg = res['aggregate']
    for f, stats in res['files'].items():
        print(f"Arquivo: {f}")
        print(f"  Total: {stats['total']}  Código: {stats['code']}  Comentários: {stats['comments']}  Vazias: {stats['blanks']}")
    print('---')
    print(f"Arquivos analisados: {agg['files']}")
    print(f"Total linhas: {agg['total']}  Código: {agg['code']}  Comentários: {agg['comments']}  Vazias: {agg['blanks']}")


if __name__ == '__main__':
    main()
