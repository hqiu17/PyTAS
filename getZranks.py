#!/usr/local/bin/python
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

    def get_qry_data(qry, df_data, retain_all):
        df=pd.DataFrame()
        df.index.name="Symbol"
        empty_row = pd.Series('0', df_data.columns)
        
        qry_dict={}
        q = open(qry,"r")
        hit = 0
        for line in q:
            array=line.rstrip().split("\t")
            symbol=array[0]
            #print (symbol)
            if symbol == "Symbol":
                continue
            if symbol in df_data.index:
                #qry_dict[array[0]]=1
                #df.loc[symbol] = df_data.loc[symbol]
                df = df.append(df_data.loc[symbol], ignore_index=False)
                hit +=1
            else:
                if retain_all:
                    empty_row.name = symbol
                    df = df.append(empty_row, ignore_index=False)
                    #df.loc[symbol] = empty_row
                #print (f"{symbol:<5} is not found in searched database")
        print ( "{}/{} symbols have annotation".format(hit, str(len(df))) )
    
        #return df_data.loc[qry_dict.keys()]
        return df
    
    
    text= "Given a symbol list, retrive the symbol information from database, e.g., Zank rank data"
    parser = argparse.ArgumentParser(description = text)
    parser.add_argument("queries",
                        nargs='*',
                        help=": files containing a list of symbols")
    parser.add_argument("--data", help=": a file containing the fundamental data")
    parser.add_argument("--dlmt", help=": is the data delimited by comma or tab. Default: comma",
                        default = "comma")
    parser.add_argument("--all" ,
                        help=": retain all data regardless of availability in rank database",
                        action='store_true')
                        
    args=parser.parse_args()
    
    data_file = args.data
    delimiter = args.dlmt
    if not delimiter: delimiter = "comma"
    retain_all = False
    if args.all: retain_all = True
    
    data=pd.DataFrame()
    if os.path.exists(data_file):
        if  delimiter == "comma":
            data=pd.read_csv(data_file)
        elif delimiter == "tab":
            data=pd.read_csv(data_file, sep="\t")
        else:
            print ("invalid delimiter")
            exit(1)
            
        if "Ticker" in data and "Symbol" not in data:
            data["Symbol"] = data["Ticker"]
        data=data.set_index("Symbol")
        
    for query in args.queries:
        df = pd.DataFrame()
        df = get_qry_data(query, data, retain_all)
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

        df.to_csv(query+".txt", sep="\t")
