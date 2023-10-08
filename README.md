# PGStorageLogger
## What is it?
Like python logger, but partitioned PostgreSQL tables are used for saving.

## How to setup?
1. pip install --user pgstoragelogger

Or You can setup manually:
1. Download pgstoragelogger.py
2. pip3 install requirements.txt
3. import pgstoragelogger to your code

## How to use?
1. Import pgstoragelogger in Your code;
2. Declare a new instance of the class PGStorageLogger (require db connection credentials & Your app name);
3. Use instance_name.Info for fast insert log;
4. Or user instance_name.InsertLog to ovverride some parameters.

Example: https://github.com/le-kazankin/PGStorageLogger/blob/main/example/example.py

### Terms and definitions
Section - a table of a current day.

### Pypi
pypi.org link project: https://pypi.org/project/pgstoragelogger/
