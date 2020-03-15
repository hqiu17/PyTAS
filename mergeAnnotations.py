#!/usr/local/bin/python
# put all downloaded price data into a common dir: daliyPrice
#

import re
import os
import sys
import time
import argparse
import pandas as pd
from getAnnotation import sort_growth_value

def df_add_newframe(old, new):
    """
    Add dataframe 'new' on top of dataframe 'old'. Priority is given to 'new' in case of 
        conflict
    
    Arguments:
        old: a pandas dataframe
        new: a second dataframe    
        *** the order of input arguments matters ***
    
    Return:
        a new dataframe combining 'old' and 'new'
    """
    return new.combine_first(old)

def df_add_newframes(list):
    """ 
    Add new dataframes on top of old dataframes step by step. In each step, Priority is 
    given to 'new' dataframe in case of conflict.

    Arguments:
    list  : a list of dataframe. The oldest dataframe at the right most first and the newest
            dataframe at the left most
                *** the order of elements in list matters. Oldest-> old->new->newest ***
    Return:
        a new dataframe combining all dataframes
    """
    base = pd.DataFrame()
    for df in list:
        base = df_add_newframe(base, df)
        print (base.shape)
    return base

if __name__ == "__main__":
    
    # set up argument parser
    text= "Merge two or more descriptive tables (e.g., zacks download table)"
    parser = argparse.ArgumentParser(description = text)
    parser.add_argument("query", nargs='*',
                                 help=": A list of csv file downloaded from Zacks ")
    parser.add_argument("--out", help=": Output file")
    
    # get parser ready
    if len(sys.argv)==1: parser.print_help(sys.stderr); sys.exit(1)
    args=parser.parse_args()

    # population key parameters
    output = args.out
    tables = args.query

    # read in input tables into dataframes and collect them into a list
    dataframes = []    
    for table in tables:
        df = pd.read_csv(table, index_col=0)            
        dataframes.append(df)
    print (len(dataframes), " input tables")

    # merge a list of dataframes and export resulting dataframe to output file
    df = df_add_newframes(dataframes)
    df = df.set_index("Ticker")
    # sort dataframe by growth and value scores
    df = sort_growth_value(df)
    df = df.fillna(0)
    df.to_csv(output,sep="\t")