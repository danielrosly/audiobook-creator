import yaml
import hashlib


class FileHashes:
    """
    Class representing file with hashes of MP3 files
    """
    def __init__(self, file):
        """
        Constructor. Initializes field with name of file with hashes.
        :param file: absolute or relative path
        """
        self.hash_file = file
        self.hashes = None

    def read_file_hashes(self):
        try:
            hashes = open(self.hash_file, encoding='utf8')
            self.hashes = yaml.load(hashes, Loader=yaml.FullLoader)
        except FileNotFoundError:
            self.hashes = {}
        except yaml.YAMLError as ex:
            from creatorTools.Exceptions import BookException
            raise BookException('Not able to correctly parse hash file: {} '.format(self.hash_file), ex)

    def write_file_hashes(self):
        with open(self.hash_file, "w", encoding="utf-8") as text_file:
            text_file.write(yaml.dump(self.hashes))

    def is_hash_processable(self, only_name, curr_hash):
        """
        Checks if given hash is NOT equal to hash for given only_name.
        :param only_name: only name of file (without path and extension)
        :param curr_hash: current hash
        :return: true - either hash for this file exists and is NOT equal to parameter,
                        or entry for file does not exist at all
                false - entry for the file exists, and it is equal to parameter
        """
        if only_name in self.hashes:
            # existing key
            if self.hashes[only_name] != curr_hash:
                return True
            else:
                return False
        else:
            # new key
            return True

    def update_hash(self, only_name, new_hash):
        self.hashes[only_name] = new_hash

    @staticmethod
    def calc_hash(hashed_string):
        return hashlib.sha256(hashed_string.encode('cp1250')).hexdigest()
