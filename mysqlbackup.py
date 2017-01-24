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
import readline
import json

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

def rlinput(prompt, prefill=''):
     readline.set_startup_hook(lambda: readline.insert_text(prefill))
     try:
        return raw_input(prompt)
     finally:
        readline.set_startup_hook()

def format_date(raw_date):
  return "%s-%s-%s %s:%s:%s" % (raw_date[0:4], raw_date[4:6], 
    raw_date[6:8], raw_date[8:10], raw_date[10:12], raw_date[12:14])

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
    ignore_codes=None, get_output=False, path="."):
    p = subprocess.Popen([command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=path)
    out, err = p.communicate()

    result = p.returncode
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
    
  def restore(self):    
    dbbackup_path = self.store + os.sep 
    backups = sorted(os.listdir(dbbackup_path), reverse=True)

    # show available options
    k = 1
    options = {}
    prev_date = ""
    databases = ""
    filenames = ""

    print "Available backups to restore:"
    for i in range(len(backups)):
      data = backups[i].split(".")
      date = data[0]

      if not prev_date:
        prev_date = date

      if (date != prev_date):
        print "["+str(k)+"]", "(%s) %s" % (format_date(prev_date), databases)

        options[k] = {
          "date": prev_date,
          "databases": databases,
          "filenames": filenames
        }

        k += 1
        prev_date = date
        databases = ""
        filenames = ""

      databases += ("" if databases == "" else ",") + data[1]
      filenames += ("" if filenames == "" else ",") + backups[i]

    print "["+str(k)+"]", "(%s) %s" % (format_date(prev_date), databases)
    options[k] = {
      "date": prev_date,
      "databases": databases,
      "filenames": filenames
    }

    # get the selection
    user_input = -1
    max_option = len(options.keys())
    while True:
      user_input = int(raw_input("\nSelect backup: "))
      if (user_input < 1) or (max_option < user_input):
        print "Error: The value should be between 1 and", max_option
      else:
        break
    
    # get the databases to restore
    date = format_date(options[user_input]["date"])
    filenames = options[user_input]["filenames"]
    selected_databases = rlinput("Databases to restore: ", options[user_input]["databases"])
    databases = ",".join(filter(lambda db: db in selected_databases, self.get_databases()))
    if databases == "":
      print "Error: The selected databases doesn't match any created databases."
      sys.exit()

    # ask for confirmation
    print "The databases \"%s\" are going to be restored using the version dated \"%s\"" % (databases, date)
    confirmation = rlinput("Continue? [Y/n] ", "Y")
    if confirmation != "Y":
      print "Aborted."
      sys.exit()

    # expand the filenames of the databases
    databases = databases.split(",")
    filenames = filter(lambda fln: reduce(lambda x,y: x or y, 
                        map(lambda dbn: dbn in fln, databases)), 
                      filenames.split(","))

    # restore the databases
    print
    for filename in filenames:
      db = filename.split(".")[1]
      restore_cmd = "gunzip < " + dbbackup_path + filename + \
        " | mysql -u " + self.user
      if self.host != None:
        restore_cmd += " -h " + "'" + self.host + "'"
      if self.password != None:
        restore_cmd += " -p" + self.password
      restore_cmd += " " + db

      print "Restoring \"" + db + "\"...",
      sys.stdout.flush()
      logging.info("Restore db, %s from %s." % (db, dbbackup_path + filename))
      self.run_command(restore_cmd)
      print "done"

    print "Restore complete!"

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
    dbs = self.get_databases()
    skip = ["information_schema", "performance_schema", "test"]
    for db in dbs:
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
  usage.append("  [-k | --keep] number of days to keep backups before deleting\n")
  usage.append("  [-d | --databases] a comma separated list of databases\n")
  usage.append("  [-t | --store] directory locally to store the backups\n")
  usage.append("  [-u | --user] the database user\n")
  usage.append("  [-p | --password] the database password\n")
  usage.append("  [-s | --host] the database server hostname\n")
  usage.append("  [-o | --options] the json file to load the options from instead of using command line\n")
  usage.append("  [-r | --restore] enables restore mode\n")
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
  options = None
  restore = False

  try:
    
    # process the command line options
    st = "hn:k:d:t:u:p:s:o:r"
    lt = ["help", "keep=", "databases=", "store=", "user=", "password=", 
        "host=", "options=", "restore"]
    opts, args = getopt.getopt(argv, st, lt)
    
    # if no arguments print usage
    if len(argv) == 0:
      usage()
      sys.exit()
    
    # detect if loading options from file and load the json
    vals = {}
    fopts = None
    for opt, arg in opts:
        vals[opt] = arg
    if ("-o" in vals.keys()) or ("--options" in vals.keys()):
      opt = "-o" if "-o" in vals.keys() else "--options"
      with open(vals[opt], 'r') as content_file:
        fopts = json.load(content_file)
    
    # merge with opts
    opts_keys = map(lambda val: val[0], opts)
    if fopts:
      for key in fopts.keys():
        prefix = ""
        if key in st.split(":"):
          prefix = "-"
        elif key in map(lambda t: t[:-1] if t[-1] == "=" else t, lt):
          prefix = "--"
        else:
          continue
        if prefix+key not in opts_keys:
          opts.append((prefix+key, fopts[key]))
            
    # loop through all of the command line options and set the appropriate
    # values, overriding defaults
    for opt, arg in opts:
      if opt in ("-h", "--help"):
        usage()
        sys.exit()
      elif opt in ("-k", "--keep"):
        keep = int(arg)
      elif opt in ("-d", "--databases"):
        databases = arg
      elif opt in ("-t", "--store"):
        store = arg
      elif opt in ("-u", "--user"):
        user = arg
      elif opt in ("-p", "--password"):
        password = arg
      elif opt in ("-s", "--host"):
        host = arg
      elif opt in ("-r", "--restore"):
        restore = True
           
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
    if restore:
        mysql_backup.restore()
    else:
        mysql_backup.backup()

  except(Exception):            
    logging.exception("Mysql backups failed.")      
  finally:
    os.remove(pid_file)
      
# if we are running the script from the command line, run the main function
if __name__ == "__main__":
  main(sys.argv[1:])
