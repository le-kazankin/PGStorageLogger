#!/bin/python3

# begin import region
import json
import pathlib
from pgstoragelogger import PGStorageLogger
# end import region

cfg = json.load(open(pathlib.Path(pathlib.Path.cwd(),'example','config.json'), "r"))

example = PGStorageLogger(application_name="test_app", db=cfg["database"]["db"], db_user=cfg["database"]["user"],
                          db_password=cfg["database"]["password"], db_host=cfg["database"]["host"], level_limit='warn', days_store=3)
example.Info("Hello world!")
example.Debug("test debug")
print(example.Warn("This is an example."))