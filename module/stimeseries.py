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
        df=self.df.copy(deep=True)
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
#        sgnl = STOK - STOD
        sgnl = STOK - 18
        df["signal"] = np.where( sgnl>0, 1, 0)        
        paction = (df['2. high'] - df['4. close']) / ( df['2. high'] - df['3. low']) 
        return STOK, STOD, df["signal"].diff(), paction
        
    def stochastic_cross(self, n, m):
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
        if ratio > cutoff: status = 1
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
        if count == 3: status = 1
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
        stok, stod, signal, paction = self.stochastic_cross_internal(n, m)
        samples={}
        sts=self.df.copy(deep=True)
        bb_dist_low   = (sts["3. low"]  -sts['BB20d'])/(sts['BB20u']-sts['BB20d'])
        bb_dist_close = (sts["4. close"]-sts['BB20d'])/(sts['BB20u']-sts['BB20d'])
        length = len(signal)
        for i in range(100, length-15):
            #print (signal[200])
            #if stod[i]<20 and signal[i]==1 and paction[i]<0.3 and bb_dist<0.05:
            
            # stochastic
            if stod[i] > 20   : continue
            if signal[i]<=0   : continue
            # candle pattern
            if paction[i]>0.3 : continue
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

            if (bb_dist_low[i]<0.02 or bb_dist_low[i-1]<0 or bb_dist_low[i-2]<0)and bb_dist_close[i] <0.33:
                sub = sts.iloc[i-100:i+13]
                if self.in_uptrend_internal(sub, 60, 0.8, 0)==0: continue
                date= "{}".format(stok.index[i]).rstrip('00:00:00')
                samples[date]=sub

        return samples
