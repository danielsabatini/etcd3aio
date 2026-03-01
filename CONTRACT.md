# Contrato do Projeto

Este contrato define as regras obrigatórias para o `etcd3aio`.

## 1. Contrato de Produto

- Manter o código simples de usar.
- Manter o código simples de fazer manutenção.
- Manter o padrão de fachada: `Etcd3Client` expõe os serviços.
- Manter compatibilidade retroativa nas APIs públicas, salvo planejamento explícito.
- Preferir mudanças aditivas a mudanças que quebram compatibilidade.

## 2. Contrato de Execução

- Apenas Python 3.13+.
- Nunca bloquear o loop de eventos do asyncio.
- Preferir APIs assíncronas de ponta a ponta.
- Toda chamada gRPC deve ser aguardada com `await` quando aplicável.

## 3. Contrato de Código

- Utilizar uma codificação simples, mas modernar.
- Manter os detalhes do gRPC isolados nas camadas de serviço/conexão.
- Manter o `Etcd3Client` leve (apenas fiação e ciclo de vida).
- Usar tipagem forte e explícita.
- O `pyproject.toml` define o modo Pyright aplicado.
- Usar `TypeAlias` quando melhorar a legibilidade.
- Não modificar os arquivos protobuf gerados em `src/etcd3aio/proto/`.

## 4. Contrato de Confiabilidade

- Tratar falhas transitórias do gRPC de forma previsível.
- Manter as retentativas simples e centralizadas.
- Garantir que canais e streams sejam fechados/cancelados corretamente.

## 5. Contrato de Qualidade

- `ruff format .` deve passar (formata o código automaticamente).
- `ruff check --fix .` deve passar (linting).
- `pyright` deve passar.
- `pytest` deve passar.
- Novos comportamentos devem incluir testes focados.

## 6. Contrato de Documentação

- Manter a documentação curta e atualizada.
- Evitar orientações duplicadas entre arquivos.
- Preferir uma única fonte de verdade para as regras (este arquivo).

## 7. Checklist de Mudanças

Antes do merge, confirmar:

- A API permaneceu simples.
- Nenhuma abstração desnecessária foi introduzida.
- O comportamento assíncrono foi preservado.
- Tipagem e testes foram atualizados.
- As verificações de qualidade estão verdes.
- Todos os arquivos `.md` foram revisados para consistência: tabelas de módulos, status do ROADMAP e referências cruzadas correspondem à implementação atual.

## 8. Diretrizes para Exemplos da Biblioteca

- Todos os exemplos devem ser armazenados no diretório examples/.
- Para cada módulo da biblioteca, deve existir um exemplo dedicado seguindo o padrão de nome: <module>_example.py
    - Esse arquivo deve demonstrar as funcionalidades principais do módulo de forma direta e objetiva.
- Deve existir um exemplo completo chamado: full_example.py
    - Este exemplo deve demonstrar o uso integrado da biblioteca, cobrindo o fluxo completo de utilização entre os diferentes módulos.
- Deve existir também um exemplo introdutório chamado: 
get_started_example.py
    - Este arquivo deve conter os casos de uso mais comuns da biblioteca, servindo como ponto inicial para novos usuários.
- Os exemplos devem:
    - Cobrir todas as funcionalidades públicas relevantes de cada módulo.
    - Demonstrar o uso da API da forma mais simples e direta possível.
    - Evitar complexidade desnecessária, mocks excessivos ou dependências externas quando não forem essenciais.
    - Ser executáveis de forma independente.
- Cada exemplo deve priorizar clareza e valor didático, permitindo que o usuário compreenda rapidamente como utilizar o módulo ou funcionalidade.