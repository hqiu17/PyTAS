#!/Users/air1/anaconda3/bin/python
# take zacks rank as input
# put all downloaded price data into a common dir: daliyPrice
#

import re
import os
import sys
import time
import pandas as pd

from alpha_vantage.timeseries import TimeSeries


def get_timeseries(key):
    ts = TimeSeries(
                    key,
                    output_format='pandas',
                    indexing_type='date'
                    )
    return ts

def get_daliyPrices_inPandas(timeseries, ticker):
    data, meta_data = timeseries.get_daily(
                                   symbol=ticker,
                                   outputsize='full'
                                   )
    return data, meta_data

def setup_outdir (file):
    """
        substract dir name from file name (i.e., remove '.txt')
        and create dir if no already exists
        retrun dir name
    """
    mymatch = re.match(r'^(\S+).txt', file)
    if mymatch:
        dir = mymatch.group(1)
    else:
        dir = file + ".dir"

    make_dir(dir)
    return dir

def make_dir (dir):
    if not os.path.exists (dir):
        os.mkdir(dir)
        print ("directory ", dir,  " is created")
    else:
        print ("directory ", dir,  " already exists")

def file_strip_txt (file):
    name=file
    mymatch = re.match(r'^(\S+)(?:.txt)+', file)
    if mymatch:
        name = mymatch.group(1)
    return name


def fix_dateAdded(day):
    day = day.replace(",", ", ")
    day = day.replace("Jan", "January")
    day = day.replace("Feb", "February")
    day = day.replace("Mar", "March")
    day = day.replace("Apr", "April")
    day = day.replace("Jun", "June")
    day = day.replace("Jul", "July")
    day = day.replace("Aug", "August")
    day = day.replace("Sep", "September")
    day = day.replace("Oct", "October")
    day = day.replace("Nov", "November")
    day = day.replace("Dec", "December")
    return day

def pick_V_G_VGM(series):
    i = False
    if (series["Growth Score"] <= "B"):
        if (series["Value Score"] <= "C"):
            i = True
        elif series["VGM Score"] == "A":
            i = True
    elif  series["VGM Score"] == "A":
        i = True

    return i


if __name__ == "__main__":

    ts = get_timeseries()
    
    list = sys.argv[1]
    fh=open(list, "r")
    #dir=setup_outdir(list)
    dir = "daliyPrice01"
    make_dir(dir)
    


    data = pd.read_csv(list,sep="\t")
    #if 'Date Added' not in data.columns:
    for index, row in data.iterrows():
        ticker = row['Symbol']
        addate = row['Date Added']
        addate = fix_dataAdded(addate)
        
        if ticker:
            outfile = dir+"/"+ticker+".txt"
        if os.path.isfile(outfile):
            #if os.stat(outfile).st_size:
            print ("# ", index, " was done: ", ticker)
        else:
            print ("# ", index, " is to be done: ", ticker)
            
            prices, metadata = get_daliyPrices_inPandas(ts, ticker)
            prices['Date Added'] = addate
            prices.to_csv(outfile, sep="\t")
            time.sleep(12)




