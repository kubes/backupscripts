#!/usr/bin/python

import sys
import string
import shutil
import getopt
import os
import os.path
import syslog
import errno
import logging
import tempfile
import datetime
import subprocess
import json
import rotatebackups

from operator import itemgetter

"""
-----------------------------------------------------------------------------
An incremental backup system that uses rsync and hard links to keep multiple
backups of one or more systems while using minimal space.  If backing up remote
servers this script assumes that the proper ssh keys have been setup from the
backup server hosting this script to the servers being backed up.

A pid file is placed into the system temp directory to prevent concurrent 
backups from running at once.  The script provides options for the number of 
backups to keep.  After the max number of backups is reached, backups are 
deleted starting with the oldest backup first.

Backup paths can be either local or remote.  The backup root directory where
the backups are stored must be local and must already exist.  If a users isn't
specified then the remote user used by ssh for rsync is considered to be root.

Use the -h or the --help flag to get a listing of options.

Program: Incremental Backups
Author: Dennis E. Kubes
Date: August 01, 2011
Revision: 1.2

Revision      | Author            | Comment
-----------------------------------------------------------------------------
20111122-1.0  Dennis E. Kubes     Initial creation of script.
20131430-1.2  Dennis E. Kubes     Added excludes logic, config json file.
-----------------------------------------------------------------------------
"""
class IncrementalBackup:

  def __init__(self, name="backup", server=None, keep=90, store=None, 
    config_file=None, user="root"):
    self.name = name
    self.server = server
    self.keep = keep
    self.config_file = config_file
    self.store = store
    self.user = user
    
  def run_command(self, command=None, shell=False, ignore_errors=False, 
    ignore_codes=None):
    result = subprocess.call(command, shell=False)
    if result and not ignore_errors and (not ignore_codes or result in set(ignore_codes)):
      raise BaseException(str(command) + " " + str(result))
        
  def backup(self):

    # rotate the backups
    rotater = rotatebackups.RotateBackups(self.keep, self.store)
    rotated_names = rotater.rotate_backups()

    rsync_to = None
    if not rotated_names:
      # get the current date and timestamp and the zero backup name
      now = datetime.datetime.now()
      padding = len(str(self.keep))
      tstamp = now.strftime("%Y%m%d%H%M%S")
      zbackup_name = string.join(["".zfill(padding), tstamp, self.name], ".")
      rsync_to = self.store + os.sep + zbackup_name
    else:
      rsync_to = rotated_names[0]
    
    # create the base rsync command with excludes
    rsync_base = ["rsync", "-avR", "--ignore-errors", "--delete", "--delete-excluded"]
    
    # get the paths to backup either from the command line or from a paths file
    bpaths = []
    expaths = []
    if self.config_file:

      pf = open(self.config_file, "r")
      config = json.load(pf)
      pf.close()

      # add the paths to backup
      bpaths.extend(config["backup"])

      # add and filter/exclude options
      if "exclude" in config:
        for exclude in config["exclude"]:
          rsync_base.extend(["--exclude", exclude])
    
    # one rsync command per path, ignore files vanished errors
    for bpath in bpaths:
      bpath = bpath.strip()
      rsync_cmd = rsync_base[:]      
      if self.server:
        bpath = self.user + "@" + self.server + ":" + bpath
      rsync_cmd.append(bpath)
      rsync_cmd.append(rsync_to)
      logging.debug(rsync_cmd)
      self.run_command(command=rsync_cmd, ignore_errors=True)

"""
Prints out the usage for the command line.
"""
def usage():
  usage = ["incrbackup.py [-hnksftu]\n"]
  usage.append("  [-h | --help] prints this help and usage message\n")
  usage.append("  [-n | --name] backup namespace\n")
  usage.append("  [-k | --keep] number of backups to keep before deleting\n")
  usage.append("  [-s | --server] the server to backup, if remote\n")
  usage.append("  [-f | --config] configuration file with backup paths\n")
  usage.append("  [-t | --store] directory locally to store the backups\n")
  usage.append("  [-u | --user] the remote username used to ssh for backups\n")
  message = string.join(usage)
  print message

"""
Main method that starts up the backup.  
"""
def main(argv):

  # set the default values
  pid_file = tempfile.gettempdir() + os.sep + "incrbackup.pid"
  name = "backup"
  keep = 90
  server = None
  config_file = None
  store = None
  user = "backup"
                   
  try:
    
    # process the command line options   
    opts, args = getopt.getopt(argv, "hn:k:s:f:t:u:", ["help", "name=", 
      "keep=", "server=", "config=", "store=", "user="])
    
    # if no arguments print usage
    if len(argv) == 0:      
      usage()                    
      sys.exit()   
            
    # loop through all of the command line options and set the appropriate
    # values, overriding defaults
    for opt, arg in opts:                
      if opt in ("-h", "--help"):      
        usage()                    
        sys.exit()
      elif opt in ("-n", "--name"):                
        name = arg
      elif opt in ("-k", "--keep"):                
        keep = int(arg)
      elif opt in ("-s", "--server"):                
        server = arg                
      elif opt in ("-f", "--config"): 
        config_file = arg
      elif opt in ("-t", "--store"): 
        store = arg
      elif opt in ("-u", "--user"): 
        user = arg
                                       
  except getopt.GetoptError, msg:
    # if an error happens print the usage and exit with an error       
    usage()                          
    sys.exit(errno.EIO)

  # check options are set correctly
  if config_file == None or store == None:
    usage()                          
    sys.exit(errno.EPERM)

  # process backup, catch any errors, and perform cleanup
  try:
  
    # another backup can't already be running, if pid file doesn't exist, then
    # create it
    if os.path.exists(pid_file):
      logging.warning("Backup running, %s pid exists, exiting." % pid_file)
      sys.exit(errno.EBUSY)
    else:
      pid = str(os.getpid())
      f = open(pid_file, "w")
      f.write("%s\n" % pid)
      f.close()
      
    # create the backup object and call its backup method
    ibackup = IncrementalBackup(name, server, keep, store, config_file, user)
    ibackup.backup()

  except(Exception):            
    logging.exception("Incremental backup failed.")      
  finally:
    os.remove(pid_file)
      
# if we are running the script from the command line, run the main function
if __name__ == "__main__":
  main(sys.argv[1:])


