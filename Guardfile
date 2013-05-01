#!/usr/bin/env python

# Guardfile
# More info at https://github.com/lepture/python-livereload

from livereload.task import Task
from livereload.compiler import shell
import sys

Task.add('client/app/*.scss', shell('sass --update', 'client/app', 'log'))

Task.add('client/app/*')
Task.add('tailbone/*')
