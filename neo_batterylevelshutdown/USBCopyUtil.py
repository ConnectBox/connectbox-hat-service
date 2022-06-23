#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
This file is designed to be a subprocess to copy files from one location to USB's file structure

"""

import sys, getopt
import os, shutil
import logging


def main(argv):
	inputdir = ""
	outputdir = ""
	try:
		opts, args = getopt.getopt(argv, "hi:0:", [ "ifile=", "ofile="])								# gete the arguments passed to the probram
    except getopt.GetoptError:
    	logging.info("startup of USBCopyUtil with unknown arguments")
    	sys.exit(2)
    for opt, arg in opts:
    	if opt in ('-h', "--help"):																		# I'm asking for help
    		print 'USBCopyUtil.py -i <inputdir> -o <outputdir'
    		sys.exit()
    	elif opt in ("-i", "--indir"):																	# We have a valid input directory
    		inputdir = arg
     	elif opt in ("-0", "--odir"):																	# we have a valid output directory
     	    outputdir = arg
    if inputdir == "" or outputdir == "":
    	print("get paramaters with -h or --help")
    	logging.info(Closed USBCopyUtil.py due to lack of valid variabales)
    	sys.exit(2)																						# we didn't get valid paramaters
    if  ! os.path.isdir(outputdir):																		#Check output that its a valid directory
    	logging.info(Closed USBCopyUtil.py due to output path not being a direcotry)
    	sys.exit(2)

   	logging.info("Starting USBCopyUtil with "+inputdir+" copying to "+outputdir)
    try:
        if os.path.isdir(inputdir):																		# We check that we have a valid direcotry on input
            logging.info("Copying tree: "+inputdir+" to: "+outputdir)
            shutil.copytree(inputdir, outputdir, symlinks=False, copy_function=copy2, ignore_dangling_symlinks=True)
        else:
            logging.info("Copying: "+inputdir+" to: "+outputdir)										# We may just try a copy if the input directory is only a file.
            copy2(inputdir, outputdir)
        except OSError as err::
            errors.append((inputdir, outputdir, str(err)))												# We encountered an error so we stop.
        except BaseException as err:
            erros.extend(err.args[0])
    try:
        copystat(inputdir, outputdir)																	# wE WANT TO MOVE THE STATISTICAL INFO TO THE FILES AS WELL	
    except OSError as err:
    if err.winerror is None:
        errors.extend((inputdir, outputdir, str(err)))													# We had an error in the statistics.
    if errors:
        raise Error(errors)
    if not errors:
    	sys.exit()																						#No error so we just exit clean
    else:
    	sys.exit(2)																						#we had an error we exit with error

