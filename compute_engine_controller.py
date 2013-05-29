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

"""Module to manipulate Compute Engine instances as game backend servers.

This module uses Google APIs Client Library to control Compute Engine.

  http://code.google.com/p/google-api-python-client/

"""



import logging
import os
import uuid

from apiclient.discovery import build
from apiclient.errors import HttpError
import httplib2
import jinja2
from oauth2client.client import OAuth2Credentials

from load_info import LoadInfo

from google.appengine.api import app_identity
from google.appengine.api import memcache
from google.appengine.api import users
from google.appengine.ext import db


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class AuthorizedUserId(db.Model):
  """Datastore schema to hold authorized user ID."""
  user_id = db.StringProperty(multiline=False)
  credentials = db.TextProperty()


class ComputeEngineController(object):
  """Class to manipulate Compute Engine instances.

  This class uses Google Client API module to manipulate Compute Engine.

  Attributes:
    compute_api: Client API object with authorized HTTP.
  """

  SCOPE = 'https://www.googleapis.com/auth/compute'

  PROJECT_ID = '858095213682'

  COMPUTE_API_VERSION = 'v1beta15'
  DEFAULT_ZONE = 'us-central1-a'
  DEFAULT_IMAGE = 'debian-7-wheezy-v20130515'
  DEFAULT_MACHINE_TYPE = 'n1-standard-1'

  INITIAL_CLUSTER_SIZE = 5
  API_URL_BASE = ('https://www.googleapis.com/compute/%s/projects/' %
                  COMPUTE_API_VERSION)
  WORKER_NAME_PREFIX = 'gameserver-'
  USER_ID_KEY = 'userid'
  USER_CREDENTIALS_KEY = 'user_credentials'

  def __init__(self, credentials=None):
    """Initialize Client API object for Compute Engine manipulation.

    If authorized HTTP is not given by parameter, it uses user ID stored
    in Memcache and fetches credentials for that user.

    Args:
      credentials: OAuth2 credentials of current user.
    """
    if credentials:
      user_id = users.get_current_user().user_id()
      credentials_in_json = credentials.to_json()
      authorized_user = AuthorizedUserId.get_or_insert(
          self.USER_ID_KEY, user_id=user_id,
          credentials=db.Text(credentials_in_json))
      memcache.set(self.USER_CREDENTIALS_KEY, credentials_in_json)
      if (authorized_user.user_id != user_id or
          str(authorized_user.credentials) != credentials_in_json):
        authorized_user.user_id = user_id
        authorized_user.credentials = db.Text(credentials_in_json)
        authorized_user.put()
    else:
      credentials_in_json = memcache.get(self.USER_CREDENTIALS_KEY)
      if not credentials_in_json:
        authorized_user = AuthorizedUserId.get_by_key_name(self.USER_ID_KEY)
        credentials_in_json = str(authorized_user.credentials)
      credentials = OAuth2Credentials.from_json(credentials_in_json)
    self.compute_api = build('compute', self.COMPUTE_API_VERSION,
                             http=credentials.authorize(httplib2.Http()))

  def _ApiUrl(self, project='', paths=(), is_global=False):
    """Returns API path for the specified resource.

    Args:
      project: Project name.  If unspecified, the default project name is used.
      paths: List or tuple of names to indicate the path to the resource.
      is_global: Boolean to indicate whether the resource is global.
    Returns:
      API path to the specified resource in string.
    """
    if not project:
      project = self.PROJECT_ID

    if is_global:
      return self.API_URL_BASE + project + '/global/' + '/'.join(paths)
    else:
      return self.API_URL_BASE + project + '/' + '/'.join(paths)

  def _StartInstance(self, instance_name):
    """Creates Compute Engine instance with the given name."""
    logging.info('Starting instance: ' + instance_name)

    startup_script_template = jinja_environment.get_template(
        os.path.join('worker', 'checkload.py'))
    version = os.environ['CURRENT_VERSION_ID'].split('.')[0]
    hostname = version + '-dot-' + app_identity.get_default_version_hostname()
    startup_script = startup_script_template.render({
        'hostname': hostname
        })

    param = {
        'kind': 'compute#instance',
        'name': instance_name,
        'zone': self._ApiUrl(paths=['zones', self.DEFAULT_ZONE]),
        'image': self._ApiUrl('debian-cloud', paths=['images', self.DEFAULT_IMAGE],
                              is_global=True),
        'machineType': self._ApiUrl(
            paths=['zones', self.DEFAULT_ZONE, 'machineTypes', self.DEFAULT_MACHINE_TYPE], is_global=False),
        'networkInterfaces': [
            {
                'kind': 'compute#networkInterface',
                'network': self._ApiUrl(paths=['networks', 'default'],
                                        is_global=True),
                'accessConfigs': [
                    {
                        'type': 'ONE_TO_ONE_NAT',
                        'name': 'External NAT'
                    }
                ],
            }
        ],
        'serviceAccounts': [
            {
                'kind': 'compute#serviceAccount',
                'email': 'default',
                'scopes': [
                    'https://www.googleapis.com/auth/devstorage.read_only'
                ]
            }
        ],
        'metadata': {
            'items': [
                {
                    'key': 'startup-script',
                    'value': startup_script,
                },
            ],
        }
    }

    logging.info('Create instance with parameter: %s', str(param))

    operation = self.compute_api.instances().insert(
        project=self.PROJECT_ID, zone=self.DEFAULT_ZONE, body=param).execute()
    logging.info('Create instance operation: %s', str(operation))

  def _DeleteInstance(self, instance_name):
    """Stops and deletes the instance specified by the name."""
    logging.info('Deleting instance %s', instance_name)
    LoadInfo.RemoveInstance(instance_name)
    result = self.compute_api.instances().delete(
        project=self.PROJECT_ID, zone=self.DEFAULT_ZONE,
        instance=instance_name).execute()
    logging.info(str(result))

  def GetInstanceInfo(self, instance_name):
    """Retrieves instance information.

    The detail of returned structure is described here.
      https://google-api-client-libraries.appspot.com/documentation/compute/v1beta13/python/latest/compute_v1beta13.instances.html#get

    Args:
      instance_name: Name of the instance.
    Returns:
      Dictionary that contains Compute Engine instance information.
      None if the information of the instance cannot be retrieved.
    """
    try:
      return self.compute_api.instances().get(
          project=self.PROJECT_ID, zone=self.DEFAULT_ZONE,
          instance=instance_name).execute()
    except HttpError, e:
      logging.error('Failed to get instance information of %s', instance_name)
      logging.error(e)
    return None

  def ListInstances(self):
    """Returns list of instance names managed by this application.

    Returns:
      List of instance names (string).  If there's no instance, returns
      empty list.
    """
    instance_list = []
    page_token = None
    try:
      while True:
        response = self.compute_api.instances().list(
            project=self.PROJECT_ID, zone=self.DEFAULT_ZONE,
            pageToken=page_token,
            filter='name eq ^{0}.+'.format(self.WORKER_NAME_PREFIX)).execute()
        if response and 'items' in response:
          instance_list.extend(response.get('items', []))
        else:
          break
        page_token = response.get('nextPageToken')
        if not page_token:
          break
    except HttpError, e:
      logging.error('Failed to retrieve Compute Engine instance list: %s',
                    str(e))

    return instance_list

  def StartUpCluster(self):
    """Initializes and start up Compute Engine cluster.

    Records user ID and use it later by Taskqueue, Cron job handlers
    and other handlers which is initiated by Compute Engine (therefore
    without log in), to retrieve credential from Datastore.  It means
    those tasks work under permission of the user who started the cluster.
    """
    LoadInfo.InitializeTable()
    self.IncreaseEngine(self.INITIAL_CLUSTER_SIZE)

  def TearDownCluster(self):
    """Deletes all Compute Engine instances with our name prefix."""
    for instance in self.ListInstances():
      self._DeleteInstance(instance['name'])

  def IncreaseEngine(self, increase_count):
    """Starts specified number of Compute Engine instances.

    Args:
      increase_count: Number of instances to increase.
    """
    for _ in xrange(increase_count):
      instance_name = self.WORKER_NAME_PREFIX + str(uuid.uuid4())
      # Add instance name to load information before actually creating the
      # instance to avoid, to make sure the instance is managed
      # when it registers IP address.
      LoadInfo.AddInstance(instance_name)
      self._StartInstance(instance_name)

  def DecreaseEngine(self, decrease_count):
    """Reduces specified number of Compute Engine instances.

    In reality, shutting down the game server is more complicated than
    shutting down the Compute Engine instance.  It should first wait for
    all users to finish their sessions before the shut down.
    This example doesn't implement the shut down procedure.

    Args:
      decrease_count: Number of instances to decrease.
    """
    # This is the placeholder for user's implementation.
    pass

