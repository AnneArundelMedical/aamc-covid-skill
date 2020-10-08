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

def test_choose_n():
    choices = [1,2,3,4,5]
    for choices in [
            [1,2,3,4,5],
            ["abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx"],
    ]:
        for x in range(1, 30):
            chosen = choose_n(choices, 3)
            assert len(chosen) == 3
            assert chosen[0] != chosen[1]
            assert chosen[0] != chosen[2]
            assert chosen[1] != chosen[2]
            assert chosen[0] in choices
            assert chosen[1] in choices
            assert chosen[2] in choices

