#!/usr/bin/python
#
#    cleanup_old_files.py
#
#    Downloads McAfee's superdat exe update installer
#
#    Copyright (C) 2009 Georg Lutz <georg AT NOSPAM georglutz DOT de>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import ftplib
import logging
import optparse
import os
import re
import shutil
import stat
import sys
import tempfile
import types

VERSIONSTRING = "0.1"
sdatPattern = "(sdat\d{4}\.exe)"
sdatFile = ""
tmpFile = (0, "")


def findFtpSdatFile(text):
    '''Tries to find the filename of a sdat file in ftp server answer to LIST
    command and stores it in global variable SdatFile'''
    result = re.search(sdatPattern, text )
    if type(result) != types.NoneType and len(result.groups()) == 1:
	# @todo: How can filename be passed back without use of global variables?
	global sdatFile
	sdatFile = result.groups()[0]
    return


def writeFtpFile(buffer):
    '''Callback function for writing ftp data into file'''
    # @todo: How can filedescriptor be passed without use of global variables?
    global tmpFile
    os.write(tmpFile[0], buffer)



########### MAIN PROGRAM #############
def main():
    global sdatFile
    ftpServer = "ftp.nai.com"

    parser = optparse.OptionParser(
	    usage="%prog [options] directory",
	    version="%prog " + VERSIONSTRING + os.linesep +
	    "Copyright (C) 2009 Georg Lutz <georg AT NOSPAM georglutz DOT de>",
	    epilog = "directory: Where to store the superdat updates") #+ os.linesep +
    
    parser.add_option("-f", "--force", dest="force",
	    default=False, action="store_true",
	    help="Force re-download of current superdat even if it exists in directory and the size matches.")
    parser.add_option("-d", "--debuglevel", dest="debuglevel",
	    type="int", default=logging.WARNING,
	    help="Sets numerical debug level, see library logging module. Default is 30 (WARNING). Possible values are CRITICAL 50, ERROR 40, WARNING 30, INFO 20, DEBUG 10, NOTSET 0. All log messages with debuglevel or above are printed. So to disable all output set debuglevel e.g. to 100.")
    parser.add_option("-k", "--keep", dest="keep",
	    type="int", default=2,
	    help="Maximum nr of sdat files to keep locally after download. Default is 2")
    parser.add_option("-t", "--testmode", dest="testmode",
	    default=False, action="store_true",
	    help="Run in test mode. Instead of using ftp.nai.com localhost will be used")

    (options, args) = parser.parse_args()

    logging.basicConfig(format="%(message)s", level=options.debuglevel)

    if len(args) < 1:
	parser.print_help()
	sys.exit(2)

    if options.keep <= 0:
	logging.error("Please provice only reasonable values for --keep option")
	sys.exit(1)

    
    dirName = os.path.expanduser(args[0])
    if not os.path.isdir(dirName):
	logging.error("directory not found")
	sys.exit(1)

    localFiles = {}
    try:
	for entry in os.listdir(dirName):
	    path = os.path.join(dirName, entry)
	    if os.path.isfile(path):
		localFiles[entry] = os.path.getsize(path)
    except:
	logging.error("directory cannot be acccessed")
	sys.exit(1)


    if options.testmode:
	ftpServer = "localhost"
    ftp = ftplib.FTP()
    if options.debuglevel >= logging.debug:
	ftp.set_debuglevel(2)
    else:
	ftp.set_debuglevel(0)

    try:
	ftp.connect(ftpServer)
    except:
	logging.error("Cannot connect to ftp server \"%s\". Aborting." % ftpServer)
	sys.exit(1) 
    try:
	ftp.login()
    except:
	logging.error("FTP server refused anonymous login. Aborting")
	sys.exit(1)
    try:
	ftp.cwd("/pub/datfiles/german")
	ftp.retrlines('LIST', findFtpSdatFile)
    except:
	logging.error("Cannot list remote directory \"/pub/datfiles/german\". Aborting")
	sys.exit(1)

    if len(sdatFile) == 0 :
	logging.error("No sdat file found at server. Aborting")
	sys.exit(1)
    logging.info("Found sdat file %s on server" % sdatFile)
    
    try:
	sdatFileSize = ftp.size(sdatFile)
    except:
	logging.warn("Cannot get size of sdat file. Disabling size check")
	sdatFileSize = -1
    if sdatFileSize > 0 and not (sdatFileSize > 90000000 and sdatFileSize < 150000000):
	logging.warn("Server reported suspecious sdat file size of %d" % sdatFileSize)
    else:
	logging.info("sdat file %s has size of %d bytes" % (sdatFile, sdatFileSize))

    if localFiles.has_key(sdatFile):
	if localFiles[sdatFile] == sdatFileSize:
	    if options.force:
		logging.info("sdat file already exists in local directory and size also matches. Force option is set. Continuing")
	    else:
		logging.info("sdat file already exists in local directory and size also matches. Aborting")
		sys.exit(0)
	else:
	    logging.info("sdat file already exists in local directory but size (%d) does not match. Perhaps an broken previous dowload? Continuing" % localFiles[sdatFile])
    else:
	logging.info("sdat file does not exist in local directory. Continuing")


    # mkstemp() returns a tuple containing an OS-level handle to an open file (as would be returned by os.open()) and the absolute pathname of that file, in that order. New in version 2.3.
    global tmpFile
    tmpFile = tempfile.mkstemp("", "vscan_superdat_updater")

    logging.info("Downloading...")
    try:
	ftp.retrbinary('RETR %s' % sdatFile, writeFtpFile)
    except:
	logging.error("Not possible to download file from ftp server. Aborting.")
	sys.exit(1)
    os.close(tmpFile[0])
    ftp.quit()
    logging.info("Download ended.")

    if os.path.getsize(tmpFile[1]) != sdatFileSize :
	logging.error("Downloaded sdat file doesn't has correct size, aborting")
	sys.exit(1)
    
    targetFile = os.path.join(dirName, sdatFile)

    try:
	shutil.move(tmpFile[1], targetFile)
	os.chmod(targetFile, stat.S_IRUSR +stat.S_IWUSR + stat.S_IRGRP + stat.S_IROTH)
    except:
	logging.error("Temporary downloaded sdat %s cannot be moved to target %s. Aborting" % (tmpFile[1], targetFile))
	sys.exit(1)

    localFiles = []
    try:
	for entry in os.listdir(dirName):
	    path = os.path.join(dirName, entry)
	    if os.path.isfile(path):
		result = re.search(sdatPattern, entry )
		if type(result) != types.NoneType and len(result.groups()) == 1:
		    sdatFile = result.groups()[0]
		    localFiles.append(result.groups()[0])
    except:
	logging.error("directory cannot be acccessed")
	sys.exit(1)

    if len(localFiles) > options.keep:
	localFiles.sort()
	i = 0
	while len(localFiles) - i > options.keep:
	    path = os.path.join(dirName, localFiles[i])
	    try:
		logging.info("Removing file %s" % path)
		os.unlink(path)
	    except:
		logging.error("File %s could not be removed" % path)
	    i = i + 1


if __name__ == "__main__":
    main()

