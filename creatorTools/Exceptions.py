# Exception for application itself and processing files
from creatorTools.ReaderLog import ReaderLog


class ReaderException(Exception):
    def __init__(self, error_message, causing_exception):
        super().__init__(error_message)
        self.message = error_message
        self.cause = causing_exception

    def print_error_message(self):
        ReaderLog.log('[ERROR] {}'.format(self.message))

    def print_details(self):
        if self.cause is not None:
            ReaderLog.log('Details:')
            ReaderLog.log(self.cause)


class GlobalException(ReaderException):
    """
    Exception for global things
    """
    def print_error_message(self):
        ReaderLog.log('[ERROR] Error in global processing:')
        super().print_error_message()


class BookException(ReaderException):
    """
    Exception for processing book
    """
    def print_error_message(self):
        ReaderLog.log('[ERROR] Error in processing book:')
        super().print_error_message()


class Mp3Exception(ReaderException):
    """
    Exception for processing mp3
    """
    def print_error_message(self):
        ReaderLog.log('[ERROR] Error in processing mp3:')
        super().print_error_message()
