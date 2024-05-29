#
# POST /auth
#
# Lambda function to handle authentication. The caller can 
# post a token, or a username/password, and the function 
# authenticates the token or username. Valid message formats:
#
# { "body": { "token": "..." } }
# { "body": { "username": "...", "password": "..." } }
#
# If a token is passed, the function returns 200 if the 
# token is still valid, and 401 if not. If a username/pwd
# is passed, the function returns 200 --- and a token ---
# if the username exists and the password matches. Otherwise
# 401 is returned.
#
# When passing username/password, an optional "duration" can
# be posted, which is the duration in minutes for the token
# before it expires --- passing small values like 1 or 2 is
# good for testing. The default is 30 minutes, and at most
# the caller can set the duration to 60 minutes. Values < 1
# or > 60 are ignored.
#
# Original author: Dilan Nair
# Modifed by: Prof. Joe Hummel
# Northwestern University
#

import json
import os
import datetime
import uuid
import datatier
import auth
import api_utils

from configparser import ConfigParser

def lambda_handler(event, context):
  try:
    print("**STARTING**")
    print("**lambda: proj04_auth**")

    #
    # setup AWS based on config file
    #
    config_file = 'benfordapp-config.ini'
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file
    
    configur = ConfigParser()
    configur.read(config_file)
    
    #
    # configure for RDS access
    #
    rds_endpoint = configur.get('rds', 'endpoint')
    rds_portnum = int(configur.get('rds', 'port_number'))
    rds_username = configur.get('rds', 'user_name')
    rds_pwd = configur.get('rds', 'user_pwd')
    rds_dbname = configur.get('rds', 'db_name')
    
    #
    # open connection to the database
    #
    print("**Opening connection**")
    
    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)

    #
    # We are expecting either a token, or username/password:
    #
    print("**Accessing request body**")
    
    token = ""
    username = ""
    password = ""

    if "body" not in event:
      return api_utils.error(400, "no body in request")
      
    body = json.loads(event["body"])
    
    if "token" in body:
      token = body["token"]
    elif "username" in body and "password" in body:
      username = body["username"]
      password = body["password"]
    else:
      return api_utils.error(400, "missing credentials in body")
      
    #
    # if we were passed a token, lookup in the database and
    # see if exists, and still valid:
    #
    if token != "":
      #
      # we have a token, validate:
      #
      print("**We were passed a token**")
      print("token:", token)
      
      print("**Looking up token in database**")
      
      sql = "SELECT userid, expiration_utc FROM tokens WHERE token = %s;"

      row = datatier.retrieve_one_row(dbConn, sql, [token])

      if row == ():
        print("**No such token, returning...**")
        return api_utils.error(401, "invalid token")
      
      userid = row[0]
      expiration_utc = row[1]
      
      print("userid", userid)
      print("expiration_utc:", expiration_utc)
      
      #
      # has token expired?
      #
      print("**Has token expired?**")
      
      utc_now = datetime.datetime.utcnow()
      print("utc_now:", utc_now)
      
      if utc_now < expiration_utc: 
        #
        # not expired, still valid:
        #
        print("**Token STILL VALID, returning success**")
        return api_utils.success(200, "valid token")
      else:
        #
        # expired:
        #
        print("**Token HAS EXPIRED, returning invalid token**")
        return api_utils.error(401, "expired token")
    
    #
    # we were passed username/password, authenticate
    # and return token if so:
    #
    print("**We were passed username/password**")
    print("username:", username)
    print("password:", password)
    
    #
    # did they pass a duration for the token? It's optional:
    #
    duration = 30 # minutes (default) before token expires
    
    if "duration" in body:
      #
      # if within range, override default:
      #
      requested_duration = int(body["duration"])
      if 1 <= requested_duration <= 60:
        duration = requested_duration
    
    print("duration:", duration)
      
    print("**Looking up user**")
      
    sql = "SELECT userid, pwdhash FROM users WHERE username = %s;"

    row = datatier.retrieve_one_row(dbConn, sql, [username])

    if row == ():
      print("**No such user, returning...**")
      return api_utils.error(401, "invalid username")
        
    userid = row[0]
    pwdhash = row[1]
      
    print("userid", userid)
    print("pwdhash:", pwdhash)
    
    #
    # hash user's password and check for a match:
    #
    if not auth.check_password(password, pwdhash):
      print("**Password is NOT correct, returning...**")
      return api_utils.error(401, "invalid password")
      
    #
    # password matches, generate a token and return it:
    #
    print("**Password is correct**")
    print("**Generating access token**")

    token = str(uuid.uuid4())
    
    print("token:", token)
    
    #
    # store token in database for future authentications
    #
    print("**Inserting token into database**")
    
    expiration_utc = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)
    
    #
    # TODO 1 of 1:
    #
    # Insert the token, userid, and expiration_utc into the database:
    #
    
    sql = "INSERT INTO tokens (token, userid, expiration_utc) VALUES (%s, %s, %s);"
    
    modified = datatier.perform_action(dbConn, sql, [token, userid, expiration_utc])
    
    if modified != 1:
      print("**INTERNAL ERROR: insert into database failed...**")
      return api_utils.error(400, "INTERNAL ERROR: insert failed to modify database")
    
    #
    # success, done!
    #
    print("**DONE, returning token**")

    return api_utils.success(200, token)
    
  except Exception as err:
    print("**ERROR**")
    print(str(err))

    return api_utils.error(400, str(err))
