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
        ratio = (df["4. close"][-1] - df["BB20d"][-1])/ ( df["BB20u"][-1] - df["BB20d"][-1])
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
        
    def stochastic_cross(self, n, m):
        df=self.df.copy(deep=True)
        high = df['2. high']
        low  = df['3. low']
        close= df['4. close']
        STOK = ( (close - low.rolling(n).min())/( high.rolling(n).max()-low.rolling(n).min() ) ) * 100
        STOD = STOK.rolling(m).mean()
        sgnl = STOK - STOD
        df["signal"] = np.where( sgnl>0, 1, 0)        
        paction = (df['2. high'] - df['4. close']) / ( df['2. high'] - df['3. low'])
                    
        return STOK[-1], STOD[-1], df["signal"].diff()[-1], paction[-1]
    
    def two_dragon_internal(self, MAdays1, MAdays2, TRNDdays, dataframe, cutoff=0.8):
        status = 0
        df=dataframe.copy(deep=True)
        # if price data is small, return zero
        if (MAdays2 + 100) > df.shape[0]: return status
        if (TRNDdays + 100) > df.shape[0]: return status
                
        df['ma01'] =df["4. close"].ewm(span=MAdays1,adjust=False).mean()
        df['ma02'] =df["4. close"].ewm(span=MAdays2,adjust=False).mean()
        sgnl = df["ma01"] - df["ma02"]
        df["signal"] =np.where( sgnl>0, 1, 0)
        
        ratio = df.tail(TRNDdays)['signal'].sum()/TRNDdays
        if ratio > cutoff:
            status = 1

        return status
        
    def two_dragon(self, MAdays1, MAdays2, TRNDdays, cutoff=0.8):
        status = two_dragon_internal(self, MAdays1, MAdays2, TRNDdays, self.df, cutoff=0.8)
        return status
        
    def in_uptrend(self, TRNDdays, cutoff=0.8, blind=0):
        df = pd.DataFrame()
        if blind > 0 and blind < self.df.shape[0]:
            last_index = self.df.shape[0] - blind
            df = self.df[0:last_index]
        else:
            df = self.df.copy(deep=True)
            
        status = 0
        count  = 0
        count += self.two_dragon_internal( 20, 50,TRNDdays, df, cutoff)
        count += self.two_dragon_internal( 50,100,TRNDdays, df, cutoff)
        count += self.two_dragon_internal(100,150,TRNDdays, df, cutoff)
        
        if count == 3: status = 1
        return status


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
