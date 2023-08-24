import os

from creatorTools.FileHashes import FileHashes
from creatorTools.GlobalConfig import GlobalConfig
from creatorTools.Mp3FileFromAwsPolly import Mp3FileFromAwsPolly
from creatorTools.ReaderLog import ReaderLog


class BookFiles:
    """
    Class representing Book with text to be read.
    Book consists of three things:
        *.book file with text. Text file that is converted should be in UTF-8 encoding.
        *.hsh file with map of hashes for partial files.
        *.yaml file describing configuration of Book.
    """

    def __init__(self, yaml_path):
        """
        Reads path to yaml file that keeps all parameters about Book.
        Initializes all main variables.
        :param yaml_path: absolute or relative path
        """
        self.yaml_file = yaml_path
        a_yaml_file = open(self.yaml_file, encoding='utf8')
        import yaml
        self.yaml_config = yaml.load(a_yaml_file, Loader=yaml.FullLoader)
        self.file_hashes = FileHashes(self.yaml_config['HashFile'])
        self.file_hashes.read_file_hashes()
        # divide text into parts that will represent individual MP3s.
        try:
            self.file_texts = open(self.yaml_config['BookFile'], encoding='utf8').read().replace("\n", "  ").split('@@')
        except OSError as ex:
            from creatorTools.Exceptions import BookException
            raise BookException('Cant open for reading file containing text of book: {} '
                                .format(self.yaml_config['BookFile']), ex)
        self.mp3_map = {}
        self.mp3_all_present = []
        self.errors_in_async = False    # set to True if in any async generation errors were present

    def parse_book_file(self):
        for file_text in self.file_texts:
            # if section part representing MP3 is empty
            if len(file_text) == 0:
                continue
            # we split by first @ - before it there is name of MP3 file
            struct = file_text.split('@', 1)
            if len(struct) < 2:
                continue
            filename = struct[0]
            only_name = filename.split('-')
            curr_hash = FileHashes.calc_hash(file_text)
            if self.file_hashes.is_hash_processable(only_name[1].split('.')[0], curr_hash):
                # mp3 file is processable - hash of text is different from one from previous (existing mp3) version.
                # params: text to read, table [num,filename with extension], hash of text, this object
                # here we select proper class to generate data - depending on configuration
                self.mp3_map[only_name[1]] = GlobalConfig.get_reading_object(struct[1], only_name, curr_hash, self)
            # add all present mp3 files to check dir later
            self.mp3_all_present.append(filename)

    def print_generated(self):
        ReaderLog.log_inline('Files to be regenerated:')
        if len(self.mp3_map) == 0:
            ReaderLog.log(' none')
            return
        for file in self.mp3_map.keys():
            print(' ', end='')
            print(file, end='')
        print('')

    def generate_mp3(self):
        async_gen = False
        for mp3 in self.mp3_map.values():
            ReaderLog.log_inline('Processing: {} ... '.format(mp3.file_tile))
            size = mp3.encode_to_required_format()
            if size <= GlobalConfig.get_max_sync_size():
                # converting on-the-fly
                ReaderLog.log_inline('generating and saving file ... ')
                mp3.save_mp3()
                ReaderLog.log('finished.')
            else:
                # asynchronous generation
                async_gen = True
                mp3.schedule_mp3_generation()
                ReaderLog.log('started asynchronous generation. ')
        return async_gen

    def check_async_gen(self):
        """
        Checks status of offline mp3 generation
        :return: true if all files were generated and downloaded, or if no files to generate
        """
        all_generated = True
        for mp3 in self.mp3_map.values():
            if mp3.task_id is not None:
                # async generation
                from creatorTools.Exceptions import ReaderException
                try:
                    tmp_res = mp3.check_save_task()
                    all_generated = all_generated and tmp_res
                except ReaderException as error:
                    error.print_error_message()
                    mp3.task_id = None  # error occurred - we will ignore this task anyway
                    self.errors_in_async = True
        return all_generated

    def clear_book_dir(self):
        # remove those files that are not present in book text anymore
        list_dir = os.listdir(self.get_result_dir())
        for file in list_dir:
            if '.mp3' in file.lower() and file not in self.mp3_all_present:
                ReaderLog.log('Removing not used file {} from {}'.format(file, self.get_result_dir()))
                os.remove(os.path.join(self.get_result_dir(), file))

    def update_and_save_hashes(self, only_name, new_hash):
        # write file after each successful conversion
        self.file_hashes.update_hash(only_name, new_hash)
        self.file_hashes.write_file_hashes()

    def get_default_language(self):
        return self.yaml_config['MainLanguage']

    def get_result_dir(self):
        return self.yaml_config['ResultDir']

    def get_mp3_tag(self, tag_name):
        return self.yaml_config[tag_name]
