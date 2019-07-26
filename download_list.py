#!/Users/air/anaconda3/bin/python
# put all downloaded price data into a common dir: daliyPrice
#

import re
import os
import sys
import time
import argparse
from alpha_vantage.timeseries import TimeSeries
import module.utility as utility
import shutil, errno


def get_key(file):
	#with open(file, "r") as fh:
	fh=open(file,"r")
	mykey=""
	for line in fh:
		if line:
			mymatch = re.match(r'^\s*(\S+)\s.*', line)
			if mymatch:
				mykey=mymatch.group(1)
				break 
	return mykey	

def copyanything(src, dst):
    try:
        shutil.copytree(src, dst)
    except OSError as exc:                   # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dst)
        else: raise

if __name__ == "__main__":

    def download_alist(list):
        fh=open(list, "r")
        for num, line in enumerate(fh):
            # remove header
            mymatch = re.match (r'Symbol.*', line)
            if mymatch:
                continue
            #
            ticker=""
            mymatch = re.match(r'(\S+)\s.*', line)
            if mymatch:
                ticker = mymatch.group(1)
            if ticker and not '.' in ticker:
                outfile = dir+"/"+ticker+".txt"
                if os.path.isfile(outfile):
                    print (f"# {num:>3} {ticker:<6} was done", end="\r", flush=True)
                else:
                    print (f"# {num:>3} {ticker:<6} is to be done",end="\r", flush=True)
                    
                    try:
                        prices, metadata = utility.get_daliyPrices_inPandas(ts, ticker)
                        prices.to_csv(outfile, sep="\t")
                    except:
                        print (f"# {num:>3} {ticker:<6} is not found !")
                        time.sleep(12)
                        pass
                            
                    time.sleep(11)
                        
    
        fh.close()
        print ("done with ", list)


    text= "Given a symbol list, draw candlesticks for each of item"
    parser = argparse.ArgumentParser(description = text)
    parser.add_argument("list",
                        nargs='*',
                        help=": a file containing a list of symbol")
    parser.add_argument("--key",  help=": a file containing the key")
    parser.add_argument("--dir" ,
                        default="/Users/air/watchlist/daliyPrice",
                        help=": directory storing all downloaded price data (default='daliyPrice')")
        

    dir = 'daliyPrice'
    args=parser.parse_args()
     
    if args.dir:
        dir = args.dir            
    utility.make_dir(dir)

    mykey=get_key(args.key)
    ts = utility.get_timeseries(mykey)
        
    for list in args.list:
        download_alist(list)
    
