Automatic RESTful backend for AppEngine

So to start just a normal RESTful backend
POST, GET, DELETE models etc

Special URLS:
  POST /api/{modelname}/
    creates an object
  PUT or POST /api/{modelname}/{id}
    updates an object, does a complete overwrite of the properites not a partial patch
  GET /api/{modelname}/{id}
    Get a specific object
  GET /api/{modelname}/?filter={propertyname==somevalue}&order={propertyname}
    Query a type

  /api/users
    can only be edited by the user, authentication via Google Account
  /api/users/me
    Returns the current users information
  /api/login
    logs you in
  /api/logout
    logs you out
  POST /api/files/
    uploads the form data to blobstore
    returns the files names and their ids
  GET /api/files/{id}
    returns the actual uploaded file
  DELETE /api/files/{id}
    deletes a file from blobstore
    note there is no put to update an id you must always create a new one and delete the old
    yourself
