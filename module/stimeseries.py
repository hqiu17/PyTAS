import numpy as np
import pandas as pd

class stimeseries:
    def __init__(self, df):
        self.df=df.copy(deep=True)
        
    def get_latest_performance(self, period):
        """ get the percentage price change for the last time period
            input  : period, an integer indicating how many 'day' backward 
            return : a percentage of price change
        """
        df_latest_period = self.df.tail(period)
        begin = df_latest_period["4. close"][0]
        last  = df_latest_period["4. close"][-1]
        performance=0
        if begin > 0:
            performance = (last-begin)/begin
        return performance
    
    def get_SMAdistance(self, benchmark, date=-1):
        """ get the distance between last closing price and specified SMA
            input  : days , time length to calculate simple moving average
            return : float, the difference in percentage
        """
        df=self.df.copy(deep=True)
        df["SMA"] =df["4. close"].rolling(benchmark).mean()
        distance=0
        if df["SMA"][date]>0:
            distance = (df["4. close"][date]-df["SMA"][date])/df["4. close"][date]
        return distance
        
    def get_BBdistance(self):
        self.sma_multiple()
        df=self.df.copy(deep=True)
        ratio = (df["3. low"][-1] - df["BB20d"][-1])/ ( df["BB20u"][-1] - df["BB20d"][-1])
        #print ( (df["4. close"][-1] - df["BB20d"][-1]), (df["4. close"][-1] - df["20MA"][-1]), ratio )
        return ratio
        
    def get_trading_uprange(self, day):
        """ get the distance between last closing price and the maximum price in specified time
            input  : days , time length to calculate maximum price
            return : float, the difference in percentage
        """
        df=self.df.copy(deep=True)
        prices = df["4. close"].tail(day)
        return (prices.max()-prices[-1])/prices.max()
    
    """
    def in_uptrend(self, days, interval=3, cutoff=0.75, blind=0):
        status=False
        df = self.df
        
        # record length is less than days required to figure out uptrend
        # return false since no judgement could be made
        if len(df)-blind < abs(days):
            return status

        # test uptrend signature for one day-point
        def ma_inorder(aday):
            i = 0
            if aday["50MA"]>=aday["150MA"] and aday["150MA"]>=aday["200MA"]:
                if days>0:
                    i=1
            elif days<0 and aday["4. close"] >= aday["50MA"]:
                    i=1
            return i

        count_all=0
        count_pass=0
        # set the beginning date and ending date of the test period
        oldest_date = 0 - abs(days) - blind
        latest_date = 0 - 1 - blind
        record_length = 0 - len(df)
        # if record length is long enough, move the beginning date earlier
        if record_length > oldest_date:
            oldest_date = record_length

        # loop through the test period and make test for each step
        for index in range(latest_date, oldest_date, 0-interval):
            aday = df.iloc[index,:]
            count_pass += ma_inorder(aday)
            count_all +=1
            #print (sticker, str(index), str(ma_inorder(day)), sep="\t")

        if (count_pass/count_all) > cutoff:
            status=True
        return status
    """
    
    def macd_cross_up(self, sspan=12, lspan=26, persist=1):
        df=self.df
        #df=self.df.copy(deep=True)
        exp1 = df['4. close'].ewm(span=sspan, adjust=False).mean()
        exp2 = df['4. close'].ewm(span=lspan, adjust=False).mean()
        macd = exp1 - exp2
        exp3 = macd.ewm(span=9, adjust=False).mean()
        df["signal"] = macd - exp3
        df["signal"] = np.where( df["signal"] >0, 1, 0)
          
        status = 0
        tail = df["signal"][-8:]
        switch = tail.diff().sum()
        landing = tail.sum()
        if (tail[0] == 0 and 
            tail[-1]== 1 and 
            switch  == 1 and 
            landing <= persist and 
            exp3[-1] < 0 ):
            status = 1
            #print(tail)
        return status
        
    def stochastic_cross_internal(self, n, m):
        df=self.df.copy(deep=True)
        high = df['2. high']
        low  = df['3. low']
        close= df['4. close']
        STOK = ( (close - low.rolling(n).min())/( high.rolling(n).max()-low.rolling(n).min() ) ) * 100
        STOD = STOK.rolling(m).mean()
        sgnl = STOK - STOD
        #sgnl = STOK - 18
        df["signal"] = np.where( sgnl>0, 1, 0)        
        paction = (df['2. high'] - df['4. close']) / ( df['2. high'] - df['3. low']) 
        return STOK, STOD, df["signal"].diff(), paction

    def stochastic_cross(self, n, m):
        """ return tuple of 4 values: k, d, k>d?(1/0), candlestick head size
        """
        stok, stod, signal, paction = self.stochastic_cross_internal(n, m)
        return stok[-1], stod[-1], signal[-1], paction[-1]
    
    def two_dragon_internal(self, MAdays1, MAdays2, TRNDdays, dataframe, cutoff=0.8):
        """ Test uptrend defined by 2 moving average indicators (internal version).
            In the defined period 'TRNDdays', if 80% of datapoint has moving average1
            greater than moving average2, return status(=1). 
        """
        status = 0
        df=dataframe.copy(deep=True)        
        ma1_key = str(MAdays1)+"MA"
        ma2_key = str(MAdays2)+"MA"
        
        if ma1_key in df.columns and ma2_key in df.columns:
            df['ma01'] = df[ma1_key]
            df['ma02'] = df[ma2_key]
        elif ( (TRNDdays+MAdays1)>df.shape[0] or (TRNDdays+MAdays2)>df.shape[0] ): 
            #print (f"Moving-avg {MAdays1} vs. {MAdays2} and window {TRNDdays} cannot be estimated for small data with {df.shape[0]} rows")
            return status
        else:
            df['ma01'] =df["4. close"].ewm(span=MAdays1,adjust=False).mean()
            df['ma02'] =df["4. close"].ewm(span=MAdays2,adjust=False).mean()
                        
        sgnl = df["ma01"] - df["ma02"]
        df["signal"] =np.where( sgnl>0, 1, 0)
        
        ratio = df.tail(TRNDdays)['signal'].sum()/TRNDdays
        if ratio > cutoff: 
            status = 1
        elif ratio < (1-cutoff):
            status = -1
        return status
        
    def two_dragon(self, MAdays1, MAdays2, TRNDdays, cutoff=0.8):
        """ Test uptrend defined by 2 moving average indicators (internal version).
            In the defined period 'TRNDdays', if 80% of datapoint has moving average1
            greater than moving average2, return status(=1). 
        """
        status = self.two_dragon_internal(MAdays1, MAdays2, TRNDdays, self.df, cutoff)
        return status
        
    def in_uptrend_internal(self, dataframe, TRNDdays, cutoff, blind):

        status = 0
        df = pd.DataFrame()
        if blind > 0 :
            if blind < dataframe.shape[0]:
                last_index = dataframe.shape[0] - blind
                df = dataframe[0:last_index]
            else:
                return status
    
        if df.shape[0] == 0:
            df = dataframe.copy(deep=True)
        count  = 0
        count += self.two_dragon_internal( 20, 50,TRNDdays, df, cutoff)
        count += self.two_dragon_internal( 50,100,TRNDdays, df, cutoff)
        count += self.two_dragon_internal(100,150,TRNDdays, df, cutoff)
        if count == 3: 
            status = 1
        elif count == -3:
            status = -1

        return status
        
    def in_uptrend(self, TRNDdays, cutoff=0.8, blind=0):
        return self.in_uptrend_internal(self.df, TRNDdays, cutoff, blind)
    
    def sma_multiple(self):
        self.df["20MA"] =self.df["4. close"].rolling(20).mean()
        self.df["50MA"] =self.df["4. close"].rolling(50).mean()
        self.df["100MA"]=self.df["4. close"].rolling(100).mean()
        self.df["150MA"]=self.df["4. close"].rolling(150).mean()
        self.df["200MA"]=self.df["4. close"].rolling(200).mean()
        self.df['STD20']=self.df["4. close"].rolling(20).std()
        self.df['BB20u']=self.df['20MA'] + self.df['STD20']*2
        self.df['BB20d']=self.df['20MA'] - self.df['STD20']*2
    
    def to_weekly(self):
        logic = {'1. open'  : 'first',
                 '2. high'  : 'max',
                 '3. low'   : 'min',
                 '4. close' : 'last',
                 '5. volume': 'sum'}
        offset = pd.offsets.timedelta(days=-6)
        self.df = self.df.resample('W', loffset=offset).apply(logic)
        
    def get_weekly(self):
        self.to_weekly()
        dataframe = self.df.copy(deep=True)
        return dataframe

    def sampling_stks_bb(self, n, m):
        prediction=20
        stok, stod, signal, paction = self.stochastic_cross_internal(n, m)
        sts=self.df.copy(deep=True)
        bb_dist_low   = (sts["3. low"]  -sts['BB20d'])/(sts['BB20u']-sts['BB20d'])
        bb_dist_close = (sts["4. close"]-sts['BB20d'])/(sts['BB20u']-sts['BB20d'])
        length = len(signal)
        
        win=0
        loss=0
        samples={}
        R={}
        for i in range(150, length-prediction):
            #print (signal[200])
            #if stod[i]<20 and signal[i]==1 and paction[i]<0.3 and bb_dist<0.05:
            
            # stochastic
            if stod[i] > 30   : continue
            if signal[i]<=0   : continue
            # candle pattern
            if paction[i]>0.3 : continue
            if sts['1. open'][i] > sts['4. close'][i]  : continue     
            if max(sts['4. close'][i-1],sts['1. open'][i-1]) > sts['4. close'][i] : continue
            # no transation
            if sts['2. high'][i] > sts['2. high'][i+1]  : continue

            """
            sts['20MA'][i]>sts['50MA'][i] and
            sts['50MA'][i]>sts['100MA'][i] and
            sts['100MA'][i]>sts['150MA'][i] and
            sts['150MA'][i]>sts['200MA'][i] and
            """
            #print (signal[i], stok.index[i], bb_dist_low[i], bb_dist_low[i-1],bb_dist_close[i])

            """
            if (bb_dist_low[i]<0.02 or bb_dist_low[i-1]<0 or bb_dist_low[i-2]<0)and bb_dist_close[i] <0.33:
                pass
            else:
                continue
            """
            
            if sts['4. close'][i]<sts['20MA'][i]: continue
            
            sub = sts.iloc[0:i+prediction-1]
            sub_test = sts.iloc[0:i+1]
            # in uptrend
            if self.in_uptrend_internal(sub_test, 90, 0.90, 0)==0: continue
            if self.in_uptrend_internal(sub_test, 60, 0.90, 0)==0: continue
            date= "{}".format(stok.index[i]).rstrip('00:00:00')
            if '18-12-' in date or '19-01-' in date: continue
            samples[date]=sub

            sts['5daymin'] = sts['3. low'].rolling(2).min()
            entry = sts['2. high'][i]
            sell_stoploss = sts['5daymin'][i]
            r_count = self.fate(sub, sts.index[i], entry, sell_stoploss, True)
            R[date]=r_count
            if r_count>0: win+=1
            if r_count<0: loss+=1
        return samples, R, win, loss

    def sampling_below_bb(self):
        samples={}
        sts=self.df.copy(deep=True)    
        bb_dist_close = (sts["4. close"]-sts['BB20d'])/(sts['BB20u']-sts['BB20d'])
        length = sts.shape[0]
        for i in range(100, length-15):
            if bb_dist_close[i] < -0.1 and sts['BB20d'][i] < sts["2. high"][i+1] and sts["4. close"][i]>sts['100MA'][i]:
                sub_show = sts.iloc[i-100:i+13]            
                sub_test = sts.iloc[i-100:i]
                if self.in_uptrend_internal(sub_test, 60, 0.8, 0)==0: continue                
                date= "{}".format(sts.index[i]).rstrip('00:00:00')
                samples[date]=sub_show
        return samples

    def sampling_plunge_macd(self, recovery=5):
        PLUNGE_DEPTH    = 0.2
        SPAN_FOR_PLUNGE = 20    # days to calculate plunge of price
        OVERSOLD_CUTFF  = 15
        AVOID  = 15             # the latest day span to avoid from sampling
        PRICE  = 10
        self.macd_cross_up()
        self.do_rsi()

        sts0=self.df.copy(deep=True)
        sts=self.df.copy(deep=True)
        # calculate necessary parameters
        sts=sts.iloc[0:(sts.shape[0]-AVOID)]
        #print('row num', sts.shape[0], sts0.shape[0])
        sts['RSImin'] = sts['RSI'].rolling(recovery).min()
        sts['signal'] = sts['signal'].diff()
        sts['signal'] = np.where(sts['signal']>0,1,0)
        sts['max_30days'] = sts['4. close'].rolling(SPAN_FOR_PLUNGE).max()
        sts['loss'] = (sts['max_30days']-sts['4. close'])/sts['max_30days']
        sts['paction']= sts['4. close'] - sts['1. open']
        # filter for rows meeting requirement
        sts['row_num'] = np.arange(len(sts))
        sts2 = sts[ sts['signal'] == 1 ]
        #sts2 = sts2[ sts2['loss']   > 0.15  ]
        sts2 = sts2[ sts2['loss']   > 0.15   ]
        sts2 = sts2[ sts2['RSImin'] < OVERSOLD_CUTFF]
        sts2 = sts2[ sts2['paction']>0              ]

        win=0
        loss=0
        samples={}
        R={}
        #print('row num', sts2.shape[0])
        for i in sts2['row_num']:
            if sts['4. close'][i] < PRICE: continue
            #print ('i', i)
            if sts['2. high'][i] > sts0['2. high'][i+1]: continue
            sub_show = sts0.iloc[i-65:i+15]
            if sub_show.shape[0]<5: continue               
            date= "{}".format(sts.index[i]).rstrip('00:00:00')
            if '18-12-' in date or '19-01-' in date: continue
            samples[date]=sub_show
            
            sts['5daymin'] = sts['3. low'].rolling(5).min()
            entry = sts['2. high'][i]
            sell_stoploss = sts['5daymin'][i]
            r_count = self.fate(sub_show, sts.index[i], entry, sell_stoploss)
            R[date]=r_count
            if r_count>0: win+=1
            if r_count<0: loss+=1
        return samples, R, win, loss

    def fate(self, df, observe_date, entry, sell_stoploss, sticky=False):
        #df = self.get_atr(df)
        #df['5daymin'] = df['3. low'].rolling(5).min()
        observe_date_index = df.index.get_loc(observe_date)
        #observe_date_row = df.loc[observe_date]
        #entry = observe_date_row['2. high']
        
        # define risk
        #risk  = observe_date_row['ATR']
        #risk = observe_date_row['2. high']-observe_date_row['5daymin']
        #sell_stoploss = entry - risk
        risk = entry - sell_stoploss + 0.000001
        
        onboard = df.iloc[observe_date_index+1:]
        # no trade if next day price does not go higher than anticipated entry
        if onboard.iloc[0,:]['2. high'] < entry: 
            return 0
        exit = 0
        last = 0
        if onboard.shape[0] < 2: return 0 
        for date, row in onboard.iterrows():
            if row['3. low'] <= sell_stoploss:
                exit = sell_stoploss
                #print('gone', str(sell_stoploss) )
                break
            else:
                #print('live', str(sell_stoploss) )
                dist = row['4. close']-sell_stoploss
                if sticky:
                    dist_byR = dist//risk
                    if dist_byR > 1:
                        sell_stoploss = sell_stoploss + risk*(dist_byR-1) 
                exit = row['4. close']
        #print ("//\n")
        #print  (exit, entry, risk)
        r = (exit-entry)/risk
        if r > 0 and r <0.001:
            r=0
        return r
                 
    def get_atr(self, df):
        df=df.copy(deep=True)
        df['atr1'] = abs(df['2. high'] - df['3. low'])
        df['atr2'] = abs(df['2. high'] - df['4. close'].shift())
        df['atr3'] = abs(df['3. low' ] - df['4. close'].shift())
        df['ATR'] = df[['atr1', 'atr2', 'atr3']].max(axis=1)
        return df

    def do_rsi(self, n=14):
        df=self.df.copy(deep=True)
        df['delta'] = df['4. close'].diff()
        df['dltup'] = np.where(df['delta']<0,0,df['delta'])
        df['dltdw'] = np.where(df['delta']>0,0,df['delta'])
#        df['dltup_rol']=df['dltup'].ewm(span=n,adjust=False).mean()
#        df['dltdw_rol']=df['dltdw'].ewm(span=n,adjust=False).mean().abs()
        df['dltup_rol']=df['dltup'].rolling(n).mean()
        df['dltdw_rol']=df['dltdw'].rolling(n).mean().abs()

        df['RSI'] = 100 - (100/(1+ df['dltup_rol']/df['dltdw_rol']))
        
        """
        df['delta'] = df['4. close'].diff()
        df['dltup'] = np.where(df['delta']<0,0,df['delta'])
        df['dltdw'] = np.where(df['delta']>0,0,df['delta'])
        df['dltup_count'] = np.where(df['delta']<0,0,1)
        df['dltdw_count'] = np.where(df['delta']>0,0,1)

        df['dltup_rol']=df['dltup'].rolling(n).sum()
        df['dltdw_rol']=df['dltdw'].rolling(n).sum().abs()
        df['dltup_count_rol'] = df['dltup_count'].rolling(n).sum()
        df['dltdw_count_rol'] = df['dltdw_count'].rolling(n).sum()
        df['dltup_rol_mean']= df['dltup_rol']/df['dltup_count_rol']
        df['dltdw_rol_mean']= df['dltdw_rol']/df['dltdw_count_rol']
        
        df['RSI'] = 100-(100/(1+ df['dltup_rol_mean']/df['dltdw_rol_mean']))
        
        print (df['dltup'][-14:])
        print (df['dltdw'][-14:])        
        print (df['dltup_rol'][-1])
        print (df['dltdw_rol'][-1])
        print (df['dltup_count_rol'][-1])
        print (df['dltdw_count_rol'][-1])
        print (df['dltup_rol_mean'][-1])
        print (df['dltdw_rol_mean'][-1])
        print (df['RSI'][-1])
        """
        
        self.df['RSI'] = df['RSI']
        
    def do_rsi_e(self, n=14):
        df=self.df.copy(deep=True)
        df['delta'] = df['4. close'].diff()
        df['dltup'] = np.where(df['delta']<0,0,df['delta'])
        df['dltdw'] = np.where(df['delta']>0,0,df['delta'])
        df['dltup_rol']=df['dltup'].ewm(span=n,adjust=False).mean()
        df['dltdw_rol']=df['dltdw'].ewm(span=n,adjust=False).mean().abs()
        df['RSI'] = 100 - (100/(1+ df['dltup_rol']/df['dltdw_rol']))
        self.df['RSI'] = df['RSI']
        
    def get_rsi(self, n=14):
        self.do_rsi(n)
        return self.df['RSI'][-1]