#!/usr/local/bin/python

import re
import os
import sys
import time
import argparse
import pandas as pd
import shutil, errno
import module.utility as utility

def get_qry_data(qry, df_data, retain_all):
    """
    Retrieve data for a list of queries from a dataframe
    
    Arguments:
        qry: a list of queries with security names at the first column. If more than 
             one columns, the file is tab delimited
        df_data: a pandas dataframe database from which information will be retrieved
        retain_all: boolean. If true, securities without match in database will not be
             discarded.
             
    Return:
        a subset of the dataframe database containing rows for query securites
    """
    
    # set up empty dataframe and rows    
    df=pd.DataFrame()
    df.index.name="Symbol"
    empty_row = pd.Series('0', df_data.columns)
    
    # read query file, loop through and append rows to empty dataframe
    q = open(qry,"r")
    hit = 0
    for line in q:
        symbol=line.rstrip().split("\t")[0]
        if symbol == "Symbol":
            continue
        if symbol in df_data.index:
            df = df.append(df_data.loc[symbol], ignore_index=False)
            hit +=1
        else:
            if retain_all:
                empty_row.name = symbol
                df = df.append(empty_row, ignore_index=False)
    print ( "{}/{} output securities have annotations".format(hit, str(len(df))) )

    return df

def sort_growth_value(df):
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
    return df


if __name__ == "__main__":

    # set up argument parser
    text= ("Given a list of securites, retrieve their descriptive information from a "
           "pandas dataframe database")
    parser = argparse.ArgumentParser(description = text)
    
    parser.add_argument("queries",nargs='*',
                                  help=": files containing a list of securities")
                                  
    parser.add_argument("--data", help=": a file containing the descriptive database")
    parser.add_argument("--dlmt", help=": specify if the database is delimited by 'comma'"
                                       " or tab. Default: comma",
                                  default = "comma")
    parser.add_argument("--all" , help=": retain all securities regardless of availability"
                             " of their information in database",
                                  action='store_true')

    # get parser ready
    if len(sys.argv)==1: parser.print_help(sys.stderr); sys.exit(1)
    args=parser.parse_args()
    
    # population key parameters
    data_file = args.data
    delimiter = args.dlmt
    if not delimiter: delimiter = "comma"
    retain_all = False
    if args.all: retain_all = True
    
    # load database file to dataframe and set 'Symbol' column as index
    data=pd.DataFrame()
    if os.path.exists(data_file):
        # read database file
        if  delimiter == "comma":
            data=pd.read_csv(data_file)
        elif delimiter == "tab":
            data=pd.read_csv(data_file, sep="\t")
        else:
            print ("invalid delimiter {}\n".format(delimiter) )
            parser.print_help(sys.stderr)
            sys.exit(1)
            
        # use ticker column as replacement of symbol column
        if "Ticker" in data and "Symbol" not in data:
            data["Symbol"] = data["Ticker"]

        # test existence of symbol column. if true, set it as index
        if "Symbol" in data.columns:
            data=data.set_index("Symbol")
        else:
            print ("No 'Symbol' column found in database file")
            sys.exit(1)
        
    # loop through query files, data retrieval and write output file
    for query in args.queries:
        # retrieve data
        df = pd.DataFrame()
        df = get_qry_data(query, data, retain_all)
        
        # sort data by growth and value score (if these scores are available)
        df = sort_growth_value(df)
        # write data to output file
        df.to_csv(query+".txt", sep="\t")
