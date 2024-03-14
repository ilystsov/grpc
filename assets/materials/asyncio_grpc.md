[Вернуться][main]

---

# AsyncIO и gRPC

Поддержка `AsyncIO` в официальном пакете `gRPC` долгое время отсутствовала. Она все еще является
экспериментальной и находится в стадии активной разработки, но если вы действительно хотите попробовать `AsyncIO` в
своих
микросервисах, то это может быть хорошим вариантом. Вы можете ознакомиться с документацией по `gRPC` `AsyncIO` для
получения
более подробной информации.

Существует также сторонний пакет `grpclib`, который реализует поддержку `AsyncIO` для `gRPC` и существует дольше.

Будьте крайне осторожны с `AsyncIO` на стороне сервера. Легко случайно написать блокирующий код, который поставит ваш
микросервис на колени. В качестве демонстрации вот как можно написать рекомендательный микросервис с использованием
`AsyncIO`, убрав всю логику:

```py
import time

import asyncio
import grpc
import grpc.experimental.aio

from recommendations_pb2 import (
    BookCategory,
    BookRecommendation,
    RecommendationResponse,
)
import recommendations_pb2_grpc


class AsyncRecommendations(recommendations_pb2_grpc.RecommendationsServicer):
    async def Recommend(self, request, context):
        print("Handling request")
        time.sleep(5)  # Oops, blocking!
        print("Done")
        return RecommendationResponse(recommendations=[])


async def main():
    grpc.experimental.aio.init_grpc_aio()
    server = grpc.experimental.aio.server()
    server.add_insecure_port("[::]:50051")
    recommendations_pb2_grpc.add_RecommendationsServicer_to_server(
        AsyncRecommendations(), server
    )
    await server.start()
    await server.wait_for_termination()


asyncio.run(main())
```

В этом коде есть ошибка. В строке 17 вы случайно сделали блокирующий вызов внутри асинхронной функции, что является
большим недопущением. Поскольку серверы `AsyncIO` являются однопоточными, это блокирует весь сервер, так что он может
обрабатывать только один запрос за раз. Это гораздо хуже, чем в случае с многопоточным сервером.

Можно продемонстрировать это, выполнив несколько одновременных запросов:

```py
from concurrent.futures import ThreadPoolExecutor

import grpc

from recommendations_pb2 import BookCategory, RecommendationRequest
from recommendations_pb2_grpc import RecommendationsStub

request = RecommendationRequest(user_id=1, category=BookCategory.MYSTERY)
channel = grpc.insecure_channel("localhost:50051")
client = RecommendationsStub(channel)

executor = ThreadPoolExecutor(max_workers=5)
a = executor.submit(client.Recommend, request)
b = executor.submit(client.Recommend, request)
c = executor.submit(client.Recommend, request)
d = executor.submit(client.Recommend, request)
e = executor.submit(client.Recommend, request)
```

Это сделает пять одновременных запросов, но на стороне сервера вы увидите следующее:

```sh
Handling request
Done
Handling request
Done
Handling request
Done
Handling request
Done
Handling request
Done
```

Запросы обрабатываются последовательно, а это не то, что вам нужно!

Есть варианты использования `AsyncIO` на стороне сервера, но вы должны быть очень осторожны, чтобы не блокировать. Это
означает, что вы не можете использовать стандартные пакеты, такие как запросы, или даже выполнять `RPC` к другим
микросервисам, если вы не запустите их в другом потоке с помощью `run_in_executor`.

Также нужно быть осторожным с запросами к базе данных. Многие из пакетов `Python`, которыми вы привыкли
пользоваться, могут пока не поддерживать `AsyncIO`, поэтому внимательно проверьте, поддерживают ли они его. Если у вас нет
сильной потребности в `AsyncIO` на стороне сервера, возможно, будет безопаснее подождать, пока не появится поддержка
пакетов. Блокирующие ошибки бывает трудно найти.


---

[Вернуться][main]


[main]: ../../README.md "содержание"

