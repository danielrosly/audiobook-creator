import yaml


class GlobalConfig:
    """
    Class with static data representing global configuration and methods that use it
    """
    _global_config = None
    _s3_created = False  # set to true if s3 has been created

    @staticmethod
    def read_global_config(file):
        """
        Reads global config from YAML file
        :param file: absolute or relative path
        """
        try:
            gl_conf = open(file, encoding='utf8')
            GlobalConfig._global_config = yaml.load(gl_conf, Loader=yaml.FullLoader)
        except FileNotFoundError as ex:
            from creatorTools.Exceptions import GlobalException
            raise GlobalException('Not able to open config file: {} '.format(file), ex)
        except yaml.YAMLError as ex:
            from creatorTools.Exceptions import GlobalException
            raise GlobalException('Not able to correctly parse config file: {} '.format(file), ex)

    @staticmethod
    def get_reading_object(text_to_read, mp3_no_name, hash_of_text, belongs_to_book):
        if GlobalConfig._global_config['reading_engine'] == 'aws polly':
            from creatorTools.Mp3FileFromAwsPolly import Mp3FileFromAwsPolly
            return Mp3FileFromAwsPolly(text_to_read, mp3_no_name, hash_of_text, belongs_to_book)
        elif GlobalConfig._global_config['reading_engine'] == 'google translate':
            from creatorTools.Mp3FileFromGoogleTranslate import Mp3FileFromGoogleTranslate
            return Mp3FileFromGoogleTranslate(text_to_read, mp3_no_name, hash_of_text, belongs_to_book)
        else:
            from creatorTools.Exceptions import GlobalException
            raise GlobalException(
                f'Not correct value for reading_engine parameter: {GlobalConfig._global_config["reading_engine"]}',
                None)

    @staticmethod
    def get_aws_region():
        return GlobalConfig._global_config['aws_region']

    @staticmethod
    def get_aws_key_id():
        return GlobalConfig._global_config['aws_access_key_id']

    @staticmethod
    def get_aws_access_key():
        return GlobalConfig._global_config['aws_secret_access_key']

    @staticmethod
    def get_s3_bucket():
        import re
        not_allowed = len(re.findall(r'[^\.^\-^a-z^0-9]', GlobalConfig._global_config['s3bucket']))
        if not_allowed == 0:
            return GlobalConfig._global_config['s3bucket']
        from creatorTools.Exceptions import GlobalException
        raise GlobalException('S3 bucket name contains not allowed characters.', None)

    @staticmethod
    def create_s3_bucket():
        # create bucket only if it doesn't exist
        if GlobalConfig._s3_created:
            return
        try:
            session = GlobalConfig.get_aws_session()
            s3 = session.resource('s3', config=GlobalConfig.get_aws_config())
            bucket = s3.Bucket(GlobalConfig.get_s3_bucket())
            if bucket not in s3.buckets.all():
                bucket.create(ACL='private',
                              CreateBucketConfiguration={'LocationConstraint': GlobalConfig.get_aws_region()})
        except Exception as ex:
            from creatorTools.Exceptions import GlobalException
            raise GlobalException('Error while creating bucket {}'
                                  .format(GlobalConfig.get_s3_bucket()), ex)
        GlobalConfig._s3_created = True

    @staticmethod
    def delete_s3_bucket():
        if not GlobalConfig._s3_created:
            return
        try:
            session = GlobalConfig.get_aws_session()
            s3 = session.resource('s3', config=GlobalConfig.get_aws_config())
            bucket = s3.Bucket(GlobalConfig.get_s3_bucket())
            bucket.objects.all().delete()
            bucket.delete()
        except Exception as ex:
            from creatorTools.Exceptions import GlobalException
            raise GlobalException('Error while deleting bucket {}'
                                  .format(GlobalConfig.get_s3_bucket()), ex)

    @staticmethod
    def get_audiobooks():
        return GlobalConfig._global_config['audiobooks']

    @staticmethod
    def get_aws_config():
        from botocore.config import Config
        return Config(
            region_name=GlobalConfig.get_aws_region(),
            signature_version='v4',
            retries={
                'max_attempts': 10,
                'mode': 'standard'
            }
        )

    @staticmethod
    def get_aws_session():
        from boto3 import Session
        return Session(
            aws_access_key_id=GlobalConfig.get_aws_key_id(),
            aws_secret_access_key=GlobalConfig.get_aws_access_key()
        )

    @staticmethod
    def get_max_sync_size():
        if GlobalConfig._global_config['reading_engine'] == 'aws polly':
            max_s = int(GlobalConfig._global_config['max_sync'])
            if max_s > 3000:
                from creatorTools.Exceptions import GlobalException
                raise GlobalException('Value of param max_sync cant be bigger than 3000.', None)
            return max_s
        elif GlobalConfig._global_config['reading_engine'] == 'google translate':
            import sys
            return sys.maxsize   # no limit

    @staticmethod
    def get_check_delay():
        return int(GlobalConfig._global_config['check_delay'])
