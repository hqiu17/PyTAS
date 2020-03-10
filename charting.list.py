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


if __name__ == "__main__":
    
    LAST_REMOVED_ROWS=0
    FIGWIDTH=42
    FIGDEPTH=24
    
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
        tickers.basic_processing()
        tickers.work()
        df = tickers.get_new_descriptions()

        # check for SPY data and add it to dataframe as background
        spy =  dir+"/"+"SPY"+".txt"
        ref = ""
        if os.path.exists(spy):
            mydf=pd.read_csv(spy,sep="\t",parse_dates=['date'], index_col=['date'])
            
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

        ########################################################################
        #       loop through filtered symbol table and collect securities      #
        ########################################################################
        securities={}
        count=1000
        df_filtered = pd.DataFrame()

        wins=0
        losses=0
        total_trade=0
        Rtotal=0
        
        for sticker, row in df.iterrows():
            row_copy = row.copy(deep=True)
            count+=1

            # prepare figure header
            note = ""
            # prepare head note for display in chart
            if "Zacks Rank" in row:
                note = note + " zr{}".format(str(int(row["Zacks Rank"])))
            if "Value Score" in row:
                if kwargs["vgm"] and not utility.pick_V_G_VGM(row):
                    continue
                note = note + "{}/{}".format(row["Value Score"],
                                      row["Growth Score"]
                                      #row["Momentum Score"],
                                      #row["VGM Score"]
                                      )
            if "# Rating Strong Buy or Buy" in row and "# of Brokers in Rating" in row:
                note = note + "br{}/{}".format(int(row["# Rating Strong Buy or Buy"]),
                                                int(row["# of Brokers in Rating"])
                                                )
                if kwargs["cutBrokerbuyRatio"]>0:
                    myratio = row["# Rating Strong Buy or Buy"]/row["# of Brokers in Rating"]
                    if myratio < kwargs["cutBrokerbuyRatio"]:
                        continue
                if kwargs["cutBrokerbuyCount"]>0:
                    if row["# Rating Strong Buy or Buy"] < kwargs["cutBrokerbuyCount"]:
                        continue
            if "Long-Term Growth Consensus Est." in row:
                note = note + "ltg{}".format(row["Long-Term Growth Consensus Est."])
            
            # prepare annotation
            antt = ""
            if "P/E (Trailing 12 Months)" in row:
                antt = antt + "pe" + str(row["P/E (Trailing 12 Months)"])
            if "PEG Ratio" in row:
                antt = antt + "peg" + str(row["PEG Ratio"])
            if "Next EPS Report Date " in row:
                antt = antt + "eday" + str(row["Next EPS Report Date "])

            # test existence of data for the given symbol
            
            
            sts_daily = tickers.sts_daily
            if sticker in sts_daily:
                sts = sts_daily[sticker]
                df = sts.df
            
            #price = dir+"/"+sticker+".txt"
            #if os.path.exists(price):
            #   df=pd.read_csv(price, sep="\t",parse_dates=['date'], index_col=['date'])

                #print(sticker, df.shape)
                
                if LAST_REMOVED_ROWS:
                    row_num = df.shape[0]
                    if row_num <= LAST_REMOVED_ROWS + 100:
                        continue
                    else: 
                        df = df.head(row_num-LAST_REMOVED_ROWS)

                #print(sticker, df.shape)
                           
                rsi = str( sts.get_rsi())[0:4]

                #print(sticker, df.shape)
                
                
                if kwargs["weekly"] or kwargs["weeklyChart"]: 
                    df = stimeseries(df).get_weekly()
                else:
                    if len(ref)>30:
                        df = df.join(ref)
                df=df.tail(500)
                
                df = cdstk.cstick_sma(df)
                
                # load the name and annotations to a dictionary
                df_filtered= df_filtered.append(row_copy,ignore_index=False)
                    
                mysecurity = Security(df)
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

                if kwargs["sample"]:
                    sample = kwargs["sample"]
                    samples={}
                    samples_test={}

                    sts = stimeseries(df)
                    if  sample == 'stks_bb':
                        samples_test,samples,R,win,loss = sts.sampling_stks_bb(14, 3)
                        if len(samples)==0: continue
                        wins+=win
                        losses+=loss
                        total_trade += len(samples)
                        #print(f"f {win:>6} {loss}")
                        for date, r in R.items():
                            Rtotal = Rtotal +r
                            if r >=0 and r<0.001: 
                                r=0
                                print (f"{date.rstrip()}.{sticker:<7}\t\t{str(r)[0:5]:>6}\t\t{str(Rtotal)[:5]:>6}\t{df.loc[date,'long']}")
                            if r >0.001:
                                print (f"{date.rstrip()}.{sticker:<7}\t{str(r)[0:5]:>6}\t\t\t{str(Rtotal)[:5]:>6}\t{df.loc[date,'long']}")
                            if r <0: 
                                print (f"{date.rstrip()}.{sticker:<7}\t\t\t{str(r)[0:5]:>6}\t{str(Rtotal)[:5]:>6}\t{df.loc[date,'long']}")
                    
                        
                    elif sample == 'below_bb':
                        samples = sts.sampling_below_bb()
                    elif sample == 'plunge_macd':
                        samples_test,samples,R,win,loss = sts.sampling_plunge_macd()
                        if len(samples)==0: continue
                        wins+=win
                        losses+=loss
                        total_trade += len(samples)
                        #print (sticker)
                        #print(f"f {win:>6} {loss}")
                        for date, r in R.items():
                            Rtotal = Rtotal +r
                            if r >=0 and r<0.001: 
                                r=0
                                print (f"{date.rstrip()}.{sticker:<7}\t\t{str(r)[0:5]:>6}\t\t{str(Rtotal)[:5]:>6}\t{df.loc[date,'long']}")
                            if r >0.001:
                                print (f"{date.rstrip()}.{sticker:<7}\t{str(r)[0:5]:>6}\t\t\t{str(Rtotal)[:5]:>6}\t{df.loc[date,'long']}")
                            if r <0: 
                                print (f"{date.rstrip()}.{sticker:<7}\t\t\t{str(r)[0:5]:>6}\t{str(Rtotal)[:5]:>6}\t{df.loc[date,'long']}")
                        #Rtotal+= sum(list(R.values()))
                    # turn price data into security and harvest for plotting
                    

                    for date, price in samples_test.items():
                        rsi = str(stimeseries(price).get_rsi())[0:3]
                        mysecurity = Security(price)                    
                        mysecurity.set_date_added(date+' ')
                        r = R[date]
                        if r>0 and r <0.001: r=0
                        r=str(r)[0:5]
                        #securities[f"{sticker}: {note} {date} {r}R_"] = mysecurity
                        securities[f"{sticker}: {note} {date}"] = mysecurity
                    """
                    for date, price in samples.items():
                        rsi = str(stimeseries(price).get_rsi())[0:3]
                        mysecurity = Security(price)                    
                        mysecurity.set_date_added(date)
                        r = R[date]
                        if r>0 and r <0.001: r=0
                        r=str(r)[0:5]    
                        securities[f"{sticker}: {note} {date} {r}R"] = mysecurity
                    """
                else:
                    securities[f"{sticker}: {note} RSI-{rsi}"] = mysecurity

            else:
                #print (price, " doesn't exist")
                df_filtered= df_filtered.append(row_copy,ignore_index=False)
            
        if kwargs["sample"]:
            win_rate = str(wins/total_trade)[0:4]
            r_edge   = str(Rtotal/total_trade)[0:4]
            print (f"#    {wins}wins, {losses}losses, {total_trade}trades, {win_rate}winrate; {str(Rtotal)[0:4]} totalR {r_edge}R edge")

        ########################################################################
        #   plot multi-panel figure while going through a list of securities   #
        ########################################################################
        if kwargs["filterOnly"]:
            df_filtered.index.name="Symbol"
            df_filtered.to_csv(file_name+".txt",sep="\t")
            pd.set_option('display.max_rows', None)
            #pd.set_option('display.max_columns', None)
            print("\n".join(df_filtered.index))
        else:
            print (f"# {len(securities):>5} data to plot")
            num_to_plot = len(securities) if len(securities) >0 else 0
            if num_to_plot:
                done=0
                this_batch={}
                # create one output file for every 'num_to_plot' securities
                c=1000
                for key, security in securities.items():
                    c+=1
                    this_batch[key]=security
                    if len(this_batch)%num_pic_per_file ==0:
                        make_imgfile(file_name, this_batch, c, panel_row, panel_col, to_be_recycled, 
                             dayspan, gradient, fig_wid, fig_dep)
                        this_batch={}
                if len(this_batch)>0:
                    make_imgfile(file_name, this_batch, c, panel_row, panel_col, to_be_recycled, 
                         dayspan, gradient, fig_wid, fig_dep)
                    this_batch={}

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


    #--->
    #    argument parser
    #<---
    

    
    args = argumentParser.get_parsed(sys.argv[1:])

    # main code
    dir = args.dir
    for list in args.list:
        chart_securities(list, **vars(args))
