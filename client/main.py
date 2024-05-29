#
# Client-side python app for benford app, which is calling
# a set of lambda functions in AWS through API Gateway.
# The overall purpose of the app is to process a PDF and
# see if the numeric values in the PDF adhere to Benford's
# law.
#
# Authors:
#   Natalie Cheng
#
#   Prof. Joe Hummel (initial template)
#   Northwestern University
#   CS 310
#

import requests
import jsons

import uuid
import pathlib
import logging
import sys
import os
import base64

from configparser import ConfigParser
from getpass import getpass


############################################################
#
# classes
#
class User:

  def __init__(self, row):
    self.userid = row[0]
    self.username = row[1]
    self.pwdhash = row[2]


class Job:

  def __init__(self, row):
    self.jobid = row[0]
    self.userid = row[1]
    self.status = row[2]
    self.originaldatafile = row[3]
    self.datafilekey = row[4]
    self.resultsfilekey = row[5]


############################################################
#
# prompt
#
def prompt():
  """
  Prompts the user and returns the command number

  Parameters
  ----------
  None

  Returns
  -------
  Command number entered by user (0, 1, 2, ...)
  """
  print()
  print(">> Enter a command:")
  print("   0 => end")
  print("   1 => users")
  print("   2 => jobs")
  print("   3 => reset database")
  print("   4 => upload pdf")
  print("   5 => download results")
  print("   6 => upload and poll")
  print("   7 => login")
  print("   8 => authenticate token")
  print("   9 => logout")

  cmd = input()

  if cmd == "":
    cmd = -1
  elif not cmd.isnumeric():
    cmd = -1
  else:
    cmd = int(cmd)

  return cmd


############################################################
#
# users
#
def users(baseurl):
  """
  Prints out all the users in the database

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  try:
    #
    # call the web service:
    #
    api = '/users'
    url = baseurl + api

    res = requests.get(url)

    #
    # let's look at what we got back:
    #
    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:
        # we'll have an error message
        body = res.json()
        print("Error message:", body)
      #
      return

    #
    # deserialize and extract users:
    #
    body = res.json()

    #
    # let's map each row into a User object:
    #
    users = []
    for row in body:
      user = User(row)
      users.append(user)
    #
    # Now we can think OOP:
    #
    if len(users) == 0:
      print("no users...")
      return

    for user in users:
      print(user.userid)
      print(" ", user.username)
      print(" ", user.pwdhash)
    #
    return

  except Exception as e:
    logging.error("users() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return


############################################################
#
# jobs
#
def jobs(baseurl, token):
  """
  Prints out all the jobs in the database

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  if not token:
    print("No current token, please login")
    return

  try:
    #
    # call the web service:
    #
    api = '/jobs'
    url = baseurl + api

    #
    # make request:
    #
    req_header = {"Authentication": token}
    res = requests.get(url, headers=req_header)

    #
    # let's look at what we got back:
    #
    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400 or res.status_code == 401:
        # we'll have an error message
        body = res.json()
        print(body)
      return

    #
    # deserialize and extract jobs:
    #
    body = res.json()
    #
    # let's map each row into an Job object:
    #
    jobs = []
    for row in body:
      job = Job(row)
      jobs.append(job)
    #
    # Now we can think OOP:
    #
    if len(jobs) == 0:
      print("no jobs...")
      return

    for job in jobs:
      print(job.jobid)
      print(" ", job.userid)
      print(" ", job.status)
      print(" ", job.originaldatafile)
      print(" ", job.datafilekey)
      print(" ", job.resultsfilekey)
    #
    return

  except Exception as e:
    logging.error("jobs() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return


############################################################
#
# reset
#
def reset(baseurl):
  """
  Resets the database back to initial state.

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  try:
    #
    # call the web service:
    #
    api = '/reset'
    url = baseurl + api

    res = requests.delete(url)

    #
    # let's look at what we got back:
    #
    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:
        # we'll have an error message
        body = res.json()
        print("Error message:", body)
      #
      return

    #
    # deserialize and print message
    #
    body = res.json()

    msg = body

    print(msg)
    return

  except Exception as e:
    logging.error("reset() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return


############################################################
#
# upload
#
def upload(baseurl):
  """
  Prompts the user for a local filename and user id, 
  and uploads that asset (PDF) to S3 for processing. 

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  print("Enter PDF filename>")
  local_filename = input()

  if not pathlib.Path(local_filename).is_file():
    print("PDF file '", local_filename, "' does not exist...")
    return

  print("Enter user id>")
  userid = input()

  try:
    #
    # build the data packet:
    #
    infile = open(local_filename, "rb")
    bytes = infile.read()
    infile.close()

    #
    # now encode the pdf as base64. Note b64encode returns
    # a bytes object, not a string. So then we have to convert
    # (decode) the bytes -> string, and then we can serialize
    # the string as JSON for upload to server:
    #
    data = base64.b64encode(bytes)
    datastr = data.decode()

    data = {"filename": local_filename, "data": datastr}

    #
    # call the web service:
    #
    api = '/pdf'
    url = baseurl + api + "/" + userid

    res = requests.post(url, json=data)

    #
    # let's look at what we got back:
    #
    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:
        # we'll have an error message
        body = res.json()
        print("Error message:", body)
      #
      return

    #
    # success, extract jobid:
    #
    body = res.json()

    jobid = body

    print("PDF uploaded, job id =", jobid)
    return

  except Exception as e:
    logging.error("upload() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return


############################################################
#
# download
#
def download(baseurl):
  """
  Prompts the user for the job id, and downloads
  that asset (PDF).

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  print("Enter job id>")
  jobid = input()

  try:
    #
    # call the web service:
    #
    api = '/results'
    url = baseurl + api + '/' + jobid

    res = requests.get(url)

    #
    # let's look at what we got back:
    #
    if res.status_code != 200:
      #
      # failed: but "failure" with download is how status
      # is returned, so let's look at what we got back
      #
      msg = res.json()

      if msg.startswith("uploaded"):
        print("No results available yet...")
        print("Job status:", msg)
        return

      if msg.startswith("processing"):
        print("No results available yet...")
        print("Job status:", msg)
        return

      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:
        # we'll have an error message
        body = res.json()
        print("Error message:", body)
      #
      return

    #
    # if we get here, status code was 200, so we
    # have results to deserialize and display:
    #
    body = res.json()

    datastr = body

    base64_bytes = datastr.encode()
    bytes = base64.b64decode(base64_bytes)
    results = bytes.decode()

    print(results)
    return

  except Exception as e:
    logging.error("download() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return


############################################################
#
# upload_and_poll
#
def upload_and_poll(baseurl):
  """
  Prompts the user for a local filename and user id, 
  and uploads that asset (PDF) to S3 for processing. 

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  print("Enter PDF filename>")
  local_filename = input()

  if not pathlib.Path(local_filename).is_file():
    print("PDF file '", local_filename, "' does not exist...")
    return

  print("Enter user id>")
  userid = input()

  try:
    #
    # build the data packet:
    #
    infile = open(local_filename, "rb")
    bytes = infile.read()
    infile.close()

    #
    # now encode the pdf as base64. Note b64encode returns
    # a bytes object, not a string. So then we have to convert
    # (decode) the bytes -> string, and then we can serialize
    # the string as JSON for upload to server:
    #
    data = base64.b64encode(bytes)
    datastr = data.decode()

    data = {"filename": local_filename, "data": datastr}

    #
    # call the web service to upload the PDF:
    #
    api = '/pdf'
    url = baseurl + api + "/" + userid

    res = requests.post(url, json=data)

    #
    # let's look at what we got back:
    #
    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:
        # we'll have an error message
        body = res.json()
        print("Error message:", body)
      #
      return

    #
    # success, extract jobid:
    #
    body = res.json()

    jobid = body

    print("uploaded, jobid:", jobid)
    print("now we poll for results...")
    print()

    #
    # now let's poll until results are ready:
    #
    while True:
      api = '/results'
      url = baseurl + api + '/' + jobid

      res = requests.get(url)

      #
      # let's look at what we got back:
      #
      if res.status_code == 200:
        print("status: completed")
        break

      if res.status_code == 400:
        #
        # failed: but "failure" with download is how status
        # is returned, so let's look at what we got back
        #
        msg = res.json()

        if msg.startswith("uploaded"):
          print("status:", msg)
          continue

        if msg.startswith("processing"):
          print("status:", msg)
          continue

        if msg.startswith("error"):
          print("status:", msg)
          return

        #
        # if get here, unknown error / status, print and
        # break out of loop
        #
        print("ERROR: failed with status code:", res.status_code)
        print(msg)
        return

      #
      # if get here, unknown error / status, print and
      # break out of loop:
      #
      print("ERROR: failed with status code:", res.status_code)
      return

    #
    # if we get here, status code was 200, so we have
    # results to display
    #
    body = res.json()

    datastr = body

    base64_bytes = datastr.encode()
    bytes = base64.b64decode(base64_bytes)
    results = bytes.decode()

    print()
    print(results)
    return

  except Exception as e:
    logging.error("upload() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return


############################################################
#
# login
#
def login(baseurl):
  """
  Prompts the user for a username and password, then tries
  to log them in. If successful, returns the token returned
  by the authentication service.

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  token if successful, None if not
  """

  try:
    username = input("username: ")
    password = getpass()
    duration = input("# of minutes before expiration? ")

    #
    # build message:
    #
    data = {"username": username, "password": password, "duration": duration}

    #
    # call the web service to upload the PDF:
    #
    api = '/auth'
    url = baseurl + api

    res = requests.post(url, json=data)

    #
    # clear password variable:
    #
    password = None

    #
    # let's look at what we got back:
    #
    if res.status_code == 401:
      #
      # authentication failed:
      #
      body = res.json()
      print(body)
      return None

    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:
        # we'll have an error message
        body = res.json()
        print("Error message:", body)
      #
      return

    #
    # success, extract token:
    #
    body = res.json()

    token = body

    print("logged in, token:", token)
    return token

  except Exception as e:
    logging.error("login() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return None


############################################################
#
# authenticate
#
def authenticate(baseurl, token):
  """
  Since tokens expire, this function authenticates the 
  current token to see if still valid. Outputs the result.

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  try:
    if token is None:
      print("No current token, please login")
      return

    print("token:", token)

    #
    # build message:
    #
    data = {"token": token}

    #
    # call the web service to upload the PDF:
    #
    api = '/auth'
    url = baseurl + api

    res = requests.post(url, json=data)

    #
    # let's look at what we got back:
    #
    if res.status_code == 401:
      #
      # authentication failed:
      #
      body = res.json()
      print(body)
      return

    if res.status_code != 200:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 400:
        # we'll have an error message
        body = res.json()
        print("Error message:", body)
      #
      return

    #
    # success, token is valid:
    #
    print("token is valid!")
    return

  except Exception as e:
    logging.error("authenticate() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return


############################################################
# main
#
try:
  print('** Welcome to BenfordApp with Authentication **')
  print()

  # eliminate traceback so we just get error message:
  sys.tracebacklimit = 0

  #
  # what config file should we use for this session?
  #
  config_file = 'benfordapp-client-config.ini'

  print("Config file to use for this session?")
  print("Press ENTER to use default, or")
  print("enter config file name>")
  s = input()

  if s == "":  # use default
    pass  # already set
  else:
    config_file = s

  #
  # does config file exist?
  #
  if not pathlib.Path(config_file).is_file():
    print("**ERROR: config file '", config_file, "' does not exist, exiting")
    sys.exit(0)

  #
  # setup base URL to web service:
  #
  configur = ConfigParser()
  configur.read(config_file)
  baseurl = configur.get('client', 'webservice')

  #
  # make sure baseurl does not end with /, if so remove:
  #
  if len(baseurl) < 16:
    print("**ERROR: baseurl '", baseurl, "' is not nearly long enough...")
    sys.exit(0)

  if baseurl == "https://YOUR_GATEWAY_API.amazonaws.com":
    print("**ERROR: update config file with your gateway endpoint")
    sys.exit(0)

  if baseurl.startswith("http:"):
    print("**ERROR: your URL starts with 'http', it should start with 'https'")
    sys.exit(0)

  lastchar = baseurl[len(baseurl) - 1]
  if lastchar == "/":
    baseurl = baseurl[:-1]

  #
  # initialize login token:
  #
  token = None

  #
  # main processing loop:
  #
  cmd = prompt()

  while cmd != 0:
    #
    if cmd == 1:
      users(baseurl)
    elif cmd == 2:
      jobs(baseurl, token)
    elif cmd == 3:
      reset(baseurl)
    elif cmd == 4:
      upload(baseurl)
    elif cmd == 5:
      download(baseurl)
    elif cmd == 6:
      upload_and_poll(baseurl)
    elif cmd == 7:
      token = login(baseurl)
    elif cmd == 8:
      authenticate(baseurl, token)
    elif cmd == 9:
      #
      # logout
      #
      token = None
    else:
      print("** Unknown command, try again...")
    #
    cmd = prompt()

  #
  # done
  #
  print()
  print('** done **')
  sys.exit(0)

except Exception as e:
  logging.error("**ERROR: main() failed:")
  logging.error(e)
  sys.exit(0)