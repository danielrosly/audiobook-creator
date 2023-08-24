# audiobook-creator

## Application that generates multi-language audiobooks

It uses AWS Polly or Google Translate to read texts from files and generate MP3s files collected into sets representing audiobooks.
So, when use Polly, AWS account is needed to use the program. Free tier should be sufficient for smaller files.
Documents for reading by application can be prepared in such way, that they use different languages and even mix them.

Supported languages for Polly: PL | ENG | US | GER | FR | ES | IT

Supported languages for Google Translate:  PL | ENG | US | GER | FR | ES | IT

### Two definitions 

**Audiobook** - set of MP3 files located in one directory, sharing name of album, artist and album date. Created out of one `book` file.
**MP3 file** - part of audiobook. Has individual title and number, the rest of tags is inherited from audiobook. Is represented by one section between double monkeys @ in `book` file.

### Input data

**Example input data are shown in tests directory.**
+ Main configuration is stored in `config.yaml` file. 
  + It contains global configuration and references to one or more audiobooks to create.
  + AWS account configuration data is located here, so keep it secret, keep it safe.
+ Each of files `fist.yaml` and `second.yaml` contains configuration of one audiobook that consists of many mp3 files.
+ Each of files `first_audiobook.book` and `second_audiobook.book` contain audiobook definition - text that is read. 
  + **Document must be properly formatted. Formatting sign is either one or two monkeys `@`**.
  + Second section of `first_audiobook.book` contains detailed information about format of `book` files.
  + These files should use UTF-8.
+ Directories `first` and `second` contain generated audiobook mp3 data.
+ Paths inside files can be either absolute of relative (should be to directory where program is started). 
+ Program generates files `*.hsh` in selected locations. These files keep hash data generated for sections of texts in `book` files. They allow to avoid regenerating non-changed text.

### Configuration inside application

There are files `Mp3FileFromAwsPolly.py` and `Mp3FileFromGoogleTranslate.py` that contain classes `Languages` that contain list of supported languages for each reading tool. Lists can be easily extended.

### How to run the program

Steps:
+ Installation of Python 3.10 is required.
+ Create virtual environment using `venv.cmd`
+ Prepare and fill-in your own set of configuration files.
  + If you plan to use Polly, provide AWS configuration data.
+ Prepare document to read. See `first_audiobook.book` for example and description of format.
+ Run the program using `run.cmd` and path to main config file (the one like `config.yaml` in example)
+ Program will generate MP3s. It will also create `hsh` files. If you delete them, next time program will recreate all mp3 files.

## Additional resources

Directory `resources` contains formatting file for documents having `book` format for Notepad++.
