import json
import os

from six.moves import configparser

parameters = json.loads(os.environ["INPUT"])
folders = ["simulation", "preprocess", "process", "postprocess", "export"]

for folder in folders:
    try:
        os.makedirs(os.path.join("/", "data", "folders", folder), 0o2775)
    # Path already exists, ignore
    except OSError:
        if not os.path.isdir(os.path.join("/", "data", "folders", folder)):
            raise

# Create ini file for containers
config = configparser.SafeConfigParser()
for section in parameters:
    if not config.has_section(section):
        config.add_section(section)
    for key, value in parameters[section].items():

        # TODO: find more elegant solution for this! ugh!
        if not key == "units":
            if not config.has_option(section, key):
                config.set(*map(str, [section, key, value]))

for folder in folders:
    with open(os.path.join("/", "data", "folders", folder, "input.ini"), "w") as f:
        config.write(f)  # Yes, the ConfigParser writes to f
