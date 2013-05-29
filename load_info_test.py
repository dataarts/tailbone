#!/usr/bin/python
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for load_info."""

import unittest

from load_info import LoadInfo
from load_info import SingleInstance

from google.appengine.api import memcache
from google.appengine.ext import testbed


class LoadInfoTest(unittest.TestCase):
  """Unit test case class for LoadInfo.

  The class uses testbed to mock Datastore and Memcache.
  """

  def setUp(self):
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_memcache_stub()

  def tearDown(self):
    self.testbed.deactivate()

  def testInitializeTable(self):
    LoadInfo.InitializeTable()

    self.assertEqual([], memcache.get(LoadInfo.ALL_INSTANCES))
    self.assertEqual({}, LoadInfo.GetAll())

  def testAddInstance(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance')

    self.assertEqual(['test-instance'], memcache.get(LoadInfo.ALL_INSTANCES))
    self.assertEqual({}, LoadInfo.GetAll())
    self.assertIsNone(memcache.get('test-instance'))
    self.assertIsNotNone(SingleInstance.GetByName('test-instance'))
    self.assertRaises(ValueError,
                      SingleInstance.GetByName('test-instance').ip_address)

  def testRegisterInstance(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance')
    LoadInfo.RegisterInstanceIpAddress('test-instance', '1.2.3.4')
    self.assertEqual(['test-instance'], memcache.get(LoadInfo.ALL_INSTANCES))
    self.assertEqual(
        {'test-instance': {'ip_address': '1.2.3.4'}},
        LoadInfo.GetAll())
    self.assertEqual({'ip_address': '1.2.3.4'}, memcache.get('test-instance'))
    self.assertEqual('1.2.3.4',
                     SingleInstance.GetByName('test-instance').ip_address)

  def testUpdateLoadInfo(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance')
    LoadInfo.RegisterInstanceIpAddress('test-instance', '1.2.3.4')

    LoadInfo.UpdateLoadInfo('test-instance', 55)
    self.assertEqual({
        'test-instance': {'ip_address': '1.2.3.4', 'load': 55, 'force': False}
        }, LoadInfo.GetAll())

    LoadInfo.UpdateLoadInfo('test-instance', 73)
    self.assertEqual({
        'test-instance': {'ip_address': '1.2.3.4', 'load': 73, 'force': False}
        }, LoadInfo.GetAll())

  def testUpdateLoadInfoForce(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance')
    LoadInfo.RegisterInstanceIpAddress('test-instance', '1.2.3.4')

    LoadInfo.UpdateLoadInfo('test-instance', 55)
    self.assertEqual({
        'test-instance': {'ip_address': '1.2.3.4', 'load': 55, 'force': False}
        }, LoadInfo.GetAll())

    LoadInfo.UpdateLoadInfo('test-instance', 92, True)
    self.assertEqual({
        'test-instance': {'ip_address': '1.2.3.4', 'load': 92, 'force': True}
        }, LoadInfo.GetAll())

    # This update is ignored since force flag is set in data and this is not
    # force update.
    LoadInfo.UpdateLoadInfo('test-instance', 15)
    self.assertEqual({
        'test-instance': {'ip_address': '1.2.3.4', 'load': 92, 'force': True}
        }, LoadInfo.GetAll())

    # Updated because of force_set flag.
    LoadInfo.UpdateLoadInfo('test-instance', 8, True)
    self.assertEqual({
        'test-instance': {'ip_address': '1.2.3.4', 'load': 8, 'force': True}
        }, LoadInfo.GetAll())

    LoadInfo.UpdateLoadInfo('test-instance', 41, False)
    self.assertEqual({
        'test-instance': {'ip_address': '1.2.3.4', 'load': 41, 'force': False}
        }, LoadInfo.GetAll())

    LoadInfo.UpdateLoadInfo('test-instance', 28)
    self.assertEqual({
        'test-instance': {'ip_address': '1.2.3.4', 'load': 28, 'force': False}
        }, LoadInfo.GetAll())

  def testMemcacheClear(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance')
    LoadInfo.RegisterInstanceIpAddress('test-instance', '1.2.3.4')
    LoadInfo.UpdateLoadInfo('test-instance', 55)
    # Simulate loss of all data in Memcache.
    memcache.flush_all()
    LoadInfo.UpdateLoadInfo('test-instance', 38)

    self.assertEqual({
        'test-instance': {'ip_address': '1.2.3.4', 'load': 38, 'force': False}
        }, LoadInfo.GetAll())

  def testRemoveInstanceFromOne(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance')
    LoadInfo.RegisterInstanceIpAddress('test-instance', '1.2.3.4')
    LoadInfo.UpdateLoadInfo('test-instance', 55)
    LoadInfo.RemoveInstance('test-instance')

    self.assertEqual({}, LoadInfo.GetAll())
    self.assertEqual([], memcache.get(LoadInfo.ALL_INSTANCES))
    self.assertIsNone(memcache.get('test-instance'))
    self.assertIsNone(SingleInstance.GetByName('test-instance'))

  def testRemoveInstanceFromTwo(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance1')
    LoadInfo.RegisterInstanceIpAddress('test-instance1', '1.2.3.4')
    LoadInfo.UpdateLoadInfo('test-instance1', 55)
    LoadInfo.AddInstance('test-instance2')
    LoadInfo.RegisterInstanceIpAddress('test-instance2', '5.6.7.8')
    LoadInfo.UpdateLoadInfo('test-instance2', 22)
    LoadInfo.RemoveInstance('test-instance1')

    self.assertEqual({
        'test-instance2': {'ip_address': '5.6.7.8', 'load': 22, 'force': False}
        }, LoadInfo.GetAll())
    self.assertIsNone(memcache.get('test-instance1'))
    self.assertIsNone(SingleInstance.GetByName('test-instance1'))

  def testGetIdleInstanceIpAddress(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance1')
    LoadInfo.RegisterInstanceIpAddress('test-instance1', '1.2.3.4')
    LoadInfo.UpdateLoadInfo('test-instance1', 55)
    LoadInfo.AddInstance('test-instance2')
    LoadInfo.RegisterInstanceIpAddress('test-instance2', '5.6.7.8')
    LoadInfo.UpdateLoadInfo('test-instance2', 11)
    LoadInfo.AddInstance('test-instance3')
    LoadInfo.RegisterInstanceIpAddress('test-instance3', '9.10.11.12')
    LoadInfo.UpdateLoadInfo('test-instance3', 66)
    LoadInfo.AddInstance('test-instance4')
    LoadInfo.RegisterInstanceIpAddress('test-instance4', '13.14.15.16')
    LoadInfo.UpdateLoadInfo('test-instance4', 22)

    # IP address should be picked up from one of the 3 least loaded instances.
    self.assertIn(
        LoadInfo.GetIdleInstanceIpAddress(),
        ('1.2.3.4', '5.6.7.8', '13.14.15.16'))

  def testGetIdleInstanceExcludingImmatureInstance(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance1')
    LoadInfo.RegisterInstanceIpAddress('test-instance1', '1.2.3.4')
    LoadInfo.UpdateLoadInfo('test-instance1', 55)
    LoadInfo.AddInstance('test-instance2')
    LoadInfo.RegisterInstanceIpAddress('test-instance2', '5.6.7.8')
    # test-instance2 hasn't yet reported load information.

    self.assertEqual('1.2.3.4', LoadInfo.GetIdleInstanceIpAddress())

  def testAverageLoad(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance1')
    LoadInfo.RegisterInstanceIpAddress('test-instance1', '1.2.3.4')
    LoadInfo.UpdateLoadInfo('test-instance1', 55)
    LoadInfo.AddInstance('test-instance2')
    LoadInfo.RegisterInstanceIpAddress('test-instance2', '5.6.7.8')
    LoadInfo.UpdateLoadInfo('test-instance2', 11)
    LoadInfo.AddInstance('test-instance3')
    LoadInfo.RegisterInstanceIpAddress('test-instance3', '9.10.11.12')
    LoadInfo.UpdateLoadInfo('test-instance3', 66)

    self.assertEqual((3, 44), LoadInfo.GetAverageLoad())

  def testAverageLoadExcludingImmatureInstance(self):
    LoadInfo.InitializeTable()
    LoadInfo.AddInstance('test-instance1')
    LoadInfo.RegisterInstanceIpAddress('test-instance1', '1.2.3.4')
    # test-instance1 hasn't yet reported load information.
    LoadInfo.AddInstance('test-instance2')
    LoadInfo.RegisterInstanceIpAddress('test-instance2', '5.6.7.8')
    LoadInfo.UpdateLoadInfo('test-instance2', 33)

    self.assertEqual((1, 33), LoadInfo.GetAverageLoad())


if __name__ == '__main__':
  unittest.main()
