import os
import sys
import numpy as np
import pandas as pd
import module.candlestick as cdstk
import module.utility as utility
from module.stimeseries import stimeseries

class descriptions:
    def __init__(self, descriptions, data_dir, file_name, kwargs):
        self.descriptions = descriptions.copy(deep=True)
        self.data_dir = data_dir
        self.file_name = file_name
        self.kwargs_backup = kwargs
        self.kwargs = kwargs
        self.new_file_name = ""
        self.sts_daily = {}
    
    def get_new_descriptions(self):
        return self.descriptions
        
    def get_new_file_name(self):
        return self.new_file_name
        
    def basic_processing(self):
        """
        Basic data processing
        """        
        df = self.descriptions 
        if "Industry" in df:
           df = df[~df["Industry"].str.contains("Oil and Gas")]
        
        # format data-added and -sold information
        if "Date Added" in df.columns:
            df["Date Added"] = df["Date Added"].apply(utility.fix_dateAdded)
            df["Date Added"] = pd.to_datetime(df["Date Added"])
        if "Date Sold" in df.columns:
            df["Date Sold"] = df["Date Sold"].apply(utility.fix_dateAdded)
            df["Date Sold"] = pd.to_datetime(df["Date Sold"])
        if "Ticker" in df and "Symbol" not in df:
            df["Symbol"] = df["Ticker"]
        
        # sort securities by name (default) or by date-added
        if self.kwargs["sort_dateAdded"] and "Date Added" in df.columns:
            df = df.sort_values(by="Date Added", ascending=True)
        else:
            df = df.sort_values(by="Symbol")
        if "Symbol" in df:
            df = df.set_index("Symbol")
        else:
            print ("#-x No 'Symbol' column in the input security data sheet")
            exit(1)

        self.descriptions = df



        
        
        
    def work(self):
        if self.kwargs["sort_brokerrecomm"]  and "# Rating Strong Buy or Buy" in self.descriptions:
            self.descriptions = self.descriptions.sort_values(["# Rating Strong Buy or Buy"], 
                                ascending=False)
            del self.kwargs['sort_brokerrecomm']
            
        if self.kwargs["sort_industry"] and "Industry" in self.descriptions:
            self.descriptions = self.descriptions.sort_values(["Industry"])
            del self.kwargs["sort_industry"]
            
        if self.kwargs["sort_earningDate"]:            
            if "Next EPS Report Date  (yyyymmdd)" in self.descriptions:
                self.descriptions["Next EPS Report Date "] = self.descriptions["Next EPS Report Date  (yyyymmdd)"]
                self.descriptions=self.descriptions.drop("Next EPS Report Date  (yyyymmdd)", axis=1)
        
            if "Next EPS Report Date " in self.descriptions:
                #sort symbols by last earning date
                self.descriptions["Next EPS Report Date "]=self.descriptions.to_numeric(df["Next EPS Report Date "])
                self.descriptions=self.descriptions.sort_values(["Next EPS Report Date "], ascending=True)

        if self.kwargs["sort_zacks"]:
            sort_zacks = self.kwargs["sort_zacks"]
            type=''
            cut =''
            if ',' in sort_zacks:
                (type, cut) = sort_zacks.split(',')
                cut = cut.upper()
            else:
                type=sort_zacks
                            
            if   type=='V' and "Value Score" in self.descriptions:
                if cut:
                    self.descriptions = self.descriptions[ self.descriptions["Value Score"]<= cut ]
                    print (f"# {self.descriptions.shape[0]:>5} symbols meeting Value cutoff {cut}")
                self.descriptions = self.descriptions.sort_values(["Value Score"])
            elif type=='G' and "Growth Score" in self.descriptions:
                if cut:
                    self.descriptions = self.descriptions[ self.descriptions["Growth Score"]<= cut ]
                    print (f"# {self.descriptions.shape[0]:>5} symbols meeting Growth cutoff {cut}")
                self.descriptions = self.descriptions.sort_values(["Growth Score"])
            else:
                print (f"invalide input for -szk: {sort_zacks}")
                exit(1)
            del self.kwargs["sort_zacks"]
            
        if len(self.kwargs)>0:
            # load all price data to dict to iterate through later on
            dict_sts = {}        
            for symbol, row in self.descriptions.iterrows():
                price = self.data_dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    price=pd.read_csv(price,sep="\t",index_col=0)              
                    sts = stimeseries(price)
                    sts.sma_multiple()
                    dict_sts[symbol]=sts
                else:
                    self.descriptions = self.descriptions.drop(symbol)

            self.sts_daily = dict_sts 

            # method sort_trange
            if self.kwargs["sort_trange"]:
                """
                Sort a list of securities based on their upward trading range for a defined recent 
                period
                
                Outcome: update instance variable 'description'
                """            
                argument = self.kwargs["sort_trange"]
                days, cutoff = argument.split(',')
                trange_days   = int(days)
                trange_cutoff = float(cutoff)
                self.descriptions["Sort"] = 0
                if trange_days>0:
                    for symbol, row in self.descriptions.iterrows():
                        self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].get_trading_uprange(trange_days)
                if trange_cutoff >=0:
                    self.descriptions = self.descriptions.loc[ self.descriptions["Sort"]>=trange_cutoff ]
                self.descriptions = self.descriptions.sort_values(["Sort"], ascending=False)
                print (len(self.descriptions), " symbols meet user criterion")


            # method filter_macd_sig
            if self.kwargs["filter_macd_sig"]:
                """ 
                Filter securities based on MACD cross above signal line
                
                Outcome: shorten instance variable 'description'
                
                example: input varialbe "14,20"
                    K line with 14-day EMA and D line with 20-day EMA
                """
                filter_macd_sig = self.kwargs["filter_macd_sig"]
                try:
                    (sspan, lspan) = list(map(int, filter_macd_sig.split(',')))
                except ValueError:
                    print ("macd argument cannot be recognized")
                    exit(1)
                
                self.descriptions["Sort"] = 0
                for symbol in self.descriptions.index:
                    self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].macd_cross_up(sspan, lspan, 3)    
                self.descriptions = self.descriptions.loc[ self.descriptions["Sort"]>0 ]
                print (len(self.descriptions), " symbols meet user criterion")

            #"""
            if self.kwargs["sort_madistance"] >0:
                #sort symbols by last close-to-SMA distance
                
                sort_madistance = self.kwargs["sort_madistance"]
            
                self.descriptions["Sort"] = 0
                for symbol in self.descriptions.index:
                    self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].get_SMAdistance(sort_madistance)
                self.descriptions = self.descriptions.sort_values(["Sort"], ascending=True)
            #"""

            # method filter based on stochastic signal
            if self.kwargs["filter_stochastic_sig"]:
                """ filter for oversold (d < cutoff) tickers with stochastic K > D and
                    bullish price action (paction < cutoff)
                    input string: stochastic long term, 
                                  stochastic short term, 
                                  stochastic d cutoff, 
                                  k>d ('all') or k just cross d up ('crs' or any string)
                """
                filter_stochastic_sig = self.kwargs["filter_stochastic_sig"]
                try:
                    (n, m, cutoff, mode) = filter_stochastic_sig.split(',')
                    n = int(n)
                    m = int(m)
                    cutoff = float(cutoff)
                except:
                    e = sys.exc_info()[0]
                    print("x-> stochastic input is invalide ", e)
                    sys.exit(1)

                for symbol in self.descriptions.index:
                    (k, d, cross, bullish) = dict_sts[symbol].stochastic_cross(n, m)
                    status = True
                    if k>cutoff+15 or d>cutoff:
                        status = False
                    if mode =='all': 
                        if k<d: status = False
                    elif cross<=0:
                        status = False
                    if not status: 
                        self.descriptions.drop(symbol, inplace=True)
                print ("# {:>5} symbols meet stochastic criteria".format(len(self.descriptions)))

            if self.kwargs["two_dragon"]:
                two_dragon = self.kwargs["two_dragon"]
                array = two_dragon.split(',')
                array2=[]
                try:
                    array2 = list(map(int, array[0:3]))
                except ValueError:
                    print (f" argument {two_dragon} is invalid")
                    exit(1)
                if len(array)==4:
                    array2.append(float(array[3]))
                
                self.descriptions["Sort"] = 0
                for symbol in self.descriptions.index:
                    self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].two_dragon(*array2)    
                self.descriptions = self.descriptions.loc[ self.descriptions["Sort"]>0 ]

                print ("# {:>5} symbols meet 2dragon criteria {}".format( len(self.descriptions), two_dragon ) )

            # method sort_sink
            if self.kwargs["sort_sink"]:
                """ 
                Sort securities by price change in a defined period relative to a reference date
                
                Outcome: update instance variable 'description'
                
                example: input varialbe "2020-20-01,4"
                    set 2020-20-01 as reference date, calculate the average price of the 
                    following 4 day, and report the change that led to this average price and from
                    the reference date
                """
                sort_sink = self.kwargs["sort_sink"]
                aa = sort_sink.split(',')
                reference_date = aa[0]
                days  = int(aa[1])
            
                self.descriptions["Sort"] = 0
                for symbol, row in self.descriptions.iterrows():
                    self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].get_referenced_change(reference_date, days)
                    
                self.descriptions = self.descriptions.sort_values(["Sort"], ascending=True)
                self.descriptions["Date Added"] = reference_date

            # method filter and sort by last close to bollinger band bottom border distance
            if self.kwargs["sort_bbdistance"]:
                sort_bbdistance = self.kwargs["sort_bbdistance"]
                list_arg = sort_bbdistance.split(',')
                cutoff = float( list_arg[0] )
                days   = 1
                if len(list_arg)==2: days= int(list_arg[1])
            
                self.descriptions["Sort"] = 0
                for symbol, row in self.descriptions.iterrows():
                    self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].get_BBdistance(days)
                
                self.descriptions = self.descriptions.loc[ self.descriptions["Sort"] <= cutoff ]
                self.descriptions = self.descriptions.sort_values(["Sort"], ascending=True)
            #"""

            if self.kwargs["sort_performance"]:
                sort_performance = self.kwargs["sort_performance"]
            
                self.descriptions["Sort"] = 0
                for symbol in self.descriptions.index:
                    self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].get_latest_performance(sort_performance)
                
                self.descriptions = self.descriptions.sort_values(["Sort"], ascending=False)
            #"""
            
            #"""
            if self.kwargs["uptrend"]:
                uptrend = self.kwargs["uptrend"]
                args = uptrend.split(',')

                self.descriptions["Sort"] = 0
                for symbol in self.descriptions.index:
                    self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].in_uptrendx(*args)
                
                self.descriptions = self.descriptions.loc[ self.descriptions["Sort"] >0 ]
                print ("# {:>5} symbols meet uptrend criteria {}".format( len(self.descriptions), uptrend ) )
            #"""
                
            if self.kwargs["filter_ema_slice"]:
                filter_ema_slice = int(self.kwargs["filter_ema_slice"])
                
                self.descriptions["Sort"] = False
                for symbol in self.descriptions.index:
                    self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].touch_down(filter_ema_slice)
                
                self.descriptions = self.descriptions.loc[ self.descriptions["Sort"] ]
                print ("# {:>5} symbols meet EMA slice criteria {}".format( len(self.descriptions), filter_ema_slice ) )