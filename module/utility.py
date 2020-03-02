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

def get_output_filename(input, **kwargs):
    file_name = input
    if kwargs["sample"]:
        file_name = file_name + ".hist_"+ kwargs["sample"]
    if kwargs["filterOnly"]:
        file_name = file_name + ".filtered"
    if kwargs["vgm"]:
        file_name = file_name + ".cvg"
    if kwargs["blind"] >0:
        file_name = file_name + ".bld"  + str(kwargs["blind"])
    if kwargs["uptrend"]:
        file_name = file_name + ".cup"  + kwargs["uptrend"].replace(',','-')
    if kwargs["cutBrokerbyRatio"]>0:
        file_name = file_name + ".cbr"  + str(int(kwargs["cutBrokerbyRatio"]*100))
    if kwargs["cutBrokerbyCount"]>0:
        file_name = file_name + ".cbc"  + str(int(kwargs["cutBrokerbyCount"]*100))
    if kwargs["sort_zacks"]:
        file_name = file_name + ".szk"  + kwargs["sort_zacks"].replace(',','')
    elif kwargs["sort_trange"]:
        file_name = file_name + ".str"  + kwargs["sort_trange"].replace(',','_')
    if kwargs["sort_madistance"] >0:
        file_name = file_name + ".sma"  + str(kwargs["sort_madistance"])
    if kwargs["sort_bbdistance"]:
        file_name = file_name + ".sbd"  + kwargs["sort_bbdistance"].replace(',','_')
    if kwargs["sort_brokerrecomm"]:
        file_name = file_name + ".sbr"
    if kwargs["sort_performance"]>0:
        file_name = file_name + ".spfmc"+ str(int(kwargs["sort_performance"]))
    if kwargs["sort_industry"]:
        file_name = file_name + ".sid"
    if ',' in kwargs["sort_sink"]:
        file_name = file_name + ".ssk" + kwargs["sort_sink"].replace(',','_')
    if kwargs["sort_earningDate"]:
        file_name = file_name + ".sed"
    if kwargs["filter_madistance"]>0:
        file_name = file_name + ".fma"  + str(kwargs["filter_madistance"])
    if kwargs["filter_macd_sig"]:
        file_name = file_name + ".macd" + kwargs["filter_macd_sig"].replace(',','-')
    if kwargs["filter_stochastic_sig"]:
        file_name = file_name + ".stks" + kwargs["filter_stochastic_sig"].replace(',','-')
    if kwargs["filter_ema_slice"] :
        file_name = file_name + ".mslc" + kwargs["filter_ema_slice"].replace(',','-')
    if kwargs["two_dragon"]:
        file_name = file_name + ".2drgn"+ kwargs["two_dragon"].replace(',','-')
        
    if kwargs["weekly"] :
        file_name = file_name + ".wkly"
    if kwargs["weeklyChart"] :
        file_name = file_name + ".wklyc"

    return file_name

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
    if (series["Growth Score"] <= "C"):
        if (series["Value Score"] <= "D"):
            i = True
        elif "VGM Score" in series:
            if series["VGM Score"] == "A":
                i = True
    elif "VGM Score" in series:
        if series["VGM Score"] == "A":
            i = True
    return i

"""
def scale(list, max, min):
    data_max=""
    data_min=""
        for array in list:
            max = array.max()
            min = array.min()
            if max > data_max: data_max = max
            if min < data_min: data_min = min
"""    

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




