import asyncio
import logging

# Olha como o import agora fica limpo e direto da nossa fachada!
from aioetcd3._protobuf import KVStub, PutRequest, RangeRequest
from aioetcd3.connections import ConnectionManager

# Configurando log básico para visualizar no terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    # As portas mapeadas no docker-compose local
    endpoints = ['localhost:2379', 'localhost:3379', 'localhost:4379']

    logger.info(f'Iniciando ConnectionManager com os endpoints: {endpoints}')
    manager = ConnectionManager(endpoints)

    # O get_channel() retorna um canal assíncrono.
    # Usamos 'async with' para garantir que a conexão seja fechada adequadamente ao final.
    channel = await manager.get_channel()
    async with channel:
        logger.info('Canal gRPC estabelecido. Criando o Stub (Cliente) para o serviço KV.')

        # Instanciando o Stub usando a classe importada da nossa fachada
        kv_stub = KVStub(channel)

        # ---------------------------------------------------------
        # 1. Teste de Escrita (Put)
        # O etcd trabalha nativamente com bytes, então precisamos converter as strings.
        # ---------------------------------------------------------
        key = b'/app/estado_desejado'
        value = b'{"replicas": 3, "version": "v2.0", "description": "Teste Real"}'

        logger.info(f'Gravando estado -> Chave: {key.decode()} | Valor: {value.decode()}')

        # Montando a requisição Protobuf via fachada
        put_request = PutRequest(key=key, value=value)

        # Executando a chamada assíncrona ao cluster
        put_response = await kv_stub.Put(put_request)
        logger.info(f'Escrita confirmada! Revisão atual do cluster: {put_response.header.revision}')

        # ---------------------------------------------------------
        # 2. Teste de Leitura (Range)
        # Range é o comando padrão do etcd v3 para dar GET em uma chave ou diretório.
        # ---------------------------------------------------------
        logger.info(f'Lendo a chave: {key.decode()} do cluster...')

        range_request = RangeRequest(key=key)
        range_response = await kv_stub.Range(range_request)

        # O retorno 'kvs' é uma lista, iteramos sobre ela para pegar o resultado
        if range_response.kvs:
            for kv in range_response.kvs:
                logger.info(
                    f'Sucesso na leitura! Valor retornado: {kv.value.decode()} '
                    f'(Criado na rev: {kv.create_revision}, Modificado na rev: {kv.mod_revision})'
                )
        else:
            logger.warning('A chave não foi encontrada!')


if __name__ == '__main__':
    # Rodando o loop assíncrono nativo
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Teste interrompido pelo usuário.')
    except Exception as e:
        logger.error(f'Erro ao comunicar com o cluster: {e}')
