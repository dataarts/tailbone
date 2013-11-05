#!/usr/bin/env python

# Guardfile
# More info at https://github.com/lepture/python-livereload

from livereload.task import Task
from livereload.compiler import shell


def recursive_watch(directory, filetypes, *args, **kwargs):
  import os
  for root, dirs, files in os.walk(directory):
    if filetypes:
      towatch = set()
      for filetype in filetypes:
        for f in files:
          if filetype in f:
            towatch.add(filetype)
      for filetype in towatch:
        Task.add(os.path.join(root,"*.{}".format(filetype)), *args, **kwargs)
    else:
      Task.add(os.path.join(root, "*"), *args, **kwargs)


recursive_watch("client/app", [])
recursive_watch("tailbone", ["py", "html", "js", "css", "yaml"])

recursive_watch("client/app", ["scss"], shell('sass --update', 'client/app'))
