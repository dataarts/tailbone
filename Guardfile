#!/usr/bin/env python

# Guardfile
# More info at https://github.com/lepture/python-livereload

from livereload.task import Task
from livereload.compiler import shell

Task.add('client/app/*.scss', shell('sass --update', 'client/app'))

Task.add('client/app/*')
Task.add('tailbone/*')
