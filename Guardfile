#!/usr/bin/env python

# Guardfile
# More info at https://github.com/lepture/python-livereload

from livereload.task import Task
from livereload.compiler import shell


def recursive_watch(directory, re_filetype, *args, **kwargs):
  import re
  import os
  pattern = re.compile(re_filetype)
  for root, dirs, files in os.walk(directory):
    for basename in files:
      if pattern.match(basename):
        filename = os.path.join(root, basename)
        Task.add(filename, *args, **kwargs)


recursive_watch("client/app", r".*")
recursive_watch("tailbone", r".*\.(py|htm[l]?|css|js|yaml)$")

recursive_watch("client/app", r".*\.scss$", shell('sass --update', 'client/app'))
