#!/Users/air1/anaconda3/bin/python
# cmp v1:  handle multiple datasets and plot multi-panel figure
# cmp v20: given a list ticker and directory holding price data, do multi-panel
#          candlestick plot
# cmp v21: handel zacks data only (need 'Date Added' information)

import os
import re
import sys
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import module.candlestick as cdstk
from module.candlestick import Security
import module.utility as utility

from matplotlib.font_manager import FontProperties

if __name__ == "__main__":

    def draw_list_candlestick(file, vgm, uptrend, sort_trange, sort_madistance, sort_brokerrecomm,
                            sort_industry, dayspan, dateAddedSort, cutoffBroker, cutBrokerbuyCount,gradient, filterOnly):
        """
            draw candlestick for a list of sticker listed in a file
            the stick prices are stored in a directory
        """
        #
        # pre-processing rank_data
        df = pd.read_csv(file, sep="\t")
        df = df[~df["Industry"].str.contains("Oil and Gas")]
        
        if "Date Added" in df.columns:
            df["Date Added"] = df["Date Added"].apply(utility.fix_dateAdded)
            df["Date Added"] = pd.to_datetime(df["Date Added"])
        if "Date Sold" in df.columns:
            df["Date Sold"] = df["Date Sold"].apply(utility.fix_dateAdded)
            df["Date Sold"] = pd.to_datetime(df["Date Sold"])

        # sort names by symbol (default) or date
        if dateAddedSort and "Date Added" in df.columns:
            df = df.sort_values(by="Date Added", ascending=True)
        else:
            df = df.sort_values(by="Symbol")
        df = df.set_index("Symbol")
        #df_filtered = pd.DataFrame(columns=df.columns)
        df_filtered = pd.DataFrame()
                
        num_stickers = df.shape[0]
        print (f"#-> {num_stickers} names in ", end="")
        
        file_name = cdstk.file_strip_txt(file)
        print (file_name)
        if vgm:
            file_name = file_name + ".vgm"
        if abs(uptrend)>0:
            file_name = file_name + ".u" + str(uptrend)     
        if sort_trange:
            file_name = file_name + ".sTradingRange"
        if sort_madistance:
            file_name = file_name + ".sMAdist"
        if sort_brokerrecomm:
            file_name = file_name + ".sBroker"
        if sort_industry:
            file_name = file_name + ".sIndustry"
        if cutoffBroker>0:
            file_name = file_name + ".cbr" + str(int(cutoffBroker*100))
        if cutBrokerbuyCount>0:
            file_name = file_name + ".cbc" + str(int(cutBrokerbuyCount))        
        
        securities={}
        count=1000
        
        # specify number of rows and columns for the whole chart
        panel_row= cdstk.set_row_num(num_stickers)
        if panel_row > 4:
            panel_row = 4
        panel_col=panel_row
        if ',' in dayspan:
            panel_col = int((panel_col+1)/2)
            
        to_be_recycled=[]    
        
        #
        # sort names by up trading range in descending order
        # first sort by 20-day trading range (when >0.05)
        # then  sort by 60-day trading range (when >0.05)
        cut_forSort_20d = "0.05"
        cut_forSort_60d = "0.05" 
        if sort_trange:
            symbols = df.copy(deep=True)
            symbols.to_csv("test0.txt")
            symbols["up_tranding_range_20d"]=pd.Series(0,index=symbols.index)
            symbols["up_tranding_range_60d"]=pd.Series(0,index=symbols.index)
            symbols.to_csv("test1.txt")
            for symbol, row in df.iterrows():
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price,sep="\t",index_col=0)
                    prices = dfPrice["4. close"]
                    price_max_20day = prices.tail(20).max()
                    price_max_60day = prices.tail(60).max()
                    price_latest = prices[-1]
                    #print (price_max_20day, price_max_60day, price_latest)
                    price_change_20d = (price_max_20day-price_latest)/price_max_20day
                    if price_change_20d < cut_forSort_20d:
                        price_change_20d = 0
                    price_change_60d = (price_max_60day-price_latest)/price_max_60day
                    if price_change_60d < cut_forSort_20d:
                        price_change_60d = 0
                        
                    symbols.loc[symbol,"up_tranding_range_20d"]=price_change_20d
                    symbols.loc[symbol,"up_tranding_range_60d"]=price_change_60d
            df=symbols
            df=df.sort_values(["up_tranding_range_20d","up_tranding_range_60d"],ascending=[False,False])
            df.to_csv(file_name+".txt")
            
        if sort_madistance:
            symbols = df.copy(deep=True)
            symbols["close-50MA"]=pd.Series(0,index=symbols.index)
            for symbol, row in df.iterrows():
                ratio=1
                price = dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    dfPrice=pd.read_csv(price,sep="\t",index_col=0)
                    dfPrice=cdstk.cstick_sma(dfPrice)
                    last_price = dfPrice["4. close"][-1]
                    last_50MA  = dfPrice["50MA"][-1]
                    if last_50MA > 0:
                        ratio = (last_price-last_50MA)/last_50MA
                    symbols.loc[symbol,"close-50MA"]=ratio
            df=symbols
            df=df.sort_values(["close-50MA"],ascending=True)
            
        if sort_brokerrecomm and "# Rating Strong Buy or Buy" in df:
            df=df.sort_values(["# Rating Strong Buy or Buy"],ascending=False)
        if sort_industry and "Industry" in df:
            df=df.sort_values(["Industry"])
        #
        # read SPY data
        spy =  dir+"/"+"SPY"+".txt"
        ref = ""
        if os.path.exists(spy):
            mydf=pd.read_csv(spy,sep="\t",index_col=0)
            mydf["close_shift1"] = mydf["4. close"].shift(periods=1)
            mydf["weather"]=(mydf["4. close"]-mydf["close_shift1"])/mydf["close_shift1"]
            ref=pd.DataFrame(mydf["weather"],index=mydf.index) 
                
        #
        # plot multi-panel figure while going through a list of symbols
        for sticker, row in df.iterrows():
            row_copy = row.copy(deep=True)
            count+=1
            # prepare figure header
            note = ""
            # prepare head note for display in chart
            if "Zacks Rank" in row:
                note = note + " ZR-{}".format(str(int(row["Zacks Rank"])))
            if "Value Score" in row:
                if vgm and not utility.pick_V_G_VGM(row):
                    continue
                note = note + "{}/{}".format(row["Value Score"],
                                      row["Growth Score"]
                                      #row["Momentum Score"],
                                      #row["VGM Score"]
                                      )
            if "# Rating Strong Buy or Buy" in row and "# of Brokers in Rating" in row:
                note = note + " BR-{}/{}".format(int(row["# Rating Strong Buy or Buy"]),
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
                note = note + " TLG-{}".format(row["Long-Term Growth Consensus Est."])
            
            # test existence of data for the given symbol
            price = dir+"/"+sticker+".txt"
            if os.path.exists(price):
                df=pd.read_csv(price,sep="\t",index_col=0)
                if len(ref)>30:
                    df = df.join(ref)
                df = cdstk.cstick_sma(df)
                  
                # exame 30 timepoint in specified trading day period
                # pass if only 80% or more timepoints support uptrend
                # otherwise skip this name
                if abs(uptrend)>0:
                    # skip new stocks with few days with price data
                    if len(df) < abs(uptrend):
                        continue
                    # exame values of price and move averages
                    def ma_inorder(aday):
                        i = 0
                        if (aday["50MA"]>=aday["200MA"]) and (aday["150MA"]>=aday["200MA"]):
                                if uptrend>0:
                                    i=1
                                elif uptrend<0 and aday["4. close"] >= aday["50MA"]:
                                    i=1
                        return i

                    count_order=0
                    checkpoint= abs(int(uptrend/3))
                    cutoff = 0.75
                    retrospect = 0 - abs(uptrend)
                    recorded = 0 - len(df)
                    if recorded > retrospect:
                        retrospect = recorded
                        
                    for index in range(-1, retrospect, int(retrospect/checkpoint)):
                        day = df.iloc[index,:]
                        count_order += ma_inorder(day)
                    
                    if count_order < checkpoint*cutoff:              
                        continue

                    print (f"{sticker:<6}", f"{count_order}/{checkpoint}", sep="###")
                
                # load the name and annotations to a dictionary
                df_filtered= df_filtered.append(row_copy,ignore_index=False)
                
                mysecurity = Security(df)
                if "Date Added" in row:
                    date = row["Date Added"]
                    mysecurity.set_date_added(date)
                if "Date Sold" in row:
                    date = row["Date Sold"]
                    if date and date != "na" and date != "NA":
                        mysecurity.set_date_sold(utility.fix_dateAdded(date))
                if "Industry" in row:
                    mysecurity.set_industry(row["Industry"])
                securities[f"{sticker}: {note}"] = mysecurity
                
            else:
                print (price, " doesn't exist")
                df_filtered= df_filtered.append(row_copy,ignore_index=False)                
            # plot multi-panel figure once sufficient datasets
            # accumulate in dict mydfs
            
            if len(securities) == panel_col * panel_row and (not filterOnly):
                draw(file_name, securities, count, panel_row, panel_col, to_be_recycled, dayspan, gradient)
                #print ("", end="\r", flush=True)
        # plot multi-panel figure for the remaining datasets
        if len(securities)>0 and (not filterOnly):
            draw(file_name, securities, count, panel_row, panel_col, to_be_recycled, dayspan, gradient)
            #print ("", end="\r", flush=True)
        df_filtered.index.name="Symbol"
        
        if filterOnly:
	        df_filtered.to_csv(file_name+".txt",sep="\t")
        
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
             dualscale=False,
             drawbyrow=False):
        output = "xcandle."+ file_name +f"_{dayspan}d."+ str(count) +".pdf"

        recycle = cdstk.draw_many_candlesticks(securities, output,
                                           panel_row, panel_col,
                                           40, 24,
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
                        default="/Users/air1/Watchlist/daliyPrice",
                        help=": a direcotry holding price data for symbols")
    parser.add_argument("-p","--period",
                        type=str, default="200",                        
                        help=": length of period (days) to plot")
    parser.add_argument("-g","--gradient",
                        type=int, default=8,
                        help=": size gradient of plot box")
    # FILTERING
    parser.add_argument("-cvg", "--vgm" ,
                        help=": set filter on for VGM",
                        action='store_true')
    parser.add_argument("-cup", "--uptrend" ,
                        type=int, default=0,
                        help=": set period length for uptrend definition")
    parser.add_argument("-cbr", "--cutBrokerbuyRatio",
                        type=float, default=0,
                        help=": set cut-off for broker buy recommendation ratio")
    parser.add_argument("-cbc", "--cutBrokerbuyCount",
                        type=float, default=0,
                        help=": set cut-off for broker buy recommendation count")
    # SORT
    parser.add_argument("-da","--dateAdded",
                        help=": sort by date added",
                        action='store_true')
    parser.add_argument("-str", "--sort_trange",
                        help=": sort by up trading range",
                        action='store_true')
    parser.add_argument("-smd", "--sort_madistance",
                        help=": sort by up trading range",
                        action='store_true')
    parser.add_argument("-sbr", "--sort_brokerrecomm",
                        help=": sort by up trading range",
                        action='store_true')
    parser.add_argument("-sid", "--sort_industry",
                        help=": sort by industry",
                        action='store_true')
    
    # SKIP CHARTING
    parser.add_argument("-f", "--filterOnly",
                        default=False,
                        help=": filter names only",
                        action='store_true')
    args=parser.parse_args()


    # main code
    dir = args.dir
    for list in args.list:
        draw_list_candlestick(list, args.vgm, args.uptrend, args.sort_trange, 
                                args.sort_madistance,
                                args.sort_brokerrecomm,
                                args.sort_industry,
                                args.period,
                                args.dateAdded,
                                args.cutBrokerbuyRatio,
                                args.cutBrokerbuyCount,
                                args.gradient,
                                args.filterOnly)

