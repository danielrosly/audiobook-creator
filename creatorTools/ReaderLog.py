import sys


class ReaderLog:

    _new_line = True

    @staticmethod
    def log(message):
        if not ReaderLog._new_line:
            print('')
        print(message)
        ReaderLog._new_line = True

    @staticmethod
    def log_par(message):
        if not ReaderLog._new_line:
            print('')
        print('')
        print(message)
        ReaderLog._new_line = True

    @staticmethod
    def log_inline(message):
        if not ReaderLog._new_line:
            print('')
        print(message, end='')
        sys.stdout.flush()
        ReaderLog._new_line = True

    @staticmethod
    def progress(message):
        sys.stdout.write("\r")
        sys.stdout.flush()
        sys.stdout.write(message)
        sys.stdout.flush()
        ReaderLog._new_line = False
