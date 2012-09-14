#! /usr/bin/env python2.7
import os
import os.path
import sys
from unittest import loader
from unittest import runner

for path in os.environ['PATH'].split(':'):
  if 'dev_appserver.py' in os.listdir(path):
    break
else:
  raise RuntimeError("Couldn't find dev_appserver.py")

# find and append appengine dir to path
app_engine_path = os.path.realpath(os.path.join(path,'dev_appserver.py'))
app_engine_path = os.path.dirname(app_engine_path)
sys.path.append(app_engine_path)

import appcfg
sys.path.extend(appcfg.EXTRA_PATHS)

loader = loader.TestLoader()
tests = loader.discover('.')
runner = runner.TextTestRunner()
result = runner.run(tests)
sys.exit(result.wasSuccessful())
