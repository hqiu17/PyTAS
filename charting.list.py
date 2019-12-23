#!/usr/local/bin/python
# cmp v1:  handle multiple datasets and plot multi-panel figure
# cmp v20: given a list ticker and directory holding price data, do multi-panel
#          candlestick plot
# cmp v21: handel zacks data only (need 'Date Added' information)

import os
import re
import sys
import copy
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import module.candlestick as cdstk
from module.candlestick import Security
from module.stimeseries import stimeseries
import module.utility as utility

from matplotlib.font_manager import FontProperties


def sandwiched(string, series):
    """
    """
    status = True
    high=""
    low =""
    if ',' in string:
        list=string.split(',')
        high=list[0]+'MA'
        low =list[1]+'MA'
    else:
        high=string +'MA'
    
    if  series['3. low']<=series[high] and series[high] <= series['4. close']:
        status = True
    elif low:
        if series[low] <= series['4. close'] and series['4. close']<= series[high]:
            status = True
        else:
            status=False
    else:
        status=False
        
    #print (status, string, list(series) )
    return status


if __name__ == "__main__":

    def draw_list_candlestick(file, vgm, weekly, weeklyChart, uptrend, sort_zacks, sort_trange, sort_madistance, sort_bbdistance, sort_brokerrecomm,
                              sort_industry, sort_performance, edaySort, dayspan, dateAddedSort, filter_madistance, cutoffBroker, cutBrokerbuyCount,
                              gradient, sort_sink, blind, filterOnly, filter_macd_sig, filter_stochastic_sig, filter_ema_slice, two_dragon, sample):
        """ chart a list of stickers listed in a file
            the stick prices data are stored in a directory
        """
        
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
        if dateAddedSort and "Date Added" in df.columns:
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
            if sample:
                file_name = file_name + ".hist_"+sample
            if filterOnly:
                file_name = file_name + ".filtered"
            if vgm:
                file_name = file_name + ".cvg"
            if blind>0:
                file_name = file_name + ".bld" + str(blind)
            if uptrend:
                file_name = file_name + ".cup" + uptrend.replace(',','-')
            if cutoffBroker>0:
                file_name = file_name + ".cbr" + str(int(cutoffBroker*100))
            if cutBrokerbuyCount>0:
                file_name = file_name + ".cbc" + str(int(cutBrokerbuyCount))
            if sort_zacks:
                file_name = file_name + ".szk" + sort_zacks.replace(',','') # sort by upside trading range                
            if sort_trange==0:
                file_name = file_name + ".str"    # sort by upside trading range
            elif sort_trange>0:
                file_name = file_name + ".str" + str(int(sort_trange*100))  # sort by upside trading range
            if sort_madistance>0:
                file_name = file_name + ".sma" + str(sort_madistance)   # sort by distance to 50MA
            if sort_bbdistance:
                file_name = file_name + ".sbd"   # sort by distance to bollinger band floor
            if sort_brokerrecomm:
                file_name = file_name + ".sbr"   # sort by broker recommendation ratio
            if sort_performance>0:
                file_name = file_name + ".spf" + str(int(sort_performance)) # sort by performance
            if sort_industry:
                file_name = file_name + ".sid"    # 
            if ',' in sort_sink:
                file_name = file_name + ".ssk"    # 
            if edaySort:
                file_name = file_name + ".sed"    # 
            if filter_madistance>0:
                file_name = file_name + ".fma" + str(filter_madistance)    #
            if filter_macd_sig:
                file_name = file_name + ".macd" + filter_macd_sig.replace(',','-')
            if filter_stochastic_sig:
                file_name = file_name + ".stks" + filter_stochastic_sig.replace(',','-')
            if filter_ema_slice:
                file_name = file_name + ".mslc" + filter_ema_slice.replace(',','-')
            if two_dragon:
                file_name = file_name + ".2drgn" + str(two_dragon).replace(',','-')
                
            if weekly:
                file_name = file_name + ".wkly"
            if weeklyChart:
                file_name = file_name + ".wklyc"
                
        # specify number of rows and columns for the whole chart
        figwidth=40
        figdepth=24
        default_row_num=args.rownumber
        if "," in dayspan:
            default_row_num=5
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

        if sort_brokerrecomm and "# Rating Strong Buy or Buy" in df:
            df=df.sort_values(["# Rating Strong Buy or Buy"],ascending=False)
            
        if sort_industry and "Industry" in df:
            df=df.sort_values(["Industry"])

        if sort_zacks:
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
                        
        if sort_trange >=0:
            """ sort symbols by upside tranding range defined as the difference between last
                close and the highest close in specified time range
            """             
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

        if filter_macd_sig:
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
            
        if filter_stochastic_sig:
            """ filter for oversold (d < cutoff) tickers with stochastic K > D and
                bullish price action (paction < cutoff)
                input string: stochastic long term, 
                              stochastic short term, 
                              stochastic d cutoff, 
                              k>d ('all') or k just cross d up ('crs' or any string)
            """
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
            symbols=symbols.loc[ symbols['BLSH'] < 0.4 ]

            if mode == "all":
                # count all instances where K>D
                symbols=symbols.loc[ symbols['STOD'] < symbols['STOK'] ]
            else:
                # count instances reflecting transit from K<D to K>D
                symbols=symbols.loc[ symbols['STOC'] > 0 ]
            df = symbols
            print (f"# {df.shape[0]:>5} symbols meet stochastic criteria")   
            
        if two_dragon:
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

        if sort_madistance >0:
            """ sort symbols by last close-to-SMA distance
            """
            symbols = df.copy(deep=True)
            symbols["Sort"]=pd.Series(0,index=symbols.index)
            for symbol, row in df.iterrows():
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price, sep="\t",parse_dates=['date'], index_col=['date'])
                    sts = stimeseries(dfPrice.tail(500))
                    if weekly:
                        sts = stimeseries(dfPrice)
                        sts.to_weekly()
                    symbols.loc[symbol,"Sort"]=sts.get_SMAdistance(sort_madistance)
            df=symbols
            df=df.sort_values(["Sort"],ascending=True)
            
        if sort_bbdistance:
            symbols = df.copy(deep=True)
            symbols["Sort"]=pd.Series(100,index=symbols.index)
            for symbol, row in df.iterrows():
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price, sep="\t",parse_dates=['date'], index_col=['date'])
                    sts = stimeseries(dfPrice.tail(500))
                    if weekly:
                        sts = stimeseries(dfPrice)
                        sts.to_weekly()
                    symbols.loc[symbol,"Sort"]=sts.get_BBdistance()
            df=symbols
            df=df.sort_values(["Sort"],ascending=True)
            
        if sort_performance >0:
            """ sort symbols by recent performance
            """         
            symbols = df.copy(deep=True)
            symbols["performance"]=pd.Series(0,index=symbols.index)
            for symbol, row in df.iterrows():
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price,sep="\t",index_col=0)
                    dfPrice=dfPrice.tail(500)
                    sts = stimeseries(dfPrice)
                    symbols.loc[symbol,"performance"] = sts.get_latest_performance(sort_performance)
            df=symbols
            df=df.sort_values(["performance"],ascending=False)

        if edaySort and "Next EPS Report Date " in df:
            """ sort symbols by last earning date
            """ 
            df["Next EPS Report Date "]=pd.to_numeric(df["Next EPS Report Date "])
            df=df.sort_values(["Next EPS Report Date "], ascending=True)

        if uptrend:
            """ filter for symbols in uptrend in a specified recent period
                symbol list will be shortened
            """
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
                    sts = stimeseries(dfPrice.tail(500))
                    if weekly:
                        sts = stimeseries(dfPrice)
                        sts.to_weekly()
                    if sts.in_uptrend(window, cutoff, blind)==1:
                        if filter_ema_slice:
                            #print (filter_ema_slice)
                            dfPrice=cdstk.cstick_sma(dfPrice)
                            if not dfPrice['20MA'][0-window] < dfPrice['20MA'][-1]: continue
                            if not sandwiched(filter_ema_slice, dfPrice.iloc[-1,:]):
                                continue
                        symbols = symbols.append(df.loc[symbol], ignore_index=False)
            df=symbols
            print (f"# {df.shape[0]:>5} symbols meet uptrend-{uptrend} criteria")

        if filter_madistance >0:
            """ filter for symbols with yesterday's price greater than moving average and then sorted by
                today's distance to moving average
                symbol list will be shortened
            """        

            symbols = pd.DataFrame(columns=df.columns)
            for symbol, row in df.iterrows():
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price,sep="\t",index_col=0)
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
      
        if "," in sort_sink:
            """ sort symbols by price change relative to a reference date
                example: input information [5, 4]
                set the fifth last day as reference, compare the average price of the 
                following 4 day and report the price change
            """
            symbols = df.copy(deep=True)
            symbols["sink"]=pd.Series(0,index=symbols.index)
            print (sort_sink)
            print (sort_sink.split(','))
            aa = sort_sink.split(',')
            #print ( (int for d in sort_sink.split(',')) )
            #dates=list(map(int, aa))
            dates=[2,1]
            date0=0-dates[0]
            daysforcompare=len(dates)
            for symbol, row in symbols.iterrows(): 
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price,sep="\t",index_col=0)
                    dfPrice=dfPrice.tail(500)
                    price_date0 = dfPrice["4. close"][date0]
                    price_examine=0
                    for i in range(date0+1, date0+daysforcompare, 1):
                        ## try
                        
                        price_examine += dfPrice["4. close"][i]
                    ratio=(price_examine - price_date0*(daysforcompare-1))/price_date0
                    symbols.loc[symbol,"Sort"]=ratio
            df=symbols
            df=df.sort_values(["Sort"],ascending=False)
            
            for s in df["Sort"]: print(s)



        # read SPY data
        spy =  dir+"/"+"SPY"+".txt"
        ref = ""
        if os.path.exists(spy):
            mydf=pd.read_csv(spy,sep="\t",index_col=0)
            mydf=mydf.tail(500)
            mydf["close_shift1"] = mydf["4. close"].shift(periods=1)
            mydf["weather"]=(mydf["4. close"]-mydf["close_shift1"])/mydf["close_shift1"]
            ref=pd.DataFrame(mydf["weather"],index=mydf.index) 
        
        ########################################################################
        #       loop through filtered symbol table and collect securities      #
        ########################################################################
        securities={}
        count=1000
        df_filtered = pd.DataFrame()

        wins=0
        losses=0
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
                if vgm and not utility.pick_V_G_VGM(row):
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
                if cutoffBroker>0:
                    myratio = row["# Rating Strong Buy or Buy"]/row["# of Brokers in Rating"]
                    if myratio < cutoffBroker:
                        continue
                if cutBrokerbuyCount>0:
                    if row["# Rating Strong Buy or Buy"] < cutBrokerbuyCount:
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

                #print(sticker)                
                rsi = str(stimeseries(df).get_rsi())[0:4]

                if weekly or weeklyChart: 
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

                if sample:
                    samples={}
                    sts = stimeseries(df)
                    if  sample == 'stks_bb':
                        samples,R,win,loss = sts.sampling_stks_bb(14, 3)
                        if len(samples)==0: continue
                        wins+=win
                        losses+=loss
                        print ('---------', sticker, '-------')
                        print(f"f {win:>6} {loss}")
                        for date, r in R.items():
                            Rtotal = Rtotal +r
                            if r >0 and r<0.001: r=0
                            print (f"r {str(r)[0:5]:>6} {Rtotal}")
                        
                    elif sample == 'below_bb':
                        samples = sts.sampling_below_bb()
                    elif sample == 'plunge_macd':
                        samples,R,win,loss = sts.sampling_plunge_macd()
                        if len(samples)==0: continue
                        wins+=win
                        losses+=loss
                        print ('---------', sticker, '-------')
                        print(f"f {win:>6} {loss}")
                        for date, r in R.items():
                            Rtotal = Rtotal +r
                            print (f"r {str(r)[0:5]:>6} {Rtotal}")
                        #Rtotal+= sum(list(R.values()))
                    for date, price in samples.items():
                        rsi = str(stimeseries(price).get_rsi())[0:3]
                        mysecurity = Security(price)                    
                        mysecurity.set_date_added(date)
                        r = R[date]
                        if r>0 and r <0.001: r=0
                        r=str(r)[0:5]
                        securities[f"{sticker}: {note} {date} {r}R"] = mysecurity
                else:
                    securities[f"{sticker}: {note} RSI-{rsi}"] = mysecurity

            else:
                print (price, " doesn't exist")
                df_filtered= df_filtered.append(row_copy,ignore_index=False)
            
        if sample:
            win_rate = str(wins/(losses+wins))[0:4]
            r_edge   = str(Rtotal/(wins+losses))[0:4]
            print (f"#    {wins}wins, {losses}losses, {win_rate}winrate; {str(Rtotal)[0:4]} totalR {r_edge}R edge")

        ########################################################################
        #   plot multi-panel figure while going through a list of securities   #
        ########################################################################
        if filterOnly:
            df_filtered.index.name="Symbol"
            df_filtered.to_csv(file_name+".txt",sep="\t")
            pd.set_option('display.max_rows', None)
            #pd.set_option('display.max_columns', None)
            print(df_filtered)
            
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
        
        """
        # plot "2 scale" while going through a list of dipped symbols
        mydfs.clear()
        to_be_recycled2 = to_be_recycled
        to_be_recycled = []
        panel_col =4
        panel_row =2
        if len(to_be_recycled2):
            for sticker in to_be_recycled2:
                mymatch = re.match(r'(\S+)\:.*', sticker)
                symbol = mymatch.group(1)
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    df=pd.read_csv(price,sep="\t",index_col=0)
                    mydfs[sticker]=df
                    
                    print (sticker, end=";")
                else:
                    print (price, " doesn't exist")
            
                if len(mydfs) == panel_col * panel_row:
                    draw(file_name, mydfs, count, panel_col, panel_row, to_be_recycled, 200, True, True)
                    print ("")
                count+=1
            
        # plot "2 scale" figure for the remaining dipped symbols
        if len(mydfs)>0:
            draw(file_name, mydfs, count, panel_col, panel_row, to_be_recycled, 200, True, True)
            print ("")
        """

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
           
    # parser
    text= "Given a symbol list, draw candlesticks for each of item"
    parser = argparse.ArgumentParser(description = text)
    parser.add_argument("list", 
                        nargs='*',
                        help=": a list of symbol in TSV")
    parser.add_argument("-d", "--dir" , 
                        default="/Users/air/watchlist/daliyPrice",
                        help=": a direcotry holding price data for symbols")
    parser.add_argument("-p","--period",
                        type=str, default="200",
                        help=": length of period (days) to plot")
    parser.add_argument("-g","--gradient",
                        type=int, default=1,
                        help=": size gradient of plot box")
    parser.add_argument("-r","--rownumber",
                        type=int, default=5,
                        help=": size gradient of plot box")
    parser.add_argument("-w", "--weekly",
                        default=False,
                        help=": analyze and chart data in weekly timeframe",
                        action='store_true')
    parser.add_argument("-wc", "--weeklyChart",
                        default=False,
                        help=": only chart data in weekly timeframe",
                        action='store_true')   
    # FILTERING
    parser.add_argument("-cvg", "--vgm" ,
                        help=": set filter on for VGM",
                        action='store_true')
    parser.add_argument("-cup", "--uptrend" ,
                        type=str, default="",
                        help=": set window for uptrend definition. example: 60,0.8,30 (window,cutoff,blind)")
    parser.add_argument("-cbr", "--cutBrokerbuyRatio",
                        type=float, default=0,
                        help=": set cut-off for broker buy recommendation ratio")
    parser.add_argument("-cbc", "--cutBrokerbuyCount",
                        type=float, default=0,
                        help=": set cut-off for broker buy recommendation count")
    parser.add_argument("-str", "--sort_trange",
                        type=float, default=-1,
                        help=": sort names by trading range, and cut if input value >0")
    parser.add_argument("-fmd", "--filter_madistance",
                        type=int, default=0,
                        help=": filter for price dipping to moving average")
    parser.add_argument("-macd", "--filter_macd_sig",
                        type=str, default="",
                        help=": filter for macd crossover upward")                 
    parser.add_argument("-stks", "--filter_stochastic_sig",
                        type=str, default="",
                        help=": filter for stochastic K>D signal. example 14,3,20,all or 14,3,20,crs")
                        
    parser.add_argument("-mslc", "--filter_ema_slice",
                        type=str, default="",
                        help=": filter for price range contain MA or last close sandwiched between 2 MAs. example 20 or 20,50")
    parser.add_argument("-2dgn", "--two_dragon",
                        type=str, default="",
                        help=": filter for uptrend defined by 2 moving average. example 20,50,60 or 20,50,60,0.8")
                        
    # SORT
    parser.add_argument("-szk","--sort_zacks",
                        type=str, default="",
                        help='sort (and filter)symbols by zacks type value(V) or growth(G) rank. example -szk V,a')    
    parser.add_argument("-sda","--sort_dateAdded",
                        help=": sort by date added",
                        action='store_true')
    parser.add_argument("-sed","--sort_earningDate",
                        help=": sort by next earning report date",
                        action='store_true')
    parser.add_argument("-sbr", "--sort_brokerrecomm",
                        help=": sort by up trading range",
                        action='store_true')
    parser.add_argument("-sid", "--sort_industry",
                        help=": sort by industry",
                        action='store_true')
    parser.add_argument("-ssk", "--sort_sink",
                        help=": sort by ratio of price down relative to reference date",
                        default="0")
    parser.add_argument("-spm", "--sort_performance",
                        type=int, default=0,
                        help=": sort by ratio of price down relative to reference date")
    parser.add_argument("-smd", "--sort_madistance",
                        type=int, default=0,
                        help=": sort by last close to SMA distance")
    parser.add_argument("-sbd", "--sort_bbdistance",
                        help=": sort by last close to bollinger bank bottom border distance",
                        action='store_true')
    parser.add_argument("-bld", "--blind",
                        type=int, default=0,
                        help=": ignore the latest preriod (for hypothesis test)")

    # SAMPLING                        
    parser.add_argument("-smpl", "--sample",
                        type=str, default="",
                        help=": sample historical data point")

    # SKIP CHARTING
    parser.add_argument("-f", "--filterOnly",
                        default=False,
                        help=": filter names only",
                        action='store_true')
    args=parser.parse_args()


    # main code
    dir = args.dir
    for list in args.list:
        draw_list_candlestick(list, 
                                args.vgm,
                                args.weekly,
                                args.weeklyChart,
                                args.uptrend,
                                args.sort_zacks,
                                args.sort_trange, 
                                args.sort_madistance,
                                args.sort_bbdistance,
                                args.sort_brokerrecomm,
                                args.sort_industry,
                                args.sort_performance,
                                args.sort_earningDate,
                                args.period,
                                args.sort_dateAdded,
                                args.filter_madistance,
                                args.cutBrokerbuyRatio,
                                args.cutBrokerbuyCount,
                                args.gradient,
                                args.sort_sink,
                                args.blind,
                                args.filterOnly,
                                args.filter_macd_sig,
                                args.filter_stochastic_sig,
                                args.filter_ema_slice,
                                args.two_dragon,
                                args.sample
                                )
