import os
import re
import time

from gtts.tokenizer import Tokenizer, tokenizer_cases
from pydub import AudioSegment
import gtts

from creatorTools.Exceptions import Mp3Exception
from creatorTools.Mp3File import Mp3File


class Mp3FileFromGoogleTranslate(Mp3File):
    """
    Class representing MP3 file.
    It does all operations on it.
    It uses Google Translate API as tool to read text
    """

    def __init__(self, text_to_read, mp3_no_name, hash_of_text, belongs_to_book):
        """
        Initializes structures with data
        :param text_to_read: raw text to be read to MP3
        :param mp3_no_name: list consisting of two strings: number of file and filename(with mp3 extension)
        :param hash_of_text: hash of text to be read calculated before
        :param belongs_to_book: object BookFiles that contains information about book MP3 belongs to
        """
        super().__init__(text_to_read, hash_of_text, belongs_to_book)
        self.tran_text = {}  # map of three-element arrays: {id: [lang, text, [full_path1, full_path1, ...]]}
        self.file_no = mp3_no_name[0]
        self.file_tile = mp3_no_name[1].split('.')[0]  # only name of file, no number and no extension
        self.file_name = mp3_no_name[0] + '-' + mp3_no_name[1]  # filename of mp3 file
        self.def_lang = self.book.get_default_language().upper()

    def encode_to_required_format(self):
        """
        Encodes text to format required by google translate.
        :return: length of encoded text, or exception if failure (i.e. wrong syntax)
        """
        # counting signs @ - there must be even number of them
        no_of_sections = len(re.findall(Languages.get_regex_lang(), self.raw_text))
        no_of_marks = len(re.findall('@', self.raw_text))
        if no_of_marks != no_of_sections * 2:
            from creatorTools.Exceptions import BookException
            raise BookException('Syntax error(not matching @) in text of book for file: {} '.format(self.file_name),
                                None)
        # constructing tran_text map
        file_list = self.raw_text.replace('===', '').split('@')
        file_no = 1
        for fragment in file_list:
            if re.match('.*\\w.*', fragment):
                lang_found = None
                final_text = ''
                for lang in Languages.get_lang_tab():
                    if fragment.startswith(lang):
                        lang_found = lang
                        final_text = fragment[3:]
                        break
                if lang_found is None:
                    lang_found = self.def_lang
                    final_text = fragment
                self.tran_text[file_no] = [str(lang_found), str(final_text), None]
                file_no += 1
        return 0  # size of text is not important

    def save_mp3(self):
        import tempfile
        tempdir = tempfile.mkdtemp(prefix="audiobookreader-")
        tr_exc = None
        output = None
        try:
            for fragment_no in self.tran_text.keys():
                self._transcode(tempdir, fragment_no)
            # concatenating MP3 files
            playlist_songs = []
            for fragment_no in sorted(self.tran_text.keys()):
                for fragm_part_no in self.tran_text[fragment_no][2]:
                    playlist_songs.append(AudioSegment.from_mp3(fragm_part_no))
            first_song = playlist_songs.pop(0)
            playlist = first_song
            for song in playlist_songs:
                playlist = playlist.append(song)
            if not os.path.isdir(self.book.get_result_dir()):
                os.mkdir(self.book.get_result_dir())
            output = os.path.join(self.book.get_result_dir(), self.file_name)
            playlist.export(output, format='mp3')
        except Exception as ex:
            tr_exc = ex
        finally:
            import shutil
            shutil.rmtree(tempdir)
            if tr_exc is not None:
                raise tr_exc
        # save ID3 and hash
        self._save_metadata(output)

    def schedule_mp3_generation(self):
        from creatorTools.Exceptions import GlobalException
        raise GlobalException('Scheduling async generation not supported for Google Translate.', None)

    def check_save_task(self):
        from creatorTools.Exceptions import GlobalException
        raise GlobalException('Async generation not supported for Google Translate.', None)

    def _transcode(self, directory, fragment_id):
        full_name = os.path.join(directory, "voice" + "{:0>4d}".format(fragment_id))
        # preparing list of divided parts of text
        raw_text = re.sub(r' +', ' ', self.tran_text[fragment_id][1].strip())
        toke_list = Tokenizer([
            tokenizer_cases.colon,
            tokenizer_cases.period_comma,
            tokenizer_cases.other_punctuation]).run(raw_text)
        final_text = []
        for toke in toke_list:
            tmp_tok = toke.strip()
            if any(c.isalpha() for c in tmp_tok):   # token must contain at least one letter to read
                while len(tmp_tok) > 100:
                    space_pos = toke.find(' ', 60)
                    if space_pos == -1:
                        raise Mp3Exception('String \'{}\' is longer than 100 characters '
                                           'and contains no dot, colon or space do divide it.'.format(tmp_tok), None)
                    if space_pos > 100:
                        raise Mp3Exception('String \'{}\' is longer than 100 characters and contains '
                                           'no space do divide it in first 100 characters.'.format(tmp_tok), None)
                    final_text.append(tmp_tok[:space_pos].strip())
                    tmp_tok = tmp_tok[space_pos:]
                if tmp_tok.strip() != '':
                    final_text.append(tmp_tok)
        # processing all fragments of text
        frag_count = 1
        self.tran_text[fragment_id][2] = []
        for final_frag in final_text:
            counter = 10
            converted = False
            while counter > 0 and not converted:
                try:
                    tts = gtts.gTTS(text=final_frag, lang=Languages.get_google_lang(self.tran_text[fragment_id][0]))
                    save_name = full_name + "_{:0>4d}.mp3".format(frag_count)
                    tts.save(save_name)
                    self.tran_text[fragment_id][2].append(save_name)
                    converted = True
                    frag_count += 1
                except Exception as exc:
                    print(exc)
                    exit(1)
                    counter -= 1
                    if counter > 0:
                        print("Error in converting returned by Google. Repeats remaining " + str(counter))
                        time.sleep(1 + 22 / counter)
                    else:
                        raise Mp3Exception('Failed to get sound from Google Translate.', exc)
            if not converted:
                raise Mp3Exception('Unknown error during converting data by Google - 10 attempts failed.', None)


class Languages:
    @staticmethod
    def get_regex_lang():
        return r'@(PL|ENG|US|GER|FR|ES|IT)[^@]*@'

    @staticmethod
    def get_lang_tab():
        return ['PL', 'ENG', 'US', 'GER', 'FR', 'ES', 'IT']

    @staticmethod
    def get_google_lang(lang):
        langs = {'PL': 'pl', 'ENG': 'en-GB', 'US': 'en', 'GER': 'de', 'FR': 'fr', 'ES': 'es', 'IT': 'it'}
        return langs[lang]
