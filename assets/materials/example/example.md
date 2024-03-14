[Вернуться][main]

---

# Пример реализации

После знакомства с Protocol Buffers пришло время посмотреть, на что они способны. Термин "протокольные
буферы" довольно многозначен, поэтому в дальнейшем в семинаре мы будем использовать общепринятое сокращение
`protobufs`.

Как уже несколько раз упоминалось, вы можете генерировать код `Python` из `protobufs`. Инструмент устанавливается в
составе пакета `grpcio-tools`.

Сначала определим начальную структуру каталогов:

```
.
├── protobufs/
│   └── recommendations.proto
|
└── recommendations/
```

В директории `protobufs/` будет находиться файл [recommendations.proto](./protobufs/recommendations.proto).
Содержимое этого файла - код протобафа:

```Protocol Buffer
syntax = "proto3";

enum BookCategory {
    MYSTERY = 0;
    SCIENCE_FICTION = 1;
    SELF_HELP = 2;
}

message RecommendationRequest {
    int32 user_id = 1;
    BookCategory category = 2;
    int32 max_results = 3;
}

message BookRecommendation {
    int32 id = 1;
    string title = 2;
}

message RecommendationResponse {
    repeated BookRecommendation recommendations = 1;
}

service Recommendations {
    rpc Recommend (RecommendationRequest) returns (RecommendationResponse);
}
```

Вы будете генерировать Python-код для взаимодействия с ним внутри каталога `recommendations/`. Сначала необходимо
установить `grpcio-tools`. Создайте файл `recommendations/requirements.txt` и добавьте в него следующее:

```
grpcio-tools ~= 1.62.1
```

Чтобы запустить код локально, вам нужно установить зависимости в виртуальное окружение.
В Linux и macOS используйте следующие команды для создания виртуальной среды и установки зависимостей:

```sh
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Теперь, чтобы сгенерировать код Python из протобафа, выполните следующее:

```sh
cd recommendations
python -m grpc_tools.protoc -I ../protobufs --python_out=. --grpc_python_out=. ../protobufs/recommendations.proto
```

Из файла `.proto` генерируется несколько файлов Python. Подробности о запуске:

- `python -m grpc_tools.protoc` запускает компилятор `protobuf`,
  который будет генерировать код Python из кода `protobuf`.
- `-I ../protobufs` указывает компилятору, где найти файлы, которые импортирует ваш код `protobuf`.
  На самом деле вы не используете функцию импорта, но тем не менее флаг `-I` необходим.
- `--python_out=. --grpc_python_out=.` указывает компилятору, куда выводить файлы Python. Как вы скоро увидите, он
  сгенерирует два файла, и при желании вы можете поместить каждый из них в отдельный каталог с этими параметрами.
- `../protobufs/recommendations.proto` - это путь к файлу `protobuf`, который будет использоваться для генерации
  Python-кода.

Если вы посмотрите на то, что будет сгенерировано, то увидите два новых файла:

```
recommendations_pb2.py recommendations_pb2_grpc.py
```

Эти файлы содержат типы и функции Python для взаимодействия с вашим API. Компилятор сгенерирует код клиента для вызова
RPC и код сервера для реализации RPC. Сначала вы рассмотрите клиентскую часть.

## Клиент RPC

Генерируемый код может понравиться только материнской плате. Иными словами, это не очень красивый Python. Это потому,
что он не предназначен для чтения человеком. Откройте оболочку Python, чтобы посмотреть, как с ним взаимодействовать:

```py
from recommendations_pb2 import BookCategory, RecommendationRequest

request = RecommendationRequest(
    user_id=1, category=BookCategory.SCIENCE_FICTION, max_results=3
)
request.category
```

Вывод:

```py
1
```

Вы видите, что компилятор `protobuf` сгенерировал типы Python, соответствующие вашим типам `protobuf`.
Пока все хорошо. Вы также можете видеть, что в полях есть проверка типов:

```py
request = RecommendationRequest(
    user_id="тиньк", category=BookCategory.SCIENCE_FICTION, max_results=3
)
```

Вывод:

```
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
TypeError: 'str' object cannot be interpreted as an integer
```

Это показывает, что вы получите ошибку `TypeError`, если передадите неправильный тип в одно из полей `protobuf`.

Важно отметить, что все поля в `proto3` являются необязательными, поэтому вам нужно убедиться, что все они установлены.
Если вы оставите одно из них неустановленным, то по умолчанию оно будет равно нулю для числовых типов или пустой строке
для строковых:

```py
request = RecommendationRequest(
    user_id=1, category=BookCategory.SCIENCE_FICTION
)
request.max_results
```

Вывод:

```
0
```

Здесь вы получите `0`, потому что это значение по умолчанию для незаданных полей `int`.

Хотя протобафы выполняют проверку типов за вас, вам все равно нужно проверять фактические значения. Поэтому, когда вы
реализуете свой микросервис рекомендаций, вы должны убедиться, что все поля имеют правильные данные. Это всегда верно
для любого сервера, независимо от того, используете ли вы протобафы, `JSON` или что-то еще. Всегда проверяйте вводимые
данные.

Файл `recommendations_pb2.py`, который был сгенерирован для вас, содержит определения типов. Файл
`recommendations_pb2_grpc.py` содержит фреймворк для клиента и сервера. Посмотрите на импорт, необходимый для создания
клиента:

```py
import grpc
from recommendations_pb2_grpc import RecommendationsStub
```

Вы импортируете модуль `grpc`, который предоставляет некоторые функции для установки соединений с удаленными серверами.
Затем вы импортируете заглушку клиента `RPC`. Он называется заглушкой, потому что сам клиент не имеет никакой
функциональности. Он обращается к удаленному серверу и передает результат обратно.

Если вы посмотрите на определение `protobuf`, то увидите в конце сервис `Recommendations`. Компилятор `protobuf`
берет это имя микросервиса, `Recommendations`, и добавляет к нему `Stub`, чтобы сформировать имя клиента,
`RecommendationsStub`.

Теперь вы можете сделать RPC-запрос:

```py
channel = grpc.insecure_channel("localhost:50051")
client = RecommendationsStub(channel)
request = RecommendationRequest(
    user_id=1, category=BookCategory.SCIENCE_FICTION, max_results=3
)
client.Recommend(request)
```

Вывод:

```
Traceback (most recent call last):
  ...
grpc._channel._InactiveRpcError: <_InactiveRpcError of RPC that terminated with:
    status = StatusCode.UNAVAILABLE
    details = "failed to connect to all addresses"
    ...
```

Вы создаете соединение с localhost, вашей собственной машиной, на порту `50051`. Этот порт является стандартным портом
для gRPC, но вы можете изменить его, если хотите. Пока что вы будете использовать небезопасный канал, который является
неаутентифицированным и незашифрованным, но вы узнаете, как использовать безопасные каналы позже в этом семинаре. Затем
вы передаете этот канал в заглушку для инстанцирования клиента.

Теперь вы можете вызвать метод `Recommend`, который вы определили для своего микросервиса `Recommendations`. Вспомните
строку 25 в определении `protobuf`: `rpc Recommend (...)` возвращает `(...)`. Вот откуда берется метод `Recommend`.
Вы получите исключение, потому что на `localhost:50051` не запущен микросервис.

Теперь, когда вы разобрались с клиентом, перейдем к серверной части.

## Сервер RPC

Тестирование клиента в консоли - это одно, а вот реализация сервера в ней - это уже перебор. Вы можете оставить консоль
открытой, но реализовывать микросервис вы будете в файле.

Начните с импорта и некоторых данных:

```py
# recommendations/recommendations.py
from concurrent import futures
import random

import grpc

from recommendations_pb2 import (
    BookCategory,
    BookRecommendation,
    RecommendationResponse,
)
import recommendations_pb2_grpc

books_by_category = {
    BookCategory.MYSTERY: [
        BookRecommendation(id=1, title="The Maltese Falcon"),
        BookRecommendation(id=2, title="Murder on the Orient Express"),
        BookRecommendation(id=3, title="The Hound of the Baskervilles"),
    ],
    BookCategory.SCIENCE_FICTION: [
        BookRecommendation(
            id=4, title="The Hitchhiker's Guide to the Galaxy"
        ),
        BookRecommendation(id=5, title="Ender's Game"),
        BookRecommendation(id=6, title="The Dune Chronicles"),
    ],
    BookCategory.SELF_HELP: [
        BookRecommendation(
            id=7, title="The 7 Habits of Highly Effective People"
        ),
        BookRecommendation(
            id=8, title="How to Win Friends and Influence People"
        ),
        BookRecommendation(id=9, title="Man's Search for Meaning"),
    ],
}
```

Этот код импортирует ваши зависимости и создает некоторые примеры данных. Вот разбивка:

- Строка 2 импортирует futures, потому что gRPC нужен пул потоков. К этому вы перейдете позже.
- Строка 3 импортирует random, потому что вы собираетесь случайным образом выбирать книги для рекомендаций.
- В строке 14 создается словарь books_by_category, в котором ключами являются категории книг, а значениями - списки книг
  в
  этой категории. В реальном микросервисе рекомендаций книги будут храниться в базе данных.

Далее вы создадите класс, реализующий функции микросервиса:

```py
class RecommendationService(
    recommendations_pb2_grpc.RecommendationsServicer
):
    def Recommend(self, request, context):
        if request.category not in books_by_category:
            context.abort(grpc.StatusCode.NOT_FOUND, "Category not found")

        books_for_category = books_by_category[request.category]
        num_results = min(request.max_results, len(books_for_category))
        books_to_recommend = random.sample(
            books_for_category, num_results
        )

        return RecommendationResponse(recommendations=books_to_recommend)
```

Вы создали класс с методом для реализации Recommend RPC. Подробнее:

- В строке 29 определяется класс `RecommendationService`. Это реализация вашего микросервиса. Обратите внимание, что вы
  создали подкласс `RecommendationsServicer`. Это часть интеграции с `gRPC`, которую вам нужно сделать.

- В строке 32 определяется метод `Recommend()` вашего класса. Он должен иметь то же имя, что и `RPC`, который вы
  определили в
  вашем файле `protobuf`. Он также принимает `RecommendationRequest` и возвращает `RecommendationResponse`, как и в
  определении
  `protobuf`. Он также принимает параметр контекста. Контекст позволяет задать код состояния для ответа.

- В строках 33 и 34 используется `abort()` для завершения запроса и установки кода состояния `NOT_FOUND` в случае
  получения
  неожиданной категории. Поскольку `gRPC` построен на базе `HTTP/2`, код состояния похож на стандартный код
  состояния ``HTTP``.
  Его установка позволяет клиенту предпринимать различные действия в зависимости от полученного кода. Он также позволяет
  промежуточному программному обеспечению, например системам мониторинга, регистрировать количество запросов с ошибками.

- Строки 36-40 случайным образом выбирают несколько книг из заданной категории для рекомендации. Вы должны убедиться,
  что
  количество рекомендаций не превышает `max_results`. Вы используете `min()`, чтобы убедиться, что вы не запрашиваете
  больше
  книг, чем есть, иначе `random.sample` выдаст ошибку.

- Строка 38 возвращает объект `RecommendationResponse` со списком рекомендаций книг.

Обратите внимание, что было бы лучше поднимать исключение при ошибке, а не использовать `abort()`, как в этом примере,
но
тогда в ответе не будет правильно установлен код состояния. Есть способ обойти это, к которому вы перейдете позже в
семинаре, когда будете рассматривать перехватчики.

Класс `RecommendationService` определяет реализацию вашего микросервиса, но вам все равно нужно его запустить.
Именно это и делает функция `serve()`:

```py
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    recommendations_pb2_grpc.add_RecommendationsServicer_to_server(
        RecommendationService(), server
    )
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
```

`serve()` запускает сетевой сервер и использует ваш класс микросервиса для обработки запросов:

- В строке 42 создается сервер `gRPC`. Вы указываете ему использовать 10 потоков для обслуживания запросов, что является
  полным излишеством для этом семинаре, но хорошим значением по умолчанию для реального микросервиса `Python`.
- Строка 43 связывает ваш класс с сервером. Это похоже на добавление обработчика запросов.
- Строка 46 указывает серверу работать на порту `50051`. Как уже говорилось, это стандартный порт для `gRPC`,
  но вы можете использовать любой другой.
- Строки 47 и 48 вызывают `server.start()` и `server.wait_for_termination()`, чтобы запустить микросервис и подождать,
  пока он не будет остановлен. Единственный способ остановить его в этом случае - `Ctrl+C` в терминале. В
  продакшн среде существуют более эффективные способы остановки, о которых мы поговорим позже.

Не закрывая терминал, который вы использовали для тестирования клиента, откройте новый терминал и выполните следующую
команду:

```sh
python recommendations.py
```

Это запустит микросервис `Recommendations`, чтобы вы могли протестировать клиента на некоторых реальных данных. Теперь
вернитесь в терминал, который вы использовали для тестирования клиента, чтобы создать заглушку канала. Запустим:

```py
import grpc
from recommendations_pb2_grpc import RecommendationsStub

channel = grpc.insecure_channel("localhost:50051")
client = RecommendationsStub(channel)
```

Теперь, когда у вас есть объект клиента, вы можете сделать запрос:

```py
request = RecommendationRequest(
    user_id=1, category=BookCategory.SCIENCE_FICTION, max_results=3)
client.Recommend(request)
```

Вывод:

```
recommendations {
  id: 5
  title: "Ender\'s Game"
}
recommendations {
  id: 6
  title: "The Dune Chronicles"
}
recommendations {
  id: 4
  title: "The Hitchhiker\'s Guide to the Galaxy"
}
```

Работает! Вы сделали RPC-запрос к своему микросервису и получили ответ! Обратите внимание, что вывод, который вы
видите, может быть другим, потому что рекомендации выбираются случайным образом.

Теперь, когда у вас есть реализованный сервер, вы можете реализовать микросервис `Marketplace` и заставить его вызывать
микросервис `Recommendations`. Теперь вы можете закрыть консоль `Python`, если хотите, но оставить микросервис
`Recommendations` запущенным.

## Свяжем всё вместе

Создайте новый каталог `marketplace/` и поместите в него файл `marketplace.py` для вашего микросервиса `Marketplace`.
Теперь дерево ваших каталогов должно выглядеть следующим образом:

```
.
├── marketplace/
│   ├── marketplace.py
│   ├── requirements.txt
│   └── templates/
│       └── homepage.html
|
├── protobufs/
│   └── recommendations.proto
|
└── recommendations/
    ├── recommendations.py
    ├── recommendations_pb2.py
    ├── recommendations_pb2_grpc.py
    └── requirements.txt
```

Обратите внимание на новый каталог `marketplace/` для кода вашего микросервиса, файл `requirements.txt` и домашнюю
страницу.
Все они будут описаны ниже. Вы можете пока создать для них пустые файлы и заполнить их позже.

Вы можете начать с кода микросервиса. Микросервис `Marketplace` будет представлять собой приложение `Flask` для
отображения
веб-страницы пользователю. Он будет вызывать микросервис `Recommendations`, чтобы получить рекомендации книг для
отображения на странице.

Откройте файл `marketplace/marketplace.py` и добавьте следующее:

```py
# marketplace/marketplace.py
import os

from flask import Flask, render_template
import grpc

from recommendations_pb2 import BookCategory, RecommendationRequest
from recommendations_pb2_grpc import RecommendationsStub

app = Flask(__name__)

recommendations_host = os.getenv("RECOMMENDATIONS_HOST", "localhost")
recommendations_channel = grpc.insecure_channel(
    f"{recommendations_host}:50051"
)
recommendations_client = RecommendationsStub(recommendations_channel)


@app.route("/")
def render_homepage():
    recommendations_request = RecommendationRequest(
        user_id=1, category=BookCategory.MYSTERY, max_results=3
    )
    recommendations_response = recommendations_client.Recommend(
        recommendations_request
    )
    return render_template(
        "homepage.html",
        recommendations=recommendations_response.recommendations,
    )
```

Вы настраиваете Flask, создаете gRPC-клиент и добавляете функцию для рендеринга домашней страницы. Подробности:

- В строке 10 создается приложение `Flask` для рендеринга веб-страницы для пользователя.
- В строках с 12 по 16 создается канал `gRPC` и заглушка.
- В строках с 20 по 30 создается `render_homepage()`, которая будет вызываться, когда пользователь зайдет на главную
  страницу вашего приложения. Она возвращает HTML-страницу, загруженную из шаблона, с тремя рекомендациями
  научно-фантастических книг.

> Примечание: В этом примере вы создаете канал `gRPC` и заглушку как глобальные файлы. Обычно глобальные файлы не
> используются, но в данном случае оправдано исключение.
>
> Канал `gRPC` поддерживает постоянное соединение с сервером, чтобы избежать накладных расходов на повторное
> подключение.
> Он может обрабатывать множество одновременных запросов и восстанавливать прерванные соединения. Однако если вы будете
> создавать новый канал перед каждым запросом, то `Python` будет собирать его в мусор, и вы не получите большинства
> преимуществ постоянного соединения.
>
> Вы хотите, чтобы канал оставался открытым, чтобы вам не нужно было заново подключаться к рекомендательному
> микросервису для каждого запроса. Вы могли бы спрятать канал в другом модуле, но поскольку в данном случае у вас
> только
> один файл, вы можете упростить ситуацию, используя globals.

Откройте файл `homepage.html` в каталоге `marketplace/templates/` и добавьте следующий HTML:

```html
<!-- homepage.html -->
<!doctype html>
<html lang="en">
<head>
    <title>Online Books For You</title>
</head>
<body>
<h1>Mystery books you may like</h1>
<ul>
    {% for book in recommendations %}
    <li>{{ book.title }}</li>
    {% endfor %}
</ul>
</body>
```

Это только демонстрационная домашняя страница. По окончании работы она должна отображать список рекомендаций книг.

Чтобы запустить этот код, вам понадобятся следующие зависимости, которые вы можете добавить в
`marketplace/requirements.txt`:

```
flask ~= 3.0.2
grpcio-tools ~= 1.30
pytest ~= 8.1.1
```

Микросервисы `Recommendations` и `Marketplace` будут иметь свой собственный файл `requirements.txt`, но для удобства в
этом
семинаре вы можете использовать одну и ту же виртуальное окружение для обоих. Выполните следующие действия, чтобы
обновить виртуальное окружение:

```sh
python -m pip install -r marketplace/requirements.txt
```

Теперь, когда вы установили все зависимости, необходимо сгенерировать код для протобафов в каталоге `marketplace/`.
Для этого выполните в консоли следующие действия:

```sh
cd marketplace
python -m grpc_tools.protoc -I ../protobufs --python_out=. --grpc_python_out=. ../protobufs/recommendations.proto
```

Это та же команда, которую вы выполняли раньше, так что ничего нового здесь нет. Может показаться странным наличие
одинаковых файлов в каталогах `marketplace/` и `recommendations/`, но позже вы увидите, как автоматически генерировать
их в
процессе развёртывания. Обычно вы не храните их в системе контроля версий вроде Git.

Чтобы запустить микросервис `Marketplace`, введите в консоли следующее:

```sh
FLASK_APP=marketplace.py flask run
```

Теперь у вас должны быть запущены микросервисы `Recommendations` и `Marketplace` в двух разных консолях. Если вы
отключили
микросервис `Recommendations`, перезапустите его в другой консоли, выполнив следующие действия:

```sh
cd recommendations
python recommendations.py
```

Это запустит ваше приложение `Flask`, которое по умолчанию работает на порту `5000`.
Откройте его в браузере по ссылке http://127.0.0.1:5000 и увидите:

![Homepage](./img/img.png)

Теперь у вас есть два микросервиса, которые общаются друг с другом! Но они все еще находятся только на вашей машине для
разработки. Далее вы узнаете, как перевести их в продакшн среду.

Вы можете остановить ваши Python-микросервисы, используя `Ctrl+C `в терминале. Далее вы будете запускать их
в Docker, и именно так они будут работать в продакшн среде.

---

[Вернуться][main]


[main]: ../../../README.md "содержание"

