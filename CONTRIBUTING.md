# Contribuindo

## Configuração Local

```bash
uv venv
uv pip install -e .
```

## Executar Verificações de Qualidade

```bash
.venv/bin/ruff format .
.venv/bin/ruff check --fix .
.venv/bin/pyright
.venv/bin/pytest
```

## Regras

- Seguir o `CONTRACT.md`.
- Manter as mudanças pequenas e focadas.
- Não editar os arquivos protobuf gerados.
- Manter a API pública compatível com versões anteriores.
- Adicionar testes para mudanças de comportamento.
