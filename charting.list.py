#!/usr/local/bin/python
# cmp v1:  handle multiple datasets and plot multi-panel figure
# cmp v20: given a list ticker and directory holding price data, do multi-panel
#          candlestick plot
# cmp v21: handel zacks data only (need 'Date Added' information)

import os
import re
import sys
import copy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

import module.candlestick as cdstk
import module.utility as utility
import module.argumentParser as argumentParser

from module.candlestick import Security
from module.stimeseries import stimeseries
from module.candlestick import date_to_index
from module.descriptions import descriptions


def make_imgfile(file_name, securities, count, panel_row, panel_col, to_be_recycled,
         dayspan=200, gradient=9, fig_wid=40, fig_dep=24,
         dualscale=False, drawbyrow=False):
    
    # remove path from file name
    if '/' in file_name:
        mymatch = re.match("^.+\/([^\/]+)$", file_name)
        if mymatch:
            file_name = mymatch.group(1)
        else:
            print (f"#  cannot parse \'\/\' in infile name: {file_name}")
            sys.exit(1)
    # define output figure
    output = "zxplot."+ file_name +f".{dayspan}d."+ str(count) +".pdf"
    
    # chart in the output figure
    recycle = cdstk.draw_many_candlesticks(securities, output,
                                       panel_row, panel_col,
                                       fig_wid, fig_dep,
                                       dayspan, gradient,
                                       drawbyrow
                                       )
    securities.clear()
    to_be_recycled.extend(recycle)


def chart_securities(file, **kwargs):
        """
        Chart a list of securities included in the input file
        
        Argument:
            file : a text input file with each row representing a security and each column representing
                   for an attribute of securities
            kwargs : a list of user input key word arguments
        """        
        fig_wid  = 42
        fig_dep  = 24        
        dayspan  = kwargs["period"]
        gradient = kwargs["gradient"]
        weekly   = kwargs['weekly']

        
        """ Basic processing the security data based on descriptive attributes
        """
        # read input security data sheet into a pandas dataframe
        df = pd.read_csv(file, sep="\t")
        
        # record total number of securities in the input data
        num_stickers = df.shape[0]
        print (f"#->{num_stickers:>4} securities in ", end="")
        
        # set final output file name based on input file and user arguments
        file_name = cdstk.file_strip_txt(file)
        if file_name:
            print (file_name)
            file_name = utility.get_output_filename(file_name, **kwargs)
                
        # set the number of rows and columns within each output chart based on  
        # the total number of input securities and charting related argument (-p)
        default_row_num = 6 if "," in dayspan else 7
        panel_row = cdstk.set_row_num(num_stickers)    
        panel_row = default_row_num if panel_row > default_row_num else panel_row
        panel_col=panel_row
        if ',' in dayspan: panel_col = int((panel_col+1)/2)
        num_pic_per_file = panel_col * panel_row
            
        if default_row_num==1:
            fig_wid=10
            fig_dep=6
        
        # securities to be charted in different scale (not implemented yet)
        to_be_recycled=[]    
        
        # filter and sort securities
        tickers = descriptions(df, dir, 'file_name', kwargs)
        #tickers.basic_processing()
        tickers.work()
        df = tickers.get_new_descriptions()

        # check for SPY data and add it to dataframe as background
        spy =  dir+"/"+"SPY"+".txt"
        ref = get_benchmark(spy)
        
        ########################################################################
        #       loop through filtered symbol table and collect securities      #
        ########################################################################
        securities={}
        count=1000
        securities_filtered = pd.DataFrame()

        for sticker, row in df.iterrows():
            #print (sticker)
            row_copy = row.copy(deep=True)
            count+=1
            note = row['header']
            antt = row['annotation']
            
            sts_daily = tickers.sts_daily
            if sticker in sts_daily:
                sts = sts_daily[sticker]
                daily_price = sts.df
                            
                if LAST_REMOVED_ROWS:
                    row_num = daily_price.shape[0]
                    if row_num <= LAST_REMOVED_ROWS + 100:
                        continue
                    else: 
                        daily_price = daily_price.head(row_num-LAST_REMOVED_ROWS)
                           
                rsi = str( sts.get_rsi())[0:4]
                
                if kwargs["weekly"] or kwargs["weeklyChart"]: 
                    daily_price = stimeseries(daily_price).get_weekly()
                else:
                    if len(ref)>30:
                        daily_price = daily_price.join(ref)
                daily_price=daily_price.tail(500)
                    
                mysecurity = Security(daily_price)

                if antt:
                    mysecurity.set_annotation(antt)
                if "Date Added" in row:
                    date = row["Date Added"]
                    mysecurity.set_date_added(date)
                if "Date Sold" in row:
                    date = row["Date Sold"]
                    if date and date != "na" and date != "NA":
                        mysecurity.set_date_sold(utility.fix_dateAdded(date))
                if "Industry" in row:
                    mysecurity.set_industry(row["Industry"])

                if "Sort" in row:
                    mysecurity.set_sortvalue(row["Sort"])

                securities[f"{sticker}: {note} RSI-{rsi}"] = mysecurity

        ########################################################################
        #   plot multi-panel figure while going through a list of securities   #
        ########################################################################
        if kwargs["filterOnly"]:
            df.to_csv(file_name+".txt",sep="\t")
            #pd.set_option('display.max_rows', None)
            #print("\n".join(df.index))
        else:
            print (f"# {len(securities):>5} data to plot")
            num_to_plot = len(securities) if len(securities) >0 else 0
            if num_to_plot:
                done=0
                security_batch={}

                c=1000
                for key, security in securities.items():
                    c+=1
                    security_batch[key]=security
                    if len(security_batch)%num_pic_per_file ==0:
                        # create one output file for every 'num_to_plot' securities
                        make_imgfile(file_name, security_batch, c, panel_row, panel_col, to_be_recycled, 
                             dayspan, gradient, fig_wid, fig_dep)
                        security_batch={}
                if len(security_batch)>0:
                    # create one output file for remaining securities
                    make_imgfile(file_name, security_batch, c, panel_row, panel_col, to_be_recycled, 
                         dayspan, gradient, fig_wid, fig_dep)
                    security_batch={}


def get_benchmark(file):
    ref = pd.DataFrame()
    if os.path.exists(file):
        mydf=pd.read_csv(file,sep="\t",parse_dates=['date'], index_col=['date'])
        
        # find go-long period
        mydf=cdstk.cstick_sma(mydf)
        mydf['last-20MA'] = mydf['4. close'] - mydf['20MA']
        mydf['long'] = np.where( mydf['last-20MA']>0, 1, 0)
        #print (mydf.head(25))
        # calculate daily change
        mydf["close_shift1"] = mydf["4. close"].shift(periods=1)
        mydf["weather"]=(mydf["4. close"]-mydf["close_shift1"])/mydf["close_shift1"]
            
        row_num = mydf.shape[0]

        if LAST_REMOVED_ROWS and row_num > LAST_REMOVED_ROWS + 100:
            mydf = mydf.head(row_num-LAST_REMOVED_ROWS)

        ### turn a series into dataframe (for record)
        ref=pd.DataFrame(mydf["weather"],index=mydf.index) 
        ref['long']=mydf['long']
    return ref


if __name__ == "__main__":
    
    LAST_REMOVED_ROWS=0
    FIGWIDTH=42
    FIGDEPTH=24
    
    #--->
    #    argument parser
    #<---
    
    args = argumentParser.get_parsed(sys.argv[1:])

    # main code
    dir = args.dir
    for list in args.list:
        chart_securities(list, **vars(args))
