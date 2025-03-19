
#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
This file is designed to be a subprocess to copy files from one location to USB's file structure

"""

import sys, getopt
import argparse
import os, shutil
import logging
import shutil


def main():
        inputdir = ""
        outputdir = ""
        error = []
        parser = argparse.ArgumentParser()
        parser.add_argument( '--i', type=str, required=True, help = "Input Directory for Copy")
        parser.add_argument( '--o', type=str, required=True, help = "Output Directory for copy")
        arguments = (parser.parse_args())
        print("arguments", arguments)
        logging.info("Starting the copy function")
#        if not ("--i" in aruments and '--o" in  arguments):
#               print("startup of USBCopyUtil with unknown arguments")
#               return(2)
        if len(arguments.i) <= 4:
                print('USBCopyUtil.py -i <inputdir> missing')
                return()
        elif len(arguments.o) <=4:
                print("USBCopyUtil.py -o <outputdir> missing")                                                # we have a valid output directory
                outputdir = val[1]
        if  arguments.i == arguments.o:
                print("cannot copy from the same source to same destination")
                print("Closed USBCopyUtil.py due to lack of valid variabales")
                return(2)                                                                                       # we didn't get valid paramaters
        if  not os.path.isdir(arguments.o):                                                                     #Check output that its a valid directory
                print("Closed USBCopyUtil.py due to output path not being a direcotry")
                return(2)
        print("Starting USBCopyUtil with "+arguments.i+" copying to "+arguments.o)
        try:
            if os.path.isdir(arguments.i):                                                                     # We check that we have a valid direcotry on input
                print("Copying tree: "+arguments.i+" to: "+arguments.o)
                shutil.rmtree( arguments.o, ignore_errors=True)							#Remove the directory where were copying to.
                logging.info("Copying: "+arguments.i+" to "+arguments.o)
                shutil.copytree(arguments.i, arguments.o, symlinks=True, copy_function=shutil.copy2, ignore_dangling_symlinks=True)
            else:
                print("Copying: "+arguments.i+" to: "+arguments.o)	                                           # We may just try a copy if the input directory is only a file.
                logging.info("USBcopyUtil copy: "+arguments.i+" to: "+arguments.o)
                shutil.copy2(arguments.i, arguments.o)
        except (OSError):
                errors.append((arguments.i, arguments.o, str(OSError), str(shutil.Error))                            # We encountered an error so we stop.
        except shutil.Error:
#            errors.append((arguments.i, arguments.o, str(OSError), str(shutil.Error))                            # We encountered an error so we stop.
       s.exit()                                                                                                #No error so we just exit clean
        return()



if __name__ == "__main__":
    print("all done")

