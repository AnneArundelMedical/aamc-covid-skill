#!/usr/bin/env python3

import os
import random

def listfiles(directory, extension=None):
    return list(_listfiles_generator(directory, extension))

def _listfiles_generator(directory, extension):
    for root, dirs, files in os.walk(directory):
        for f in files:
            if extension is None or f.endswith(extension):
                yield os.path.join(root, f)

def choose_n(source_list, n_choices):
    choices = []
    while len(choices) < n_choices:
        next_batch = list(source_list)
        random.shuffle(next_batch)
        choices += next_batch
    return choices[:n_choices]

