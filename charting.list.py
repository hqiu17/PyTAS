#!/usr/local/bin/python
# cmp v1:  handle multiple datasets and plot multi-panel figure
# cmp v20: given a list ticker and directory holding price data, do multi-panel
#          candlestick plot
# cmp v21: handel zacks data only (need 'Date Added' information)

import os
import re
import sys
import copy
#import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import module.candlestick as cdstk
from module.candlestick import Security
from module.candlestick import date_to_index
from module.stimeseries import stimeseries
import module.utility as utility
import module.argumentParser as argumentParser
from module.descriptions import descriptions

from matplotlib.font_manager import FontProperties


def sandwiched(string, series):
    """
    Test if daily candle crosses moving average or is sandwiched between two moving averages
    
        Argument:
            string : parameter(s) for moving average calculation, including 20, 50, 100, 150 and 200
                     two parameters separated by ',' is valide such as "20,50"
            series : a pandas series holding data for one day (including high, low, volumn, etc )    
        Return:   if series (daily candle) and moving average(s) meet the requirement (ture) or not (false)
    """
    status = False
    high=""
    low =""
    if ',' in string:
        list=string.split(',')
        high=list[0]+'MA'
        low =list[1]+'MA'
    else:
        if string == 'bb':
            high = 'BB20d'
        else:
            high=string +'MA'

    if  series['3. low']<=series[high] and series[high] <= series['4. close']:
        # candle cross MA/BB
        status = True
        if series['3MA'] <= series[high]: status = False
    elif low:
        # last close stay between 2 MAs
        if series[low] <= series['4. close'] and series['4. close']<= series[high]:
            status = True
        if series['5MA'] <= series[low]: status = False
    elif high == 'BB20d':
        bb_dist_low   = (series["3. low"]-series['BB20d'])/(series['BB20u']-series['BB20d'])
        if bb_dist_low <0.05:
            status = True

    return status

#def dataframe

if __name__ == "__main__":
    
    LAST_REMOVED_ROWS=0
    
    def draw_list_candlestick(file, **kwargs):
        """ chart a list of stickers listed in a file
            the stick prices data are stored in a directory
        """
        dayspan  = kwargs["period"]
        gradient = kwargs["gradient"]
        weekly   = kwargs['weekly']
        ########################################################################
        #                 preparation                                          #
        ########################################################################
        # pre-processing rank_data
        df = pd.read_csv(file, sep="\t")
        if "Industry" in df:
           df = df[~df["Industry"].str.contains("Oil and Gas")]
        if "Date Added" in df.columns:
            df["Date Added"] = df["Date Added"].apply(utility.fix_dateAdded)
            df["Date Added"] = pd.to_datetime(df["Date Added"])
        if "Date Sold" in df.columns:
            df["Date Sold"] = df["Date Sold"].apply(utility.fix_dateAdded)
            df["Date Sold"] = pd.to_datetime(df["Date Sold"])
        if "Ticker" in df and "Symbol" not in df:
            df["Symbol"] = df["Ticker"]
        
        # sort names by symbol (default) or date
        if kwargs["sort_dateAdded"] and "Date Added" in df.columns:
            df = df.sort_values(by="Date Added", ascending=True)
        else:
            df = df.sort_values(by="Symbol")
        if "Symbol" in df:
            df = df.set_index("Symbol")
        else:
            print ("#-x No Symbols column in the table of symbols")
            exit(1)

        num_stickers = df.shape[0]
        print (f"#->{num_stickers:>4} symbols in ", end="")
        
        # prepare output name 
        file_name = cdstk.file_strip_txt(file)
        if file_name:
            print (file_name)
            file_name = utility.get_output_filename(file_name, **kwargs)
                
        # specify number of rows and columns for the whole chart
        figwidth=42
        figdepth=24
        default_row_num=7
        if "," in dayspan:
            default_row_num=6
        panel_row= cdstk.set_row_num(num_stickers)
        if panel_row > default_row_num:
            panel_row = default_row_num
        panel_col=panel_row
        if ',' in dayspan:
            panel_col = int((panel_col+1)/2)
        num_pic_per_file = panel_col * panel_row
            
        if default_row_num==1:
            figwidth=10
            figdepth=6
            
        to_be_recycled=[]    
        
        ########################################################################
        #                 sort or fileter a given list of symbols              #
        ########################################################################
        """
        if kwargs["sort_brokerrecomm"]  and "# Rating Strong Buy or Buy" in df:
            df=df.sort_values(["# Rating Strong Buy or Buy"], ascending=False)
            
        if kwargs["sort_industry"] and "Industry" in df:
            df=df.sort_values(["Industry"])

        if kwargs["sort_zacks"]:
            sort_zacks = kwargs["sort_zacks"]
            type=''
            cut =''
            if ',' in sort_zacks:
                list = sort_zacks.split(',')
                type, cut = list
                cut = cut.upper()
            else:
                type=sort_zacks
                            
            if   type=='V' and "Value Score" in df:
                if cut:
                    df = df[ df["Value Score"]<= cut ]
                    print (f"# {df.shape[0]:>5} symbols meeting Value cutoff {cut}")
                df=df.sort_values(["Value Score"])
            elif type=='G' and "Growth Score" in df:
                if cut:
                    df = df[ df["Growth Score"]<= cut ]
                    print (f"# {df.shape[0]:>5} symbols meeting Growth cutoff {cut}")
                df=df.sort_values(["Growth Score"])
            else:
                print (f"invalide input for -szk: {sort_zacks}")
                exit(1)

        if kwargs["sort_trange"] >=0:
            sort_trange = kwargs["sort_trange"]
            cut_forSort_20d = 0.03
            cut_forSort_60d = 0.05 

            symbols = df.copy(deep=True)
            #symbols.to_csv("test0.txt")
            symbols["up_tranding_range_20d"]=pd.Series(0,index=symbols.index)
            symbols["up_tranding_range_60d"]=pd.Series(0,index=symbols.index)
            #symbols.to_csv("test1.txt")
            for symbol, row in df.iterrows():
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price,sep="\t",index_col=0)
                    
                    if LAST_REMOVED_ROWS:
                        if dfPrice.shape[0] <= LAST_REMOVED_ROWS:
                            continue
                        else: 
                            dfPrice=dfPrice.iloc[0:len(dfPrice)-LAST_REMOVED_ROWS]
                    dfPrice=dfPrice.tail(500)
                    
                    sts = stimeseries(dfPrice)

                    price_change_20d = sts.get_trading_uprange(20)
                    if price_change_20d < cut_forSort_20d:
                        #price_change_20d = 0
                        pass
                    price_change_60d = sts.get_trading_uprange(60)
                    if price_change_60d < cut_forSort_20d:
                        #price_change_60d = 0
                        pass


                    symbols.loc[symbol,"up_tranding_range_20d"]=price_change_20d
                    symbols.loc[symbol,"up_tranding_range_60d"]=price_change_60d

            if sort_trange>0:
                symbols = symbols.loc[ symbols["up_tranding_range_20d"]>sort_trange ]

                                 
            df=symbols
            df=df.sort_values(["up_tranding_range_20d","up_tranding_range_60d"],ascending=[False,False])
            print (f"# {df.shape[0]:>5} symbols meet trading range requirement")
        """        
        
        tickers = descriptions(df, dir, file_name, kwargs)
        tickers.work()
        df = tickers.get_new_descriptions()

        if kwargs["filter_macd_sig"]:
            filter_macd_sig = kwargs["filter_macd_sig"]
            mymatch = re.match("(\d+),(\d+)", filter_macd_sig)
            sspan = 0
            lspan = 0
            if mymatch:
                sspan = int(mymatch.group(1))
                lspan = int(mymatch.group(2))
            else:
                print ("macd input is invalide")
                sys.exit(1)

            #
            symbols = df.copy(deep=True)
            symbols["Sort"]=pd.Series(0,index=symbols.index)
            for symbol, row in df.iterrows():
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price, sep="\t",parse_dates=['date'], index_col=['date'])
                    
                    if LAST_REMOVED_ROWS:
                        if dfPrice.shape[0] <= LAST_REMOVED_ROWS:
                            continue
                        else: 
                            dfPrice=dfPrice.iloc[0:len(dfPrice)-LAST_REMOVED_ROWS]

                    sts = stimeseries(dfPrice.tail(500))
                    if weekly:
                        sts = stimeseries(dfPrice)
                        sts.to_weekly()                                            
                    signal = sts.macd_cross_up(sspan, lspan, 3)
                    

                    """                    
                    status = 1
                    if signal[-1]==0 or signal[0]==1:
                        status = 0
                    else:
                        tmp=0
                        change=0
                        for s in signal:
                            if s != tmp:
                                change+=1
                                tmp = s
                        if change >1: status =0
                    if macd_ref >= 0: status = 0
                    symbols.loc[symbol,"Sort"]= status
                    """
                    
                    #if macd_ref >= 0: signal = 0
                    symbols.loc[symbol,"Sort"]= signal

            symbols=symbols.sort_values(["Sort"],ascending=False)
            symbols=symbols.loc[ symbols['Sort'] > 0 ]
            df=symbols
            print (f"# {df.shape[0]:>5} symbols meet macd criteria")
            
        if kwargs["filter_stochastic_sig"]:
            """ filter for oversold (d < cutoff) tickers with stochastic K > D and
                bullish price action (paction < cutoff)
                input string: stochastic long term, 
                              stochastic short term, 
                              stochastic d cutoff, 
                              k>d ('all') or k just cross d up ('crs' or any string)
            """
            filter_stochastic_sig = kwargs["filter_stochastic_sig"]
            mymatch = re.match("(\d+),(\d+),(\d+),(\w+)", filter_stochastic_sig)
            n = 0
            m = 0
            c = 20
            mode = "all"
            if mymatch:
                n = int(mymatch.group(1))
                m = int(mymatch.group(2))
                c = int(mymatch.group(3))
                mode = mymatch.group(4)
            else:
                print ("stochastic input is invalide")
                sys.exit(1)
            symbols = df.copy(deep=True)
            symbols["STOK"]=pd.Series(100,index=symbols.index)
            symbols["STOD"]=pd.Series(100,index=symbols.index)
            symbols["STOC"]=pd.Series(0,index=symbols.index)
            symbols["BLSH"]=pd.Series(0,index=symbols.index)
            for symbol, row in df.iterrows():
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price, sep="\t",parse_dates=['date'], index_col=['date'])
                    
                    if LAST_REMOVED_ROWS:
                        if dfPrice.shape[0] <= LAST_REMOVED_ROWS:
                            continue
                        else: 
                            dfPrice=dfPrice.iloc[0:len(dfPrice)-LAST_REMOVED_ROWS]

                    sts = stimeseries(dfPrice.tail(500))
                    if weekly:
                        sts = stimeseries(dfPrice)
                        sts.to_weekly()
                    
                    (symbols.loc[symbol,"STOK"], 
                     symbols.loc[symbol,"STOD"], 
                     symbols.loc[symbol,"STOC"],
                     symbols.loc[symbol,"BLSH"] ) = sts.stochastic_cross(n, m)
            symbols=symbols.loc[ symbols['STOK'] < c+15 ]
            symbols=symbols.loc[ symbols['STOD'] < c ]
            #symbols=symbols.loc[ symbols['BLSH'] < 0.4 ]

            if mode == "all":
                # count all instances where K>D
                symbols=symbols.loc[ symbols['STOD'] < symbols['STOK'] ]
            else:
                # count instances reflecting transit from K<D to K>D
                symbols=symbols.loc[ symbols['STOC'] > 0 ]
            df = symbols

            print (f"# {df.shape[0]:>5} symbols meet stochastic criteria")   
            
        if kwargs["two_dragon"]:
            two_dragon = kwargs["two_dragon"]
            array = two_dragon.split(',')
            num_parm = len(array)
            if num_parm < 3:
                print ('#  invalid two_dragon value. 3 or 4 integers are required')
                exit(0)
            symbols = df.copy(deep=True)
            symbols["2dragon"]=pd.Series(0,index=symbols.index)
            for symbol, row in df.iterrows():
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price,sep="\t",index_col=0)
                    
                    if LAST_REMOVED_ROWS:
                        if dfPrice.shape[0] <= LAST_REMOVED_ROWS:
                            continue
                        else: 
                            dfPrice=dfPrice.iloc[0:len(dfPrice)-LAST_REMOVED_ROWS]

                    dfPrice=dfPrice.tail(500)
                    dfPrice=cdstk.cstick_sma(dfPrice)
                    sts = stimeseries(dfPrice)
                    if num_parm ==3:
                        symbols.loc[symbol,"2dragon"] = sts.two_dragon(int(array[0]),
                                                                        int(array[1]),
                                                                        int(array[2]))
                    elif num_parm ==4:
                        symbols.loc[symbol,"2dragon"] = sts.two_dragon(int(array[0]),
                                                                        int(array[1]),
                                                                        int(array[2]),
                                                                        float(array[3]))
                                                                
                    
            symbols=symbols.loc[ symbols['2dragon'] > 0 ]
            df = symbols
            print (f"# {df.shape[0]:>5} symbols meet 2dragon criteria({two_dragon})")

        if kwargs["sort_madistance"] >0:
            """ sort symbols by last close-to-SMA distance
            """
            sort_madistance = kwargs["sort_madistance"]
            symbols = df.copy(deep=True)
            symbols["Sort"]=pd.Series(0,index=symbols.index)
            for symbol, row in df.iterrows():
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price, sep="\t",parse_dates=['date'], index_col=['date'])
                    
                    if LAST_REMOVED_ROWS:
                        if dfPrice.shape[0] <= LAST_REMOVED_ROWS:
                            continue
                        else: 
                            dfPrice=dfPrice.iloc[0:len(dfPrice)-LAST_REMOVED_ROWS]

                    sts = stimeseries(dfPrice.tail(500))
                    if weekly:
                        sts = stimeseries(dfPrice)
                        sts.to_weekly()
                    symbols.loc[symbol,"Sort"]=sts.get_SMAdistance(sort_madistance)
            df=symbols
            df=df.sort_values(["Sort"],ascending=True)
            
        if kwargs["sort_bbdistance"]:
            sort_bbdistance = kwargs["sort_bbdistance"]
            days  = 1
            cutoff= -10
            if ',' in sort_bbdistance:
                list=sort_bbdistance.split(',')
                cutoff=float(list[0])
                days  =int(list[1])
            else:
                cutoff = float(sort_bbdistance)

            symbols = df.copy(deep=True)
            symbols["Sort"]=pd.Series(100,index=symbols.index)
            for symbol, row in df.iterrows():
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price, sep="\t",parse_dates=['date'], index_col=['date'])

                    if LAST_REMOVED_ROWS:
                        if dfPrice.shape[0] <= LAST_REMOVED_ROWS:
                            continue
                        else: 
                            dfPrice=dfPrice.iloc[0:len(dfPrice)-LAST_REMOVED_ROWS]

                    sts = stimeseries(dfPrice.tail(500))
                    if weekly:
                        sts = stimeseries(dfPrice)
                        sts.to_weekly()
                        
                    #bbdist = sts.get_BBdistance()
                    #if bbdist > sort_bbdistance: continue
                    #print ( bbdist, sort_bbdistance )
                    symbols.loc[symbol,"Sort"]=sts.get_BBdistance(days)
                    
            df=symbols
            df=df[ df['Sort'] <= cutoff ]
            df=df.sort_values(["Sort"],ascending=True)
            print (f"# {df.shape[0]:>5} symbols meet bollinger-band dist filter/sort({sort_bbdistance})")
            
        if kwargs["sort_performance"] >0:
            """ sort symbols by recent performance
            """         
            sort_performance = kwargs["sort_performance"]
            symbols = df.copy(deep=True)
            symbols["Sort"]=pd.Series(0,index=symbols.index)
            for symbol, row in df.iterrows():
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price,sep="\t",index_col=0)
                    
                    if LAST_REMOVED_ROWS:
                        if dfPrice.shape[0] <= LAST_REMOVED_ROWS:
                            continue
                        else: 
                            dfPrice=dfPrice.iloc[0:len(dfPrice)-LAST_REMOVED_ROWS]

                    dfPrice=dfPrice.tail(500)
                    sts = stimeseries(dfPrice)
                    symbols.loc[symbol,"Sort"] = sts.get_latest_performance(sort_performance)
            df=symbols
            df=df.sort_values(["Sort"],ascending=False)
            print(df["Sort"])

        if kwargs["sort_earningDate"]:            
            if "Next EPS Report Date  (yyyymmdd)" in df:
                df["Next EPS Report Date "] = df["Next EPS Report Date  (yyyymmdd)"]
                df=df.drop("Next EPS Report Date  (yyyymmdd)", axis=1)
        
            if "Next EPS Report Date " in df:
                """ sort symbols by last earning date
                """ 
                df["Next EPS Report Date "]=pd.to_numeric(df["Next EPS Report Date "])
                df=df.sort_values(["Next EPS Report Date "], ascending=True)

        if kwargs["uptrend"]:
            """ filter for symbols in uptrend in a specified recent period
                symbol list will be shortened
            """
            uptrend = kwargs["uptrend"]
            window=0
            cutoff=0.8
            blind =0
            array=[]
            if ',' in uptrend:
                array = uptrend.split(',')
                window=int(array[0])
                cutoff=float(array[1])
                if len(array)>=3: blind =int(array[2])
            else:
                window=int(uptrend)

            symbols = pd.DataFrame(columns=df.columns)
            for symbol, row in df.iterrows():
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price, sep="\t",parse_dates=['date'], index_col=['date'])

                    if LAST_REMOVED_ROWS:
                        if dfPrice.shape[0] <= LAST_REMOVED_ROWS:
                            continue
                        else: 
                            dfPrice=dfPrice.iloc[0:len(dfPrice)-LAST_REMOVED_ROWS]

                    sts = stimeseries(dfPrice.tail(500))
                    if weekly:
                        sts = stimeseries(dfPrice)
                        sts.to_weekly()
                    if sts.in_uptrend(window, cutoff, blind)==1:
                        if filter_ema_slice:
                            indicator_ceiling=""
                            indicator_base=""
                            if ',' in filter_ema_slice:
                                list=filter_ema_slice.split(',')
                                indicator_ceiling=list[0]+'MA'
                                indicator_base   =list[1]+'MA'
                            else:
                                indicator_base   =filter_ema_slice+'MA'
                                
                            #dfPrice=cdstk.cstick_sma(dfPrice)
                            dfPrice=sts.df
                            
                            sts.sma_multiple()
                            if sts.cross_up("3MA", indicator_base, int(window/2)) : continue
                            
                            if not dfPrice['20MA'][0-window] < dfPrice['20MA'][-1] : continue
                            if not sandwiched(filter_ema_slice, dfPrice.iloc[-1,:]): continue
                            
                        symbols = symbols.append(df.loc[symbol], ignore_index=False)
            df=symbols
            print (f"# {df.shape[0]:>5} symbols meet uptrend-{uptrend} criteria")

        if kwargs["filter_madistance"] >0:
            """ filter for symbols with yesterday's price greater than moving average and then sorted by
                today's distance to moving average
                symbol list will be shortened
            """        
            filter_madistance = kwargs["filter_madistance"]
            symbols = pd.DataFrame(columns=df.columns)
            for symbol, row in df.iterrows():
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price,sep="\t",index_col=0)
                    
                    if LAST_REMOVED_ROWS:
                        if dfPrice.shape[0] <= LAST_REMOVED_ROWS:
                            continue
                        else: 
                            dfPrice=dfPrice.iloc[0:len(dfPrice)-LAST_REMOVED_ROWS]

                    dfPrice=dfPrice.tail(500)
                    sts = stimeseries(dfPrice)
                    dist_day_before2 = sts.get_SMAdistance(filter_madistance, -2)
                    dist_day_before3 = sts.get_SMAdistance(filter_madistance, -3)
                    if dist_day_before2 > 0 and dist_day_before3 >0:
                        series = df.loc[symbol].copy(deep=True)
                        series['Sort'] = sts.get_SMAdistance(filter_madistance, -1)
                        symbols = symbols.append(series, ignore_index=False)
            df=symbols
            df=df.sort_values(["Sort"],ascending=True)
      
        # read SPY data
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
            price = dir+"/"+sticker+".txt"
            if os.path.exists(price):
                df=pd.read_csv(price, sep="\t",parse_dates=['date'], index_col=['date'])

                #print(sticker, df.shape)
                
                if LAST_REMOVED_ROWS:
                    row_num = df.shape[0]
                    if row_num <= LAST_REMOVED_ROWS + 100:
                        continue
                    else: 
                        df = df.head(row_num-LAST_REMOVED_ROWS)

                #print(sticker, df.shape)
                           
                rsi = str(stimeseries(df).get_rsi())[0:4]

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
                        draw(file_name, this_batch, c, panel_row, panel_col, to_be_recycled, 
                             dayspan, gradient, figwidth, figdepth)
                        this_batch={}
                if len(this_batch)>0:
                    draw(file_name, this_batch, c, panel_row, panel_col, to_be_recycled, 
                         dayspan, gradient, figwidth, figdepth)
                    this_batch={}

    def draw(file_name,
             securities,
             count,
             panel_row, panel_col,
             to_be_recycled,
             dayspan=200,
             gradient=9,
             figwidth=40,
             figdepth=24,
             dualscale=False,
             drawbyrow=False):
        
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
                                           figwidth, figdepth,
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
        draw_list_candlestick(list, **vars(args))
