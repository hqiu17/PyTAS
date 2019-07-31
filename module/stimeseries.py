
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
    

    def get_SMAdistance(self, days):
        """
            get the distance between last closing price and specified SMA
            input  : days , time length to calculate simple moving average
            return : float, the difference in percentage
        """
        df=self.df.copy(deep=True)
        df["SMA"] =df["4. close"].rolling(days).mean()
        distance=0
        if df["SMA"][-1]>0:
            distance = (df["4. close"][-1]-df["SMA"][-1])/df["4. close"][-1]
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

        
            