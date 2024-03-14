[Вернуться][main]

---

# Мониторинг микросервисов с помощью перехватчиков

После того как вы разместили в облаке несколько микросервисов, вам необходимо получить представление о том, как они
работают. Некоторые вещи, которые вы хотите отслеживать, включают:

- Сколько запросов получает каждый микросервис
- Сколько запросов приводит к ошибке и какого типа она возникает
- Задержка каждого запроса
- Логи исключений, чтобы вы могли отладить их в дальнейшем.

В следующих разделах вы узнаете о нескольких способах сделать это.

## Почему не декораторы

Один из способов сделать это, наиболее естественный для разработчиков на Python, - добавить декоратор к каждой конечной
точке микросервиса. Однако в этом случае у использования декораторов есть несколько минусов:

- Разработчики новых микросервисов должны помнить о необходимости добавлять их в каждый метод.
- Если у вас много мониторингов, то в итоге может получиться целая стопка декораторов.
- Если у вас есть стопка декораторов, то разработчики могут разместить их в неправильном порядке.
- Вы можете объединить весь мониторинг в один декоратор, но тогда это может привести к беспорядку.

Например такой стопки декораторов вы хотите избежать:

```py
class RecommendationService(recommendations_pb2_grpc.RecommendationsServicer):
    @catch_and_log_exceptions
    @log_request_counts
    @log_latency
    def Recommend(self, request, context):
        ...
```

## Перехватчики - Interceptors

Существует альтернативный подход к использованию декораторов, который вы рассмотрите в этом разделе: в `gRPC` есть
концепция
перехватчика, которая обеспечивает функциональность, аналогичную декораторам, но в более чистом виде.

### Реализация перехватчиков

К сожалению, Python-реализация `gRPC` имеет довольно сложный API для перехватчиков. Это объясняется его невероятной
гибкостью. Однако для их упрощения существует пакет `grpc-interceptor`.

Добавьте его в файл `recommendations/requirements.txt` вместе с `pytest`, который вы будете использовать в ближайшее
время:

```
grpcio-tools ~= 1.62.1
grpc-interceptor ~= 0.15.4
pytest ~= 8.1.1
```

Затем обновите виртуальное окружение:

```sh
python -m pip install recommendations/requirements.txt
```

Теперь вы можете создать перехватчик с помощью следующего кода. Вам не нужно добавлять
его в свой проект, так как это просто пример:

```py
from grpc_interceptor import ServerInterceptor


class ErrorLogger(ServerInterceptor):
    def intercept(self, method, request, context, method_name):
        try:
            return method(request, context)
        except Exception as e:
            self.log_error(e)
            raise

    def log_error(self, e: Exception) -> None:
# ...
```

Это вызовет `log_error()` всякий раз, когда будет вызвано необработанное исключение в вашем микросервисе. Вы можете
реализовать это, например, регистрируя исключения в `Sentry`, чтобы получать предупреждения и отладочную информацию,
когда
они происходят.

Чтобы использовать этот перехватчик, вы передадите его в `grpc.server()` следующим образом:

```py
interceptors = [ErrorLogger()]
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors)
```

С помощью этого кода каждый запрос к микросервису Python и ответ от него будут проходить через ваш перехватчик, и вы
сможете подсчитать, сколько запросов и ошибок он получает.

`grpc-interceptor` также предоставляет исключение для каждого кода состояния `gRPC` и перехватчик под названием
`ExceptionToStatusInterceptor`. Если одно из исключений будет вызвано микросервисом, то `ExceptionToStatusInterceptor`
установит код статуса `gRPC`. Это позволит вам упростить микросервис, внеся в файл `recommendations/recommendations.py`
изменения, указанные ниже:

```py
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound


# ...

class RecommendationService(recommendations_pb2_grpc.RecommendationsServicer):
    def Recommend(self, request, context):
        if request.category not in books_by_category:
            raise NotFound("Category not found")

        books_for_category = books_by_category[request.category]
        num_results = min(request.max_results, len(books_for_category))
        books_to_recommend = random.sample(books_for_category, num_results)

        return RecommendationResponse(recommendations=books_to_recommend)


def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=interceptors
    )
    # ...
```

Это более удобно для чтения. Вы также можете поднять исключение из многих функций вниз по стеку вызовов, а не передавать
контекст для вызова `context.abort()`. Вам также не придется самостоятельно перехватывать исключение в своем
микросервисе - перехватчик перехватит его за вас.

### Тестирование перехватчиков

Если вы хотите написать свои собственные перехватчики, то вам следует их протестировать. Но при тестировании
перехватчиков опасно слишком много издеваться над ними. Например, вы можете вызвать `.intercept()` в тесте и убедиться,
что он возвращает то, что вы хотите, но это не позволит проверить реалистичность вводимых данных или то, что они вообще
будут вызваны.

Чтобы улучшить тестирование, вы можете запустить микросервис `gRPC` с перехватчиками. Пакет `grpc-interceptor`
предоставляет
фреймворк для этого. Ниже вы напишете тест для перехватчика `ErrorLogger`. Это всего лишь пример, поэтому вам не нужно
добавлять его в свой проект. Если бы вы добавили его, то добавили бы его в тестовый файл.

Вот как можно написать тест для перехватчика:

```py
from grpc_interceptor.testing import dummy_client, DummyRequest, raises


class MockErrorLogger(ErrorLogger):
    def __init__(self):
        self.logged_exception = None

    def log_error(self, e: Exception) -> None:
        self.logged_exception = e


def test_log_error():
    mock = MockErrorLogger()
    ex = Exception()
    special_cases = {"error": raises(ex)}

    with dummy_client(special_cases=special_cases, interceptors=[mock]) as client:
        # Test no exception
        assert client.Execute(DummyRequest(input="foo")).output == "foo"
        assert mock.logged_exception is None

        # Test exception
        with pytest.raises(grpc.RpcError) as e:
            client.Execute(DummyRequest(input="error"))
        assert mock.logged_exception is ex
```

Что тут происходит:

- В строках с 3 по 8 подкласс `ErrorLogger` имитирует `log_error()`. На самом деле вы не хотите, чтобы побочный эффект
  логирования происходил. Вы просто хотите убедиться, что она вызывается.

- В строках с 15 по 18 используется менеджер контекста `dummy_client()` для создания клиента, подключенного к настоящему
  микросервису `gRPC`. Вы отправляете микросервису `DummyRequest`, а он отвечает `DummyResponse`. По умолчанию входной сигнал
  `DummyRequest` эхом передается в выходной сигнал `DummyResponse`. Однако вы можете передать `dummy_client()` словарь особых
  случаев, и если входные данные соответствуют одному из них, то он вызовет указанную вами функцию и вернет результат.

- Строки 21-23: Вы проверяете, что `log_error()` вызывается с ожидаемым исключением. `raises()` возвращает другую функцию,
  которая вызывает указанное исключение. Вы устанавливаете для `input` значение `error`, чтобы микросервис вызывал
  исключение.

Альтернативой перехватчикам в некоторых случаях может быть использование сервисной сетки. Она будет отправлять все
запросы и ответы микросервиса через прокси, чтобы прокси мог автоматически регистрировать такие вещи, как объем запросов
и количество ошибок. Чтобы получить точный лог ошибок, микросервису все равно нужно правильно устанавливать коды
состояния. Поэтому в некоторых случаях перехватчики могут дополнять сетку сервисов. Одной из популярных сервисных сеток
является `Istio`.


---

[Вернуться][main]


[main]: ../../../README.md "содержание"
