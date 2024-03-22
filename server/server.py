from concurrent import futures
from signal import signal, SIGTERM
from typing import Callable, Any

import grpc
from grpc_interceptor.exceptions import NotFound, InvalidArgument

from service_pb2_grpc import (
    GreetingAndSumServicer,
    add_GreetingAndSumServicer_to_server,
)
from service_pb2 import (
    GreetingRequest,
    GreetingResponse,
    SumRequest,
    SumResponse,
    GreetingStyle,
)
from grpc_interceptor import ServerInterceptor, ExceptionToStatusInterceptor
import logging

logging.basicConfig(
    filename="server.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

greeting_by_style = {
    GreetingStyle.INFORMAL: "Hey, {}!",
    GreetingStyle.FORMAL: "Good day, {}.",
}


class ServerLogger(ServerInterceptor):
    def intercept(
        self,
        method: Callable,
        request: Any,
        context: grpc.ServicerContext,
        method_name: str,
    ) -> Any:
        try:
            self.log_request(method_name, request)
            response = method(request, context)
            self.log_response(method_name)
            return response
        except Exception as e:
            self.log_error(e)
            raise

    def log_error(self, e: Exception) -> None:
        logging.error(f"Exception occurred: {e}", exc_info=True)

    def log_request(self, method_name: str, request: Any) -> None:
        logging.info(f"Server received request: {method_name}, with {request}")

    def log_response(self, method_name: str) -> None:
        logging.info(f"Server responded to: {method_name}")


class GreetingAndSumService(GreetingAndSumServicer):
    def GreetPerson(
        self, request: GreetingRequest, context
    ) -> GreetingResponse:
        if request.style not in greeting_by_style:
            raise NotFound("Style not found")

        if not request.name:
            raise InvalidArgument("Name required")

        greeting = greeting_by_style[request.style].format(request.name)
        return GreetingResponse(greeting_message=greeting)

    def AddTwoNumbers(self, request: SumRequest, context) -> SumResponse:
        result = request.first_number + request.second_number
        return SumResponse(result=result)


def serve():
    interceptors = [ExceptionToStatusInterceptor(), ServerLogger()]

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=3), interceptors=interceptors
    )
    add_GreetingAndSumServicer_to_server(GreetingAndSumService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()

    def handle_sigterm(*_) -> None:
        print("Received shutdown signal")
        all_rpcs_done_event = server.stop(30)
        all_rpcs_done_event.wait(30)
        print("Shut down gracefully")

    signal(SIGTERM, handle_sigterm)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
