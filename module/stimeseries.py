import numpy as np

class stimeseries:
    def __init__(self, df):
        self.df=df.copy(deep=True)
        
    def get_latest_performance(self, period):
        """
            get the percentage price change for the last time period
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
        """
            get the distance between last closing price and specified SMA
            input  : days , time length to calculate simple moving average
            return : float, the difference in percentage
        """
        df=self.df.copy(deep=True)
        df["SMA"] =df["4. close"].rolling(benchmark).mean()
        distance=0
        if df["SMA"][date]>0:
            distance = (df["4. close"][date]-df["SMA"][date])/df["4. close"][date]
        return distance
        
    def get_trading_uprange(self, day):
        """
            get the distance between last closing price and the maximum price in specified time
            input  : days , time length to calculate maximum price
            return : float, the difference in percentage
        """
        df=self.df.copy(deep=True)        
        prices = df["4. close"].tail(day)
        return (prices.max()-prices[-1])/prices.max()
        
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

    def macd_cross_up(self, sspan=12, lspan=26):
        df=self.df.copy(deep=True)
        exp1 = df['4. close'].ewm(span=sspan, adjust=False).mean()
        exp2 = df['4. close'].ewm(span=lspan, adjust=False).mean()
        macd = exp1 - exp2
        exp3 = macd.ewm(span=9, adjust=False).mean()
        df["signal"] = macd - exp3

        #print (df["signal"][-3:])
        df["signal"] = np.where( df["signal"] >0, 1, 0)
        #print (df["signal"][-3:])
        return df["signal"].diff()[-1]
        
            