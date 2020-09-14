#!/usr/bin/env python3
# vim: et sts=4 sw=4

import sys, os, os.path, pathlib, json

PARAMS_PATH = "file_params.json"

FILE_PARAM_NAMES = [
    "EXPECTED",
]

def main():
    _, source_path = sys.argv
    generate(source_path)

def generate(source_path):
    with open(source_path) as f:
        source = f.readlines()
    in_comment = False
    filename = None
    language = None
    content_lines = []
    file_params = {}
    for line in source:
        line = line.rstrip()
        if in_comment:
            if line.endswith("]"):
                in_comment = False
        else:
            if line.startswith("["):
                if line.endswith("]"):
                    pass # one-line comment, just ignore this line
                else:
                    in_comment = True # multi-line comment
            elif line.startswith(">"):
                cmd, arg = line[1:].split("=")
                old_filename = filename
                old_language = language
                if cmd == "FILE":
                    filename = arg
                    language = None
                elif cmd == "LANG":
                    language = arg
                elif cmd in FILE_PARAM_NAMES:
                    if not (filename in file_params):
                        file_params[filename] = {}
                    if cmd in file_params[filename]:
                        raise Exception("Duplicate param '%s' for file '%s'." % (cmd, filename))
                    file_params[filename][cmd] = arg
                else:
                    raise Exception("Invalid command: " + cmd)
                write_file(old_filename, old_language, content_lines)
                content_lines = []
            else:
                content_lines.append(line)
    write_file(filename, language, content_lines)
    write_params(file_params)

def write_file(filename, language, content_lines):
    if filename is None:
        return
    if language is None and content_lines:
        raise Exception("No language specified for filename: " + filename)
    if language is None:
        return
    directory = "locale/%s" % language
    mkdir(directory)
    path = "%s/%s" % (directory, filename)
    content = "\n".join(content_lines).strip()
    content = content.replace("’", "'")
    content = content.replace('“', '"')
    content = content.replace('”', '"')
    with open(path, "wb") as f:
        f.write(content.encode("utf-8"))
        f.write(b'\n')

def write_params(file_params):
    with open(PARAMS_PATH, "w") as f:
        json.dump(file_params, f, indent=1, sort_keys=True)
        print(file=f)

def mkdir(directory):
    pathlib.Path(directory).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    main()

