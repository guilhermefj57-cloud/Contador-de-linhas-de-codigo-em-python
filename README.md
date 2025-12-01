# Contador de Linhas de Código (Python)

Este repositório fornece um script simples para contar linhas de código em projetos Python,
ignorando comentários e linhas vazias. O objetivo é dar uma visão clara do tamanho do
código em termos de linhas efetivas de código.

**Arquivos principais**
- `loc_counter.py`: script CLI que analisa arquivos `.py` individuais ou diretórios (recursivo) e possui um modo interativo.
- `example.py`: pequeno arquivo de exemplo para testes.

**Compatibilidade**
- Recomendado Python 3.8+.

**O que é contado**
- **Código:** linhas que contêm instruções/declarações executáveis.
- **Comentários:** linhas com `#` e docstrings (módulo/função/classe).
- **Vazias:** linhas sem conteúdo útil (apenas espaços ou tabs).

**Como o script identifica cada tipo**
- Comentários de linha são detectados com o módulo `tokenize` (tokens do tipo `COMMENT`).
- Docstrings são detectadas com `ast` (o script procura a string que aparece como primeira
  expressão no corpo de módulos, funções e classes e marca suas linhas como docstring).
- Linhas que contêm strings atribuídas a variáveis são contadas como código (não são docstrings).

## Uso básico (PowerShell)

Analisar um arquivo específico:

```powershell
python .\loc_counter.py .\example.py
```

Analisar um diretório (recursivo):

```powershell
python .\loc_counter.py .\
```

Saída em JSON (para integração):

```powershell
python .\loc_counter.py <caminho> --json
```

Exemplo de estrutura do JSON:

```json
{
  "files": {
    "C:\\projeto\\main.py": {"total": 120, "code": 80, "comments": 30, "blanks": 10}
  },
  "aggregate": {"files": 5, "total": 400, "code": 250, "comments": 120, "blanks": 30}
}
```

## Modo interativo

Se você executar o script sem passar um `path`, ele entra em um navegador simples
de diretórios no terminal. Comandos disponíveis:
- `0` : seleciona o diretório atual (será analisado recursivamente);
- números: selecionam o item correspondente (subdiretório ou arquivo `.py`);
- `u` : sobe um nível (pai);
- `e` : digitar caminho manualmente.

O navegador lista primeiro subdiretórios e depois arquivos `.py`. Se você selecionar
um arquivo `.py`, só esse arquivo será analisado; se selecionar um diretório, todos os
`.py` dentro dele (recursivamente) serão analisados.

## Exemplo de saída (legível)

```
Arquivo: C:\Users\Você\projeto\exemplo.py
  Total: 21  Código: 7  Comentários: 6  Vazias: 8
---
Arquivos analisados: 1
Total linhas: 21  Código: 7  Comentários: 6  Vazias: 8
```

## Solução de problemas
- Erro de encoding ao ler um arquivo: verifique se o arquivo está em UTF-8; converta ou edite `loc_counter.py` para tentar outro encoding.
- Arquivos não aparecem: verifique permissões e se o nome termina com `.py`.

## Melhorias possíveis
- Adicionar `--exclude`/`--include` com suporte a globs (ex.: ignorar `venv`/`__pycache__`).
- Filtrar automaticamente ambientes virtuais e caches.
- Suporte a interface gráfica (`tkinter.filedialog`) para seleção de pastas no Windows.
 
---
