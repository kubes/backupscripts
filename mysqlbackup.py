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

from operator import itemgetter

"""
-----------------------------------------------------------------------------
A script to backup mysql databases through the mysqldump utility.

Use the -h or the --help flag to get a listing of options.

Program: Mysql Database Backups
Author: Dennis E. Kubes
Date: April 28, 2013
Revision: 1.0

Revision      | Author            | Comment
-----------------------------------------------------------------------------
20130428-1.0    Dennis E. Kubes     Initial creation of script.
-----------------------------------------------------------------------------
"""
class MysqlBackup:

  def __init__(self, keep=90, databases=None, store=None, user="root", 
    password=None, host=None):
    self.host = host
    self.keep = keep
    self.databases = databases
    self.store = store
    self.user = user
    self.password = password
    self.host = host
    
  def run_command(self, command=None, shell=False, ignore_errors=False, 
    ignore_codes=None, get_output=False):
    result = subprocess.call(command, shell=False)
    if result and not ignore_errors and (not ignore_codes or result in set(ignore_codes)):
      raise BaseException(str(command) + " " + str(result))

  def get_databases(self):

    if self.databases != None:
      return [s.strip() for s in self.databases.strip().split(",")]

    list_cmd = "mysql -u" + self.user
    if self.host != None:
      list_cmd += " -h " + self.host
    if self.password != None:
      list_cmd += " -p" + self.password
    list_cmd += " --silent -N -e 'show databases'"
    databases = os.popen(list_cmd).readlines()
    return [s.strip() for s in databases]
        
  def backup(self):
    
    padding = len(str(self.keep))    
    backups = []
  
    # remove files older than keep days
    cutdate = datetime.datetime.now() - datetime.timedelta(days=self.keep)   
    for backup_file in os.listdir(self.store):
      bparts = backup_file.split(".")
      if bparts[0].isdigit():
        dumpdate = datetime.datetime.strptime(bparts[0], "%Y%m%d%H%M%S")
        if dumpdate < cutdate:
          os.remove(os.path.join(self.store, backup_file))
        
    # get the current date and timestamp and the zero backup name
    tstamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")    
    databases = self.get_databases()
    skip = ["information_schema", "performance_schema", "test"]
    for db in databases:
      if db in skip:
        continue

      dbbackup_name = string.join([tstamp, db, "sql"], ".")
      dbbackup_path = self.store + os.sep + dbbackup_name 

      dump_cmd = "mysqldump -u " + self.user
      if self.host != None:
        dump_cmd += " -h " + "'" + self.host + "'"
      if self.password != None:
        dump_cmd += " -p" + self.password
      dump_cmd += " -e --opt -c " + db + " | gzip > " + dbbackup_path + ".gz"
      logging.info("Dump db, %s to %s." % (db, dbbackup_path))
      os.popen(dump_cmd)

"""
Prints out the usage for the command line.
"""
def usage():
  usage = ["mysqlbackup.py [-hkdbups]\n"]
  usage.append("  [-h | --help] prints this help and usage message\n")
  usage.append("  [-k | --keep] number of backups to keep before deleting\n")
  usage.append("  [-d | --databases] a comma separated list of databases\n")
  usage.append("  [-t | --store] directory locally to store the backups\n")
  usage.append("  [-u | --user] the database user\n")
  usage.append("  [-p | --password] the database password\n")
  usage.append("  [-s | --host] the database server hostname\n")
  message = string.join(usage)
  print message

"""
Main method that starts up the backup.  
"""
def main(argv):

  # set the default values
  pid_file = tempfile.gettempdir() + os.sep + "mysqlbackup.pid"
  keep = 90
  databases = None
  user = None
  password = None
  host = None
  store = None
                   
  try:
    
    # process the command line options   
    opts, args = getopt.getopt(argv, "hn:k:d:t:u:p:s:", ["help", "keep=", 
      "databases=", "store=", "user=", "password=", "host="])
    
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
      elif opt in ("-k", "--keep"):                
        keep = int(arg)
      elif opt in ("-d", "--databases"):                
        server = arg                
      elif opt in ("-t", "--store"): 
        store = arg
      elif opt in ("-u", "--user"): 
        user = arg
      elif opt in ("-p", "--password"): 
        password = arg
      elif opt in ("-s", "--host"): 
        host = arg
                                       
  except getopt.GetoptError, msg:    
    logging.warning(msg)
    # if an error happens print the usage and exit with an error       
    usage()                          
    sys.exit(errno.EIO)

  # check options are set correctly
  if user == None or store == None:
    logging.warning("Backup store directory (-t) and user (-u) are required")
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
    mysql_backup = MysqlBackup(keep, databases, store, user, password, host)
    mysql_backup.backup()

  except(Exception):            
    logging.exception("Mysql backups failed.")      
  finally:
    os.remove(pid_file)
      
# if we are running the script from the command line, run the main function
if __name__ == "__main__":
  main(sys.argv[1:])