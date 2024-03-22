from typing import Callable, Any

import grpc
import os

from grpc_interceptor import ClientInterceptor

from service_pb2 import GreetingRequest, GreetingStyle, SumRequest
from service_pb2_grpc import GreetingAndSumStub
import logging

logging.basicConfig(
    filename="client.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class ClientLogger(ClientInterceptor):
    def intercept(
        self,
        method: Callable,
        request_or_iterator: Any,
        call_details: grpc.ClientCallDetails,
    ) -> Any:
        self.log_request(call_details)
        response = method(request_or_iterator, call_details)
        self.log_response(call_details)
        return response

    def log_request(self, call_details: grpc.ClientCallDetails):
        logging.info(f"Client called method: {call_details.method}")

    def log_response(self, call_details: grpc.ClientCallDetails):
        logging.info(f"Client received response to: {call_details.method}")


server_host = os.getenv("SERVER_HOST", "localhost")
server_channel = grpc.insecure_channel(f"{server_host}:50051")
intercepted_channel = grpc.intercept_channel(server_channel, ClientLogger())
greeting_and_sum_client = GreetingAndSumStub(intercepted_channel)


class ServerError(Exception):
    pass


def greet_person(name: str, style: GreetingStyle) -> str | None:
    try:
        greeting_request = GreetingRequest(name=name, style=style)
        greeting_response = greeting_and_sum_client.GreetPerson(
            greeting_request
        )
    except grpc.RpcError as e:
        raise ServerError(f"gRPC error occurred: {e.details()}") from e
    return greeting_response.greeting_message


def add_two_numbers(first_number: int, second_number: int) -> int | None:
    try:
        sum_request = SumRequest(
            first_number=first_number, second_number=second_number
        )
        sum_response = greeting_and_sum_client.AddTwoNumbers(sum_request)
    except grpc.RpcError as e:
        raise ServerError(f"gRPC error occurred: {e.details()}") from e
    return sum_response.result


if __name__ == "__main__":
    try:
        greeting = greet_person("Amelia", GreetingStyle.FORMAL)
        print(greeting)
    except ServerError as e:
        print(e)

    try:
        result = add_two_numbers(2147483647, 2147483647)
        print(result)
    except ServerError as e:
        print(e)
