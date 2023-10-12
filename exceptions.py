class HTTPRequestError(Exception):
    def __init__(self, response):
        message = (f'Error {response.status_code}]')
        super().__init__(message)


class ParseStatusError(Exception):
    def __init__(self, homework_status):
        message = (
            (f'Unknown work status: {homework_status}')
        )
        super().__init__(message)
