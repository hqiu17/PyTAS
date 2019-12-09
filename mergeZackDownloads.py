#!/usr/local/bin/python
# put all downloaded price data into a common dir: daliyPrice
#

import re
import os
import sys
import time
import argparse
import pandas as pd


def df_add_newframe(old, new):
    """ Add info from df 'new' on top of df 'old'. Priority is given to new in case of conflict
        *** the order of input arguments matters ***
        Return -- a new dataframe
    """
    return new.combine_first(old)

def df_add_newframes(list):
    """ Add info from the 2nd df on top of the 1st, and then add the 3rd top of the combination
        of the first two df. Repeat the process until the last df is incorporated.
        *** the order of elements in list matters. Old ->-> New ***
        list   -- a list of dataframe. Oldest df the first and newest df the last
        Return -- a new dataframe
    """
    base = pd.DataFrame()
    for df in list:
        base = df_add_newframe(base, df)
        print (base.shape)
    return base

if __name__ == "__main__":
    
    text= "Merge two or more Zacks download tables"
    parser = argparse.ArgumentParser(description = text)
    parser.add_argument("query",
                        nargs='*',
                        help=": A list of csv file downloaded from Zacks ")
    parser.add_argument("--out",  help=": Output file")
    args=parser.parse_args()
    
    
    output = args.out
    tables = args.query

    # read in input tables into dataframes and collect them into a list
    dataframes = []    
    for table in tables:
        df = pd.read_csv(table, index_col=0)

        #if "Industry" in df:
            # remove oil related industry
        #    df = df[~df["Industry"].str.contains("Oil and Gas")]
        #if "Last Close" in df:
            # remove stock with too high price
        #    df = df.loc[ df['Last Close'] < 400]
            
        dataframes.append(df)
    print (len(dataframes), " input tables")

    # merge the list of dataframes and export to output file
    df = df_add_newframes(dataframes)
    df = df.set_index("Ticker")
    if "Growth Score" in df and "Value Score" in df:
        df["Growth Score"].replace('0','X',inplace=True)
        df["Value Score"].replace('0','X',inplace=True)
        df = df.sort_values(["Growth Score","Value Score"], ascending=True )
    elif "Growth Score" in df:
        df["Growth Score"].replace('0','X',inplace=True)
        df = df.sort_values(["Growth Score"], ascending=True )
    elif "Value Score" in df:
        df["Value Score"].replace('0','X',inplace=True)
        df = df.sort_values(["Value Score"], ascending=True )

    df = df.fillna(0)
    df.to_csv(output,sep="\t")