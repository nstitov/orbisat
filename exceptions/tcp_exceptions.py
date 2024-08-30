class TCPServerResponseError(Exception):
    def __init__(self, function_name: str):
        self.function_name = function_name
        super().__init__(f"Error response when calling {function_name}.")


class TCPServerUnexpectedResponseError(Exception):
    def __init__(self, function_name: str):
        self.request_name = function_name
        super().__init__(f"Unexpected response when calling {function_name}.")


class TCPServerBodyRequestError(Exception):
    def __init__(self, request_name: str):
        self.request_name = request_name
        super().__init__(f"No body in {request_name} request.")
