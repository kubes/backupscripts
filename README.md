Python Incremental Backup Scripts
=============

Python scripts for incremental backups of servers.  This includes filesystem 
backup and mysql backup.  


Filesystem Backups
===========
Filesystem backups are done through the incrbackup script.

Filesystem backups use rsync and hard links to keep multiple copies of one or 
more filesystems while using minimal space.  If backing up remote
servers this script assumes that the proper ssh keys have been setup from the
backup server hosting this script to the servers being backed up.

A pid file is placed into the system temp directory to prevent concurrent 
backups from running at once.  The script provides options for the number of 
backups to keep.  After the max number of backups is reached, backups are 
deleted starting with the oldest backup first.

Backup paths can be either local or remote.  The backup directory where
the backups are stored must be local and must already exist.  If a users isn't
specified then the remote user used by ssh for rsync is considered to be a 
user named backup.

Use the -h or the --help flag to get a listing of options.

    incremental_backup.py [-hnksftu]
       [-h | --help] prints this help and usage message
       [-n | --name] backup namespace
       [-k | --keep] number of backups to keep before deleting
       [-s | --server] the server to backup, if remote
       [-f | --config] configuration file with backup paths
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

MySQL Backups
===========
MySQL backups are done through the mysqlbackup script.

A pid file is placed into the system temp directory to prevent concurrent 
backups from running at once.  The script provides options for the number of 
backups to keep.  After the max number of backups is reached, backups are 
deleted starting with the oldest backup first.

Use the -h or the --help flag to get a listing of options.

    mysqlback [-hnkdbus]
       [-h | --help] prints this help and usage message
       [-k | --keep] number of backups to keep before deleting
       [-d | --databases] a comma separated list of databases
       [-b | --backup-root] directory locally to store the backups
       [-u | --user] the database user
       [-p | --password] the database password
       [-s | --host] the database server hostname

Please feel free to send any improvements or bug fixes.