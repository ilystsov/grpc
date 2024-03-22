import grpc
import pytest
import os
import sys
from grpc_interceptor.exceptions import NotFound, InvalidArgument


sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
)
from service_pb2 import (  # noqa: E402
    GreetingRequest,
    GreetingStyle,
    SumRequest,
)
from grpc_interceptor.testing import (  # noqa: E402
    dummy_client,
    DummyRequest,
    raises,
)
import server.server  # noqa: E402


class MockErrorLogger(server.server.ServerLogger):
    def __init__(self):
        self.logged_exception = None

    def log_error(self, e: Exception) -> None:
        self.logged_exception = e


def test_log_error():
    mock = MockErrorLogger()
    ex = Exception()
    special_cases = {"error": raises(ex)}

    with dummy_client(
        special_cases=special_cases, interceptors=[mock]
    ) as client:
        assert client.Execute(DummyRequest(input="foo")).output == "foo"
        assert mock.logged_exception is None

        with pytest.raises(grpc.RpcError):
            client.Execute(DummyRequest(input="error"))
        assert mock.logged_exception is ex


@pytest.mark.parametrize(
    "name, style, expected_message",
    [
        ("Mads", GreetingStyle.FORMAL, "Good day, Mads."),
        ("Amelia", GreetingStyle.INFORMAL, "Hey, Amelia!"),
    ],
)
def test_GreetPerson(name, style, expected_message):
    request = GreetingRequest(name=name, style=style)
    response = server.server.GreetingAndSumService().GreetPerson(request, None)
    assert response.greeting_message == expected_message


@pytest.mark.parametrize(
    "name, style, exception, expected_details",
    [
        ("", GreetingStyle.FORMAL, InvalidArgument, "Name required"),
        ("Amelia", 42, NotFound, "Style not found"),
    ],
)
def test_GreetPerson_exception(name, style, exception, expected_details):
    request = GreetingRequest(name=name, style=style)
    with pytest.raises(exception) as e:
        server.server.GreetingAndSumService().GreetPerson(request, None)
    assert expected_details in str(e)


def test_AddTwoNumbers():
    request = SumRequest(first_number=100, second_number=-14)
    response = server.server.GreetingAndSumService().AddTwoNumbers(
        request, None
    )
    assert response.result == 86
