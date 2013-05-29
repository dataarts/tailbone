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

"""Module to manage load information of Compute Engine instances."""



import logging
import random

from google.appengine.api import memcache
from google.appengine.ext import db


class SingleInstance(db.Model):
  """Datastore schema to represent single instance.

  Instance information in Datastore works as back up in case table in Memcache
  is gone.
  """
  ip_address = db.StringProperty(multiline=False)

  @classmethod
  def GetByName(cls, name):
    """Utility to get SingleInstance object in Datastore.

    Args:
      name: Name of the instance.
    Returns:
      SingleInstance object saved in Datastore.  None if the name is not found.
    """
    return cls.get_by_key_name(name)


class LoadInfo(object):
  """Utility class to handle load information database.

  Memcache holds list of instances with load information.
  Key: Name of instance.
  Value: Dictionary with the following keys.
    ip_address: IP address in string
    load: Load level in integer [0-100].
    force: Boolean to indicate it's set by admin UI.
  Instance name is generated with UUID when the instance is created.
  List of all keys are saved with under 'all_instances' key, in order to
  retrieve information of all instances.
  """

  ALL_INSTANCES = 'all_instances'
  IP_ADDRESS = 'ip_address'
  LOAD = 'load'
  FORCE = 'force'
  CANDIDATE_MIN_SIZE = 3

  @classmethod
  def _GetInstanceList(cls):
    """Returns all instance names in list."""
    all_instances = memcache.get(cls.ALL_INSTANCES)
    if all_instances is not None:
      return all_instances
    all_instances = [key.name() for key in SingleInstance.all(keys_only=True)]
    memcache.set(cls.ALL_INSTANCES, all_instances)
    return all_instances

  @classmethod
  def _IsManagedInstance(cls, name):
    """Determines whether the instance is managed by this application.

    Args:
      name: Name of the instance to check.
    Returns:
      Boolean value.
    """
    return name in cls._GetInstanceList()

  @classmethod
  def InitializeTable(cls):
    """Clears list of managed instances and initializes the load table."""
    memcache.set(cls.ALL_INSTANCES, [])

  @classmethod
  def AddInstance(cls, name):
    """Adds new instance to the list of instances in Memcache.

    Args:
      name: Name of the instance.
    """
    # First, update Datastore.
    # Add StringInstance for this instance without ip_address property.
    # Existing entity with the same name is overwritten by put() call.
    SingleInstance(key_name=name).put()

    # Then update Memcache.
    # To avoid race condition, use cas update.
    memcache_client = memcache.Client()
    while True:
      instances = memcache_client.gets(cls.ALL_INSTANCES)
      if instances is None:
        # This is not supposed to happen, since InitializeTable() is
        # supposed to be called in advance at cluster set up.
        # This is dangerous operation, since somebody else might have already
        # set value betweeen previous gets() and now.
        logging.error('all_instances entry in Memcache is None.')
        memcache.set(cls.ALL_INSTANCES, [name])
        break
      if name in instances:
        break
      instances.append(name)
      if memcache_client.cas(cls.ALL_INSTANCES, instances):
        break

  @classmethod
  def RegisterInstanceIpAddress(cls, name, ip_address):
    """Registers IP address of the instance to load information.

    If the instance is not in the list of instances the application manages,
    the function does nothing.

    Args:
      name: Name of the instance.
      ip_address: IP address in string format.
    """
    if cls._IsManagedInstance(name):
      # Record IP address to SingleInstance in Datastore.
      instance = SingleInstance.GetByName(name)
      instance.ip_address = ip_address
      instance.put()
      # Update Memcache information.
      memcache.set(name, {cls.IP_ADDRESS: ip_address})
    else:
      logging.error('Registration request for unmanaged instance %s', name)

  @classmethod
  def RemoveInstance(cls, name):
    """Removes load information entry of the instance.

    Args:
      name: Name of the instance to remove from load information list.
    """
    # Use cas operation to remove from instance name list.
    memcache_client = memcache.Client()
    while True:
      instances = memcache_client.gets(cls.ALL_INSTANCES)
      if not instances:
        break
      try:
        instances.remove(name)
      except ValueError:
        # The instance name was not in the list.
        break
      if memcache_client.cas(cls.ALL_INSTANCES, instances):
        break

    # Delete the entry for the instance in Memcache and Datastore.
    memcache.delete(name)
    datastore_single_instance = SingleInstance.GetByName(name)
    if datastore_single_instance:
      datastore_single_instance.delete()

  @classmethod
  def UpdateLoadInfo(cls, name, load, force_set=None):
    """Updates load informatino of one instance specified by name.

    This function assumes the corresponding entry already exists, and fails
    if it doesn't exist.  If force_set is already true, and new update is not
    force_set, the function doesn't overwrite the old value.

    Args:
      name: Name of the instance.
      load: New load level in percent integer [0-100].
      force_set: Switch to set load overwrite ('force') flag.  True to set,
          False to unset and None for unchange.
    Returns:
      Boolean to indicate success update.
    """
    if not cls._IsManagedInstance(name):
      return False

    info = memcache.get(name)
    if info:
      # If force flag is set in Memcache, it doesn't accept regular update.
      # It's only updated when force_set switch is specified (True or False).
      if info.get(cls.FORCE, False) and force_set is None:
        return True
    else:
      # The entry for this instance doesn't exist in Memcache.
      logging.warning('Load entry of instance %s does not exist in Memcache',
                      name)
      # Try to get from Datastore.
      ds_instance = SingleInstance.GetByName(name)
      if ds_instance:
        info = {cls.IP_ADDRESS: ds_instance.ip_address}
      else:
        logging.error('Load entry for instance %s not found in Datastore',
                      name)
        return False

    info[cls.LOAD] = load
    info[cls.FORCE] = bool(force_set)
    return memcache.set(name, info)

  @classmethod
  def GetAll(cls):
    """Retrieves all load information of all instances.

    Returns:
      Dictionary of instance name as a key and dictionary of load information
      as a value.  If no instance is managed, returns empty dictionary.
    """
    all_instances = cls._GetInstanceList()
    if not all_instances:
      return {}
    return memcache.get_multi(all_instances)

  @classmethod
  def GetIdleInstanceIpAddress(cls):
    """Retrieves IP address of desirable instance.

    This function returns IP address of one of the least loaded instances.
    It returns an IP address randomly from several of the idlest instances.

    Returns:
      None if the function fails, otherwise IP address in string format
      ('xxx.xxx.xxx.xxx').
    """
    all_infos = cls.GetAll()
    candidates = []
    # At least CANDIDATE_MIN_SIZE instances are added to candidates.
    # After that, if the instance's load is the same as the last candidate's
    # load, the instance is added to candidates.
    for info in sorted(all_infos.values(),
                       key=lambda x: x.get(cls.LOAD, 10000)):
      if cls.LOAD not in info:
        break
      if len(candidates) < cls.CANDIDATE_MIN_SIZE:
        candidates.append(info)
        last_load = info[cls.LOAD]
      else:
        if info[cls.LOAD] == last_load:
          candidates.append(info)
        else:
          break
    # If candidates are empty, we cannot return anything.
    if not candidates:
      return None
    # Return IP address of one of the candidates randomly.
    return candidates[random.randint(0, len(candidates) - 1)][cls.IP_ADDRESS]

  @classmethod
  def GetAverageLoad(cls):
    """Calculates average load of all instances.

    Returns:
      Cluster size and average load.  Average load level is in percent in
      integer [0-100].
    """
    all_infos = cls.GetAll()
    total_load = 0
    cluster_size = 0
    for info in all_infos.values():
      if cls.LOAD in info:
        cluster_size += 1
        total_load += info[cls.LOAD]
    if not cluster_size:
      return 0, 0
    return cluster_size, total_load / cluster_size

