Python Backup Scripts
=============

Python scripts for incremental backups of servers.  This includes filesystem 
backups and mysql backups.  

Pulled Backups
===========
Pulled filesystem backups are done through the incrbackup.py script.  Backups
are pulled down from remote systems to the backup server for security, the 
backup server can get to the remote systems being backed up but not vice versa.
Hence if a remote system is compromised the backup server isn't.

Pulled backups use rsync and hard links to keep multiple copies of one or 
more filesystems while using minimal space.  If backing up remote
servers this script assumes that the proper ssh keys have been setup from the
backup server hosting this script to the servers being backed up.

Backup paths can be either local or remote.  The backup directory where
the backups are stored must be local and must already exist.  If a users isn't
specified then the remote user used by ssh for rsync is considered to be a 
user named backup.

Use the -h or the --help flag to get a listing of options.

    incrbackup.py [-hnksctu]
       [-h | --help] prints this help and usage message
       [-n | --name] backup namespace
       [-k | --keep] number of backups to keep before deleting
       [-s | --server] the server to backup, if remote
       [-c | --config] configuration file with backup paths
       [-t | --store] directory locally to store the backups
       [-u | --user] the remote username used to ssh for backups

Backups read their include and exclude paths from a config file specified using
the -f option.  The config file looks like this.  Exclude paths follow rsync
exclude filter rules.

    {
      "backup" : [
        "/path/to/include",
        "/another/path/to/include"
      ],
      "exclude" : [
        "*.filetype.to.exclude",
        "*.another.to.exclude",
        "/path/to/exclude",
        "/another/path/to/exclude"
      ]
    }

Usually the backup scripts are run from a remote, off-site, server pulling down
content from the servers to backup.  Scripts are usually setup to run from cron
periodically.


Pushed Filesystem Backups
===========
Pushed filesystem backups are done through the pushbackup.py script.

This is an incremental backup system that pushes to a remote server.  Useful
for remote systems that aren't always on (laptops).  Backups use rsync and hard 
links to keep multiple full copies while using minimal space.  It is assumed
that the rotatebackups.py script exists on the remote backup server and that
the proper ssh keys have been setup from the pushing server to the backup
server.

Use the -h or the --help flag to get a listing of options.

    pushbackup.py [-hnksctuxr]
       [-h | --help] prints this help and usage message
       [-n | --name] backup namespace
       [-k | --keep] number of backups to keep before deleting
       [-s | --server] the server to push to backup to
       [-c | --config] configuration file with backup paths
       [-t | --store] directory locally to store the backups
       [-u | --user] the remote username used to ssh for backups
       [-x | --ssh-key] the ssh key used to connect to the backup
       [-r | --rotate-script] the rotatebackups script remote location

Pushed backup use the same config format as pulled backups.  Pushed backups are
usually run manually when needed.  They should not be used to backup servers due
to security reasons.  If backing up server filesystem see pulled backups.

MySQL Backups
===========
MySQL backups are done through the mysqlbackup.py script.

Use the -h or the --help flag to get a listing of options.

    mysqlbackup.py [-hkdbups]
       [-h | --help] prints this help and usage message
       [-k | --keep] number of days to keep backups before deleting
       [-d | --databases] a comma separated list of databases
       [-t | --store] directory locally to store the backups
       [-u | --user] the database user
       [-p | --password] the database password
       [-s | --host] the database server hostname
       [-o | --options] the json file to load the options from instead of using command line
       [-r | --restore] enables restore mode

License and Bug Fixes
===========
These works are public domain or licensed under the Apache Licene. You can do
anything you want with them.  Please feel free to send any improvements or 
bug fixes.