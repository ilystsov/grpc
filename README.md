# Домашнее задание: "Python микросервисы с gRPC". Документация о проделанной работе.
## Создание gRPC сервиса
Прежде всего, напишем **protobuf** файл `service.proto`. 
В методе-приветствии
добавим возможность выбирать стиль приветствия,
а в методе-сумматоре учтем возможное переполнение,
установив тип результата `int64`.
Установим нужные зависимости в 
виртуальном окружении. Сгенерируем
из protobuf код для взаимодействия 
клиента и сервера в `./server` и `./client`:
```
python -m grpc_tools.protoc -I ../protobufs --python_out=. \
         --grpc_python_out=. ../protobufs/service.proto
```
Реализуем оба требуемых метода. 
## Обработка ошибок 
Несмотря 
на встроенную валидацию *типов* в 
gRPC, валидировать *данные* всё равно 
необходимо. Добавим в серверную часть
обработку возможных ошибок. Будем проверять,
было ли передано имя для приветствия:
```python
if not request.name:
    context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Name required")
```
А также, присутствует ли переданный стиль приветствия
в словаре возможных стилей:
```python
if request.style not in greeting_by_style:
    context.abort(grpc.StatusCode.NOT_FOUND, "Style not found")
```
## Логирование
Для логирования, как и на семинаре, будем
использовать интерсепторы `grpc-interceptor`.
С помощью `ExceptionToStatusInterceptor`
можно также использовать
более красивый `raise` для обработки ошибок
вместо `context.abort`.

## Тестирование
Тестировать интерсепторы будем так же, 
как и на семинаре. А для тестирования других
функций воспользуемся [pytest-grpc](https://pypi.org/project/pytest-grpc/),
таким образом не возникнет необходимости
запускать сервер, чтобы провести 
юнит-тестирование.
Данный плагин предоставляет
фикстуру `grpc_channel`, а также 
требует следующей инфраструктуры:
```python
from service_pb2_grpc import GreetingAndSumStub

@pytest.fixture(scope='module')
def grpc_add_to_server():
    from service_pb2_grpc import add_GreetingAndSumServicer_to_server

    return add_GreetingAndSumServicer_to_server


@pytest.fixture(scope='module')
def grpc_servicer():
    from server.server import GreetingAndSumService
    return GreetingAndSumService()


@pytest.fixture(scope='module')
def grpc_stub(grpc_channel):
    return GreetingAndSumStub(grpc_channel)
```

## Контейнеризация сервиса с использованием Docker
Напишем докерфайлы для сервера и клиента.
Соберем докер-образы:
```
docker build . -f server/docker/Dockerfile -t server
docker build . -f client/docker/Dockerfile -t client
```
Создадим сеть, через которую сервер и клиент
смогут общаться:
```
docker network create microservices
```
Запустим контейнер сервера:
```
docker run -p 127.0.0.1:50051:50051/tcp --network microservices \
             --name server server
```
Запустим контейнер клиента, установив
адрес сервера через переменную окружения:
```
docker run --network microservices \
             -e SERVER_HOST=server client
```
Получим вывод в терминал - всё работает!
Напишем docker-compose.yml, чтобы каждый раз 
не создавать сеть, а запускать все одной 
командой `docker compose up`. 
Убедимся, что клиент может общаться с сервером
и в `github actions`, для этого будем 
проверять логи контейнеров:
```yml
  test-interaction:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run containers
        run: docker compose up -d
      - name: Fetch logs
        if: always()
        run: docker-compose logs
      - name: Stop and remove containers
        if: always()
        run: docker-compose down
```

## Развёртывание сервиса на Kubernetes
Опишем манифесты в директории `kubernetes`.
Так как используются локальные образы, 
нужно не забыть прописать `imagePullPolicy: Never`.
Из-за `CMD ["python", "client.py"]` в докерфайле
клиент сразу завершается при запуске контейнеров
в поде. Поэтому в манифест пропишем следующую 
стартовую команду:
```yml
command: ["sh", "-c", "python client.py; sleep infinity"]
```
Создадим кластер:
```
minikube start
```
Так как используем локальные образы, также
необходимо прописать команду:
```bash
eval $(minikube docker-env)
```
Соберем образы:
```
docker compose build server
docker compose build client
```
И применим манифесты:
```
kubectl apply -f k8s/kubernetes.yaml
```
Проверим, что все поды на месте:
```bash
$ kubectl get pods
NAME                      READY   STATUS    RESTARTS   AGE
client-7b658c4569-g5qs2   1/1     Running   0          91s
server-7478d79958-5f9p2   1/1     Running   0          91s
server-7478d79958-9zcwb   1/1     Running   0          91s
server-7478d79958-rgjlr   1/1     Running   0          91s
```
Зайдем в контейнер клиента и запустим в нем
`client.py`, чтобы удостовериться, что
он может обращаться к серверу:
```bash
$ kubectl exec -it client-7b658c4569-g5qs2 -- /bin/bash
root@client-7b658c4569-g5qs2:/service/client# python client.py
Good day, Amelia.
4294967294
root@client-7b658c4569-g5qs2:/service/client#
```
Получили ожидаемый вывод. Ура, всё работает!