# Contexto Gemini: etcd3aio

Este documento fornece uma visão geral abrangente do projeto `etcd3aio`, destinada a ser usada como contexto para assistência ao desenvolvimento com IA.

## Visão Geral do Projeto

`etcd3aio` é uma biblioteca cliente Python assíncrona para etcd v3. Utiliza `grpc.aio` para comunicação com o cluster etcd. A biblioteca fornece uma fachada simples e de alto nível para interagir com os serviços etcd como Key-Value, Lease e Watch.

**Tecnologias Principais:**

*   **Python 3.13+**
*   **gRPC (`grpc.aio`)**: Para comunicação assíncrona com o etcd.
*   **etcd v3**

**Arquitetura:**

O projeto é estruturado como uma biblioteca Python padrão com o código-fonte localizado no diretório `src/etcd3aio`. É dividido em módulos, cada um correspondendo a um serviço etcd específico (ex.: `kv.py`, `lease.py`, `watch.py`). O ponto de entrada principal é a classe `Etcd3Client` em `src/etcd3aio/client.py`, que atua como fachada para todos os serviços.

O projeto usa `setuptools` para empacotamento, `pytest` para testes, `ruff` para linting e formatação, e `pyright` para verificação estática de tipos.

## Build e Execução

### Configuração do Ambiente de Desenvolvimento Local

Para configurar o ambiente de desenvolvimento local, você precisa do `uv`.

1.  **Criar e ativar o ambiente virtual:**
    ```bash
    uv venv
    ```

2.  **Instalar o projeto em modo editável com todas as dependências:**
    ```bash
    uv pip install -e .
    ```

### Executando um Cluster etcd

O projeto inclui um arquivo `docker-compose.yaml` para executar facilmente um cluster etcd local.

```bash
docker compose -f docker/docker-compose.yaml up -d
```

### Executando Verificações de Qualidade

Os seguintes comandos são usados para garantir a qualidade do código:

*   **Formatar o código:**
    ```bash
    .venv/bin/ruff format .
    ```

*   **Fazer lint do código:**
    ```bash
    .venv/bin/ruff check --fix .
    ```

*   **Verificação de tipos:**
    ```bash
    .venv/bin/pyright
    ```

*   **Executar os testes:**
    ```bash
    .venv/bin/pytest
    ```

## Convenções de Desenvolvimento

*   **Seguir o `CONTRACT.md`**: Aderir ao contrato não negociável do projeto.
*   **Mudanças pequenas e focadas**: Manter os pull requests pequenos e focados em um único problema ou funcionalidade.
*   **Não editar os arquivos protobuf gerados**: Os arquivos protobuf em `src/etcd3aio/proto` são gerados e não devem ser editados manualmente.
*   **Compatibilidade retroativa**: A API pública deve permanecer compatível com versões anteriores.
*   **Adicionar testes**: Todas as mudanças de comportamento devem ser acompanhadas de testes.
*   **Estilo de código**: O projeto usa `ruff` para aplicar um estilo de código consistente. A configuração pode ser encontrada em `pyproject.toml`.
