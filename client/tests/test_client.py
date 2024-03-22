import pytest
import os
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
)
from service_pb2 import GreetingStyle               # noqa: E402
from service_pb2_grpc import GreetingAndSumStub     # noqa: E402
import client.client                                # noqa: E402


@pytest.fixture(scope="module")
def grpc_add_to_server():
    from service_pb2_grpc import add_GreetingAndSumServicer_to_server

    return add_GreetingAndSumServicer_to_server


@pytest.fixture(scope="module")
def grpc_servicer():
    from server.server import GreetingAndSumService

    return GreetingAndSumService()


@pytest.fixture(scope="module")
def grpc_stub(grpc_channel):
    return GreetingAndSumStub(grpc_channel)


@pytest.mark.parametrize(
    "name, style, expected_message",
    [
        ("Mads", GreetingStyle.FORMAL, "Good day, Mads."),
        ("Amelia", GreetingStyle.INFORMAL, "Hey, Amelia!"),
    ],
)
def test_greet_person(monkeypatch, grpc_stub, name, style, expected_message):
    monkeypatch.setattr("client.client.greeting_and_sum_client", grpc_stub)
    response = client.client.greet_person(name, style)
    assert response == expected_message


@pytest.mark.parametrize(
    "name, style",
    [
        ("", GreetingStyle.FORMAL),
        ("Amelia", 42),
    ],
)
def test_greet_person_exception(monkeypatch, grpc_stub, name, style):
    monkeypatch.setattr("client.client.greeting_and_sum_client", grpc_stub)
    with pytest.raises(client.client.ServerError) as excinfo:
        client.client.greet_person(name, style)
    assert "gRPC error occurred:" in str(excinfo.value)


def test_add_two_numbers(monkeypatch, grpc_stub):
    monkeypatch.setattr("client.client.greeting_and_sum_client", grpc_stub)
    response = client.client.add_two_numbers(2147483647, 2147483647)
    assert response == 4294967294
