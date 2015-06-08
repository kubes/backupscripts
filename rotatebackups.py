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

from operator import itemgetter

"""
-----------------------------------------------------------------------------
Rotates backup folders, keeping a given number of backups and deleting older
backups.

Use the -h or the --help flag to get a listing of options.

Program: Rotate Backups
Author: Dennis E. Kubes
Date: May 01, 2013
Revision: 1.0

Revision      | Author            | Comment
-----------------------------------------------------------------------------
20130501-1.0  Dennis E. Kubes     Initial creation of script.
-----------------------------------------------------------------------------
"""
class RotateBackups:

  def __init__(self, keep=90, store=None, name=None):
    self.keep = keep
    self.store = store
    self.name = name

  def run_command(self, command=None, shell=False, ignore_errors=False, 
    ignore_codes=None):
    result = subprocess.call(command, shell=False)
    if result and not ignore_errors and (not ignore_codes or result in set(ignore_codes)):
      raise BaseException(str(command) + " " + str(result))

  def rotate_backups(self):

    padding = len(str(self.keep))

    backups = []
    final_backup_names = []
    
    # add the backup directories to a list, dirs are the form num.prefix.date
    for backup_dir in os.listdir(self.store):
      bparts = backup_dir.split(".")
      if bparts[0].isdigit():
        backups.append((backup_dir, bparts))
    
    # only need to process backup directories if we have some
    if len(backups) > 0:
    
      # order the backups in the list by reverse number, highest first
      backups = sorted(backups, key=itemgetter(0), reverse=True)

      # perform shifting and processing on the backup directories
      for btup in backups:

        # unpack the original directory and backup parts
        origdir = btup[0]
        bparts = btup[1]
      
        # remove backups >= number of days to keep
        bnum = int(bparts[0])
        if bnum >= self.keep:
          bpath = self.store + os.sep + origdir
          logging.debug(["rm", "-fr", bpath])
          self.run_command(["rm", "-fr", bpath])
        else:
        
          # above 0 gets shifted to one number higher and moved, 0 gets hardlink
          # copied to 1 if it is a directory.  If 0 is file assumed that another
          # process will write out the new 0 file
          base_path = os.path.abspath(self.store)
          old_bpath = base_path + os.sep + origdir
          num_prefix = str(bnum + 1).zfill(padding)
          incr_name = num_prefix + "." + string.join(bparts[1:], ".")
          new_bpath = base_path + os.sep + incr_name        
          if bnum > 0:
            logging.debug([bnum, "mv", old_bpath, new_bpath])
            self.run_command(["mv", old_bpath, new_bpath])
            final_backup_names.append(new_bpath)

          elif bnum == 0:

            if os.path.isdir(old_bpath):
              logging.debug(["cp", "-al", old_bpath, new_bpath])          
              self.run_command(["cp", "-al", old_bpath, new_bpath])
              final_backup_names.append(new_bpath)

              # get the current date and timestamp and create the zero backup path
              now = datetime.datetime.now()
              tstamp = now.strftime("%Y%m%d%H%M%S")
              zero_parts = ["".zfill(padding), tstamp]
              zero_parts.extend(bparts[2:])
              zbackup_path = base_path + os.sep + string.join(zero_parts, ".")
  
              # move the zero directory to the new timestamp
              logging.debug([0, "mv", old_bpath, zbackup_path])   
              self.run_command(["mv", old_bpath, zbackup_path])
              final_backup_names.append(zbackup_path)

            else:
              logging.debug(["mv",  old_bpath, new_bpath])          
              self.run_command(["mv", old_bpath, new_bpath])
              final_backup_names.append(new_bpath)

    # return the final backup file or directory names, most recent to least
    final_backup_names.reverse()
    return final_backup_names                  


"""
Prints out the usage for the command line.
"""
def usage():
  usage = ["rotatebackups.py [-hkt]\n"]
  usage.append("  [-h | --help] prints this help and usage message\n")
  usage.append("  [-k | --keep] number of backups to keep before deleting\n")
  usage.append("  [-t | --store] directory locally to store the backups\n")
  message = string.join(usage)
  print message

"""
Main method that starts up the backup.  
"""
def main(argv):

  # set the default values
  pid_file = tempfile.gettempdir() + os.sep + "rotbackup.pid"
  keep = 90
  store = None
  padding = 5
                   
  try:
    
    # process the command line options   
    opts, args = getopt.getopt(argv, "hk:t:p:", ["help", "keep=", "store="])
    
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
      elif opt in ("-t", "--store"): 
        store = arg
                                       
  except getopt.GetoptError, msg:
    # if an error happens print the usage and exit with an error       
    usage()                          
    sys.exit(errno.EIO)

  # check options are set correctly
  if store == None:
    usage()                          
    sys.exit(errno.EPERM)

  # process, catch any errors, and perform cleanup
  try:
  
    # another rotate can't already be running
    if os.path.exists(pid_file):
      logging.warning("Rotate backups running, %s pid exists, exiting." % pid_file)
      sys.exit(errno.EBUSY)
    else:
      pid = str(os.getpid())
      f = open(pid_file, "w")
      f.write("%s\n" % pid)
      f.close()
      
    # create the backup object and call its backup method
    rotback = RotateBackups(keep, store)
    rotated_names = rotback.rotate_backups()
    if (len(rotated_names) > 0):
      print("\n".join(rotated_names))

  except(Exception):            
    logging.exception("Rotate backups failed.")      
  finally:
    os.remove(pid_file)
      
# if we are running the script from the command line, run the main function
if __name__ == "__main__":
  main(sys.argv[1:])
