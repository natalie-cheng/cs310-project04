#
# Retrieves and returns all the jobs in the 
# BenfordApp database.
#

import json
import boto3
import os
import datatier
import requests

from configparser import ConfigParser

def lambda_handler(event, context):
  try:
    print("**STARTING**")
    print("**lambda: proj03_jobs**")
    
    #
    # setup AWS based on config file:
    #
    config_file = 'benfordapp-config.ini'
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = config_file
    
    configur = ConfigParser()
    configur.read(config_file)
    
    #
    # get the authentication token from the request headers:
    #
    print("**Accessing request headers to get authenticated user info**")
    
    if "headers" not in event:
      msg = "no headers in request"
      print("**ERROR:", msg)
      return {
        'statusCode': 400,
        'body': json.dumps(msg)
        
      }
      
    headers = event["headers"]
    
    if "Authentication" not in headers:
      msg = "no security credentials"
      print("**ERROR:", msg)
      return {
        'statusCode': 401,
        'body': json.dumps(msg)
      }
      
    token = headers['Authentication']
    
    #
    # is the token valid? Ask authentication service...
    #
    auth_url = configur.get('auth', 'webservice')
    data = {"token": token}
    api = '/auth'
    url = auth_url + api
    response = requests.post(url, json=data)
    
    if response.status_code != 200:
      msg = "authentication failure"
      return {
        'statusCode': 401,
        'body': json.dumps(msg)
      }
    
    #
    # configure for S3 access:
    #
    s3_profile = 's3readonly'
    boto3.setup_default_session(profile_name=s3_profile)
    
    bucketname = configur.get('s3', 'bucket_name')
    
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucketname)
    
    #
    # configure for RDS access
    #
    rds_endpoint = configur.get('rds', 'endpoint')
    rds_portnum = int(configur.get('rds', 'port_number'))
    rds_username = configur.get('rds', 'user_name')
    rds_pwd = configur.get('rds', 'user_pwd')
    rds_dbname = configur.get('rds', 'db_name')

    #
    # open connection to the database:
    #
    print("**Opening connection**")
    
    dbConn = datatier.get_dbConn(rds_endpoint, rds_portnum, rds_username, rds_pwd, rds_dbname)
    
    #
    # now retrieve all the jobs:
    #
    print("**Retrieving data**")
    
    sql = "SELECT userid FROM tokens WHERE token = %s";
    
    user_id = datatier.retrieve_one_row(dbConn, sql, [token])
    
    sql = "SELECT * FROM jobs WHERE userid = %s ORDER BY jobid";
    
    rows = datatier.retrieve_all_rows(dbConn, sql,[user_id])
    
    for row in rows:
      print(row)

    #
    # respond in an HTTP-like way, i.e. with a status
    # code and body in JSON format:
    #
    print("**DONE, returning rows**")
    
    return {
      'statusCode': 200,
      'body': json.dumps(rows)
    }
    
  except Exception as err:
    print("**ERROR**")
    print(str(err))
    
    return {
      'statusCode': 400,
      'body': json.dumps(str(err))
    }