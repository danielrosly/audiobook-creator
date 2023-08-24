from creatorTools.GlobalConfig import GlobalConfig
import os
import re
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing
from creatorTools.Mp3File import Mp3File
from creatorTools.ReaderLog import ReaderLog


class Mp3FileFromAwsPolly(Mp3File):
    """
    Class representing MP3 file.
    Doing all operations on it.
    It uses https://docs.aws.amazon.com/polly/latest/dg/StartSpeechSynthesisTaskSamplePython.html
    as method 'synthesize_speech' has upper limit of 3000 characters
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
        self.polly_text = text_to_read
        self.file_no = mp3_no_name[0]
        self.file_tile = mp3_no_name[1].split('.')[0]  # only name of file, no number and no extension
        self.file_name = mp3_no_name[0] + '-' + mp3_no_name[1]  # filename of mp3 file
        self.def_voice = Languages.get_voice(self.book.get_default_language().upper())
        self.task_id = None     # task id for Polly is kept here if asynchronous generation is used

    def encode_to_required_format(self):
        """
        Encodes text to format required by polly engine.
        :return: length of encoded text, or exception if failure (i.e. wrong syntax)
        """
        # counting signs @ - there must be even number of them
        no_of_sections = len(re.findall(Languages.get_regex_lang(), self.raw_text))
        no_of_marks = len(re.findall('@', self.raw_text))
        if no_of_marks != no_of_sections * 2:
            from creatorTools.Exceptions import BookException
            raise BookException('Syntax error(not matching @) in text of book for file: {} '.format(self.file_name),
                                None)
        # replacing names of section with strings required by polly
        for lang, p_code in Languages.table_of_languages().items():
            polly_beginning = re.sub('XX', p_code, '<lang xml:lang="XX">')
            self.polly_text = re.sub('@{}'.format(lang.upper()), polly_beginning, self.polly_text)
        # ends are the same everywhere
        polly_end = '</lang>'
        self.polly_text = re.sub(r'@[^a-z^A-Z]', polly_end, self.polly_text)
        self.polly_text = '<speak>' + self.polly_text + '</speak>'
        remains = re.search('@', self.polly_text)
        if remains is not None:
            from creatorTools.Exceptions import BookException
            start_pos = remains.span()[0]
            end_pos = min(len(self.polly_text), start_pos + 6)
            raise BookException('Syntax error(string: {}) in text of book for file: {} '
                                .format(self.polly_text[start_pos:end_pos], self.file_name), None)
        return len(self.polly_text)

    def save_mp3(self):
        """
        Encodes text to mp3. Uses synchronous method that has upper limit of converting 3000 characters.
        :return: nothing
        """
        session = GlobalConfig.get_aws_session()
        polly = session.client("polly", config=GlobalConfig.get_aws_config())
        try:
            # Request speech synthesis
            response = polly.synthesize_speech(Text=self.polly_text, OutputFormat="mp3",
                                               VoiceId=self.def_voice, TextType='ssml')
        except (BotoCoreError, ClientError) as error:
            from creatorTools.Exceptions import Mp3Exception
            raise Mp3Exception('Error from AWS while generating MP3 file: {} '.format(self.file_name), error)

        # Access the audio stream from the response
        if "AudioStream" in response:
            if not os.path.isdir(self.book.get_result_dir()):
                os.mkdir(self.book.get_result_dir())
            # Note: Closing the stream is important because the service throttles on the
            # number of parallel connections. Here we are using contextlib.closing to
            # ensure the close method of the stream object will be called automatically
            # at the end of the with statement's scope.
            with closing(response["AudioStream"]) as stream:
                output = os.path.join(self.book.get_result_dir(), self.file_name)
                try:
                    # Open a file for writing the output as a binary stream
                    with open(output, "wb") as file:
                        file.write(stream.read())
                except IOError as error:
                    from creatorTools.Exceptions import Mp3Exception
                    raise Mp3Exception('Not able to write MP3 file: {} '.format(self.file_name), error)
                ReaderLog.log_inline('saved: {} ... '.format(output))
        else:
            from creatorTools.Exceptions import Mp3Exception
            raise Mp3Exception('The response for generating {} didnt contain audio data'.format(self.file_name), None)
        self._save_metadata(output)

    def schedule_mp3_generation(self):
        """
        Schedules asynchronous generation of mp3 file.
        File is generated as: https://s3.eu-west-1.amazonaws.com/<BUCKET>/<TaskId>.mp3
        :return: id of task returned by start_speech_synthesis_task
        """
        session = GlobalConfig.get_aws_session()
        polly = session.client("polly", config=GlobalConfig.get_aws_config())
        try:
            # Request speech synthesis
            GlobalConfig.create_s3_bucket()
            response = polly.start_speech_synthesis_task(Text=self.polly_text, OutputFormat="mp3",
                                                         VoiceId=self.def_voice, TextType='ssml',
                                                         OutputS3BucketName=GlobalConfig.get_s3_bucket())
        except (BotoCoreError, ClientError) as error:
            from creatorTools.Exceptions import Mp3Exception
            raise Mp3Exception('Error from AWS while generating MP3 file: {} '.format(self.file_name), error)
        try:
            task_id = response['SynthesisTask']['TaskId']
        except Exception as error:
            from creatorTools.Exceptions import Mp3Exception
            raise Mp3Exception('Error from AWS while getting id for task for: {} '.format(self.file_name), error)
        self.task_id = task_id
        ReaderLog.log_inline('scheduled task: {} ... '.format(task_id))

    def check_save_task(self):
        """
        Checks if given task is finished and eventually downloads mp3 file
        :return: true if all is ok, and file is saved, false if file is not ready yet, throws exception
        """
        session = GlobalConfig.get_aws_session()
        polly = session.client("polly", config=GlobalConfig.get_aws_config())
        task_status = polly.get_speech_synthesis_task(TaskId=self.task_id)
        status = task_status['SynthesisTask']['TaskStatus']
        if status == 'failed':
            from creatorTools.Exceptions import Mp3Exception
            raise Mp3Exception('Status failed returned by AWS while batch generating MP3 file: {} Reason is: {}'
                               .format(self.file_name, task_status['SynthesisTask']['TaskStatusReason']), None)
        if status == 'scheduled' or status == 'inProgress':
            return False
        if status == 'completed':
            output = os.path.join(self.book.get_result_dir(), self.file_name)
            try:
                s3_client = session.client('s3', config=GlobalConfig.get_aws_config())
                s3_client.download_file(GlobalConfig.get_s3_bucket(), self.task_id+'.mp3', output)
                ReaderLog.log('Downloaded file: {} ... '.format(output))
            except Exception as ex:
                from creatorTools.Exceptions import Mp3Exception
                raise Mp3Exception('Error while downloading file {} from AWS S3 bucket {} key {}'
                                   .format(self.file_name, GlobalConfig.get_s3_bucket(), self.task_id+'.mp3'), ex)
            self._save_metadata(output)
            self.task_id = None
            return True
        from creatorTools.Exceptions import Mp3Exception
        raise Mp3Exception('Unknown status {} returned by AWS while batch generating MP3 file: {} '
                           .format(status, self.file_name), None)


class Languages:
    """"
    class translates codes of languages used in 'book' file to language codes used by polly:
    https://docs.aws.amazon.com/polly/latest/dg/voicelist.html
    """

    @staticmethod
    def table_of_languages():
        return {'PL': 'pl-PL', 'ENG': 'en-GB', 'US': 'en-US',
                'GER': 'de-DE', 'FR': 'fr-FR', 'ES': 'es-ES',
                'IT': 'it-IT'}

    @staticmethod
    def get_voice(lang_code):
        voices = {'PL': 'Jacek', 'ENG': 'Brian', 'US': 'Joey',
                  'GER': 'Hans', 'FR': 'Mathieu', 'ES': 'Miguel',
                  'IT': 'Giorgio'}
        return voices[lang_code]

    @staticmethod
    def get_regex_lang():
        return r'@(PL|ENG|US|GER|FR|ES|IT)[^@]*@'

    @staticmethod
    def supported_languages():
        return 'PL ENG US GER FR ES IT'
