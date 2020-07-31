#!/usr/bin/env python3
# vim: et sts=4 sw=4

import sys, os, os.path, pathlib

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
                else:
                    raise Exception("Invalid command: " + cmd, file=sys.stderr)
                write_file(old_filename, old_language, content_lines)
                content_lines = []
            else:
                content_lines.append(line)
    write_file(filename, language, content_lines)

def write_file(filename, language, content_lines):
    if filename is None:
        return
    if language is None and content_lines:
        raise Exception("No language specified for filename: " + filename)
    directory = "locale/%s" % language
    mkdir(directory)
    path = "%s/%s" % (directory, filename)
    content = "\n".join(content_lines).strip()
    with open(path, "wb") as f:
        f.write(content.encode("utf-8"))

def mkdir(directory):
    pathlib.Path(directory).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    main()

