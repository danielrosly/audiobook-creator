import sys
import time
import traceback

from creatorTools.BookFiles import BookFiles
from creatorTools.Exceptions import ReaderException
from creatorTools.GlobalConfig import GlobalConfig
from creatorTools.Mp3FileFromAwsPolly import Languages
from creatorTools.ReaderLog import ReaderLog


if len(sys.argv) != 2:
    print('Number of arguments:', len(sys.argv), ' is different than one.')
    print('Provide path to YAML as parameter. YAML should contain configuration of audiobook(s).')
    print('Text files that is converted should be in UTF-8 encoding.')
    print('Supported languages (both default and embedded with sign @): ' + Languages.supported_languages())
    exit(0)

print('Processing config: ', sys.argv[1])
try:
    GlobalConfig.read_global_config(sys.argv[1])
    async_list = []
    for book_config in GlobalConfig.get_audiobooks():
        ReaderLog.log_par('Processing audiobook defined in file {}'.format(book_config))
        book = BookFiles(book_config)
        book.parse_book_file()
        book.print_generated()
        if book.generate_mp3():
            async_list.append(book)
        book.clear_book_dir()
    # if there were async gen tasks
    if len(async_list) > 0:
        ReaderLog.log_par('Waiting for generation of files.')
        errors_present = False
        finished = True
        a_list_size = len(async_list)
        waiting = 0
        waiting_step = GlobalConfig.get_check_delay()
        while True:
            s_tmp = []
            ReaderLog.progress("Waiting " + str(waiting) + " seconds. Still " +
                               str(len(async_list)) + '/' + str(a_list_size) + " books to process.  ")
            for book in async_list:
                tmp_res = book.check_async_gen()
                finished = finished and tmp_res
                errors_present = errors_present or book.errors_in_async
                if not tmp_res:
                    # still mp3 to generate - book will be checked next time
                    s_tmp.append(book)
            if finished:
                break
            else:
                async_list = s_tmp
                finished = True
                time.sleep(waiting_step)
                waiting += waiting_step
        if not errors_present:
            ReaderLog.log('finished.')
        else:
            ReaderLog.log('finished with ERRORS. See log above.')
        GlobalConfig.delete_s3_bucket()
except ReaderException as ex:
    ReaderLog.log_par('==========================================================================')
    ex.print_error_message()
    ReaderLog.log('==========================================================================')
    ex.print_details()
    sys.exit(1)
except Exception:
    ReaderLog.log_par('==========================================================================')
    ReaderLog.log('[ERROR] Unhandled exception. Details below.')
    ReaderLog.log('==========================================================================')
    ReaderLog.log('Details:')
    sys.stdout.flush()
    traceback.print_exc(file=sys.stdout)
    sys.exit(10)
