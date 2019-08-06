#!/usr/local/bin/python
# put all downloaded price data into a common dir: daliyPrice
#

import re
import os
import sys
import time
import argparse
from datetime import datetime
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

def get_filecreation_date(filepath):
    time_stamp=os.stat(filepath).st_ctime
    datetime_obj=datetime.fromtimestamp(time_stamp)
    date_code=get_datecode(datetime_obj)
    return date_code, datetime_obj.weekday()

"""
    turn datetime object for (2019, 8, 1) into numeric code 20190801
"""
def get_datecode(datetime_obj):

    date_code=datetime_obj.year*10000
    date_code=date_code + 10000 + datetime_obj.month*100
    date_code=date_code + 100 + datetime_obj.day
    date_code=date_code - 10100
    return date_code

if __name__ == "__main__":

    
    def download_asymbol(symbol, outfile):
        try:
            prices, metadata = utility.get_daliyPrices_inPandas(ts, symbol)
            prices.to_csv(outfile, sep="\t")
        except:
            time.sleep(12)
            return 1


    def download_alist(list):
        fh=open(list, "r")
        for num, line in enumerate(fh):
            # remove header
            mymatch = re.match (r'Symbol.*', line)
            if mymatch: continue
            #
            ticker=""
            mymatch = re.match(r'(\S+)\s.*', line)
            #time.sleep(1)
            if mymatch:
                ticker = mymatch.group(1)
            if ticker and not '.' in ticker:
                outfile = dir+"/"+ticker+".txt"
                
                if refresh:
                    print (f"# {num:>3} {ticker:<6} is to be done")#,end="\r", flush=True)
                    #download_asymbol(ticker)
                # if existing download is present
                elif os.path.isfile(outfile):
                    datecode, weekday = get_filecreation_date(outfile)
                    # existing download is created on the same day
                    if (today_datecode-datecode) == 0:
                        print (f"# {num:>3} {ticker:<6} was done [today download] {datecode}")#, end="\r", flush=True)
                    # on Saturday with existing download created on this friday
                    elif today_weekday == 5 and (today_datecode-datecode)==1:
                        print (f"# {num:>3} {ticker:<6} was done [friday download]")#, end="\r", flush=True)
                    # on Sunday with existing download created on this friday and saturday
                    elif today_weekday == 6 and (today_datecode-datecode)<=2:
                        print (f"# {num:>3} {ticker:<6} was done [friday/Saturday download]")#, end="\r", flush=True)
                    # on struction to keep all existing download
                    elif stay:
                        print (f"# {num:>3} {ticker:<6} was done [refreshed]")#, end="\r", flush=True)
                    # existing download is created on other days
                    else:
                        print (f"# {num:>3} {ticker:<6} is to be done; previous download is relocated")#,end="\r", flush=True)
                        
                        # move old download to elsewhere
                        os.rename(outfile, symbol_collection+"/"+ticker+".txt")
                        status = download_asymbol(ticker, outfile)
                        if status == 1 : print (f"# {num:>3} {ticker:<6} is not found !")
                        time.sleep(11)
                # if not existing download is found, then engage download
                else:
                    print (f"# {num:>3} {ticker:<6} is to be done")#,end="\r", flush=True)
                    status = download_asymbol(ticker, outfile)
                    if status == 1 : print (f"# {num:>3} {ticker:<6} is not found !")
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
    parser.add_argument("--refresh", help=": ignore existing download files",
                        action='store_true')
    parser.add_argument("--stay", help=": skip symbols with existing download files",
                        action='store_true')

    dir = 'daliyPrice'
    args=parser.parse_args()
    
     
    if args.dir:
        dir = args.dir            
        utility.make_dir(dir)

    if args.key:
        mykey=get_key(args.key)
        ts = utility.get_timeseries(mykey)

    refresh = False
    refresh = args.refresh

    stay = False
    stay = args.stay

    print (refresh, stay)

    symbol_collection = "names.allinone"

    today_datecode = get_datecode(datetime.today())
    today_weekday  = datetime.today().weekday()
    print(datetime.today())
    print(today_datecode, today_weekday)


    for list in args.list:
        download_alist(list)
    
