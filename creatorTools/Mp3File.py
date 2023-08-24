# Pseudo-abstract class inherited by different ways of generating Mp3 file

from abc import ABC, abstractmethod


class Mp3File(ABC):

    def __init__(self, text_to_read, hash_of_text, belongs_to_book):
        self.book = None
        self.raw_text = text_to_read
        self.raw_text_hash = hash_of_text
        self.file_no = None
        self.file_name = None
        self.file_tile = None
        self.book = belongs_to_book

    @abstractmethod
    def encode_to_required_format(self):
        pass

    @abstractmethod
    def save_mp3(self):
        pass

    @abstractmethod
    def schedule_mp3_generation(self):
        pass

    @abstractmethod
    def check_save_task(self):
        pass

    def _save_metadata(self, full_path):
        # set proper values to MP3 tags
        try:
            from mutagen.mp3 import MP3
            from mutagen.easyid3 import EasyID3
            mp3 = MP3(full_path, ID3=EasyID3)
            mp3['album'] = self.book.get_mp3_tag('Album')
            mp3['artist'] = self.book.get_mp3_tag('Artist')
            mp3['albumartist'] = self.book.get_mp3_tag('AlbumArtist')
            mp3['tracknumber'] = self.file_no
            mp3['title'] = self.file_tile.replace('_', ' ').title()
            mp3['date'] = self.book.get_mp3_tag('AlbumDate')
            mp3.save()
        except Exception as ex:
            from creatorTools.Exceptions import Mp3Exception
            raise Mp3Exception('Updating ID3 tags for file {} failed.'.format(self.file_name), ex)
        # save hash
        self.book.update_and_save_hashes(self.file_tile, self.raw_text_hash)
