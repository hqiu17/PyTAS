#!/Users/air1/anaconda3/bin/python
# put all downloaded price data into a common dir: daliyPrice
#

import re
import os
import sys
import time
import argparse
import pandas as pd
import module.utility as utility
import shutil, errno


if __name__ == "__main__":

    text= "Given a symbol list, retain its unique symbols (discard those found other database)"
    parser = argparse.ArgumentParser(description = text)
    parser.add_argument("others",
                        nargs='*',
                        help=": files containing a list of symbols")
    parser.add_argument("--query",  help=": a query file to retain unique symbol")
    args=parser.parse_args()
    
    database={}
    for file in args.others:
        db = open(file, "r")
        for line in db:
            array=line.rstrip().split("\t")
            symbol=array[0]
            database[symbol]=1
    
    query=args.query
    qry = open(query, "r")
    outs = open(query+"_swin.txt", "w")
    outc = open(query+"_core.txt", "w")
    for line in qry:
        array=line.rstrip().split("\t")
        symbol=array[0]
        if symbol == "Symbol":
            outs.write(line)
            outc.write(line)
        if symbol in database:
            outc.write(line)
        else:
            outs.write(line)