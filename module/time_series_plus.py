import re
import numpy as np
import pandas as pd
from module.utility import date_to_index
from scipy.stats import chisquare

class TimeSeriesPlus:
    def __init__(self, df):
        self.df = df.copy(deep=True)
        self.ema_length = [2, 3, 5, 10, 20, 50, 100, 150, 200]
        self.sma_multiple()

    def sma_multiple(self):
        # ma_days = [3, 20, 50, 100, 150, 200]
        df = self.df
        df = df.sort_index(axis=0)
        if '4. close' in df.columns:
            # for days in ma_days:
            for days in self.ema_length:
                # df[str(days)+'MA'] = df["4. close"].rolling(days).mean()
                ema = str(days) + 'MA'
                df[ema] = df["4. close"].ewm(span=days, adjust=False).mean()
                emama = ema + 'SMA'
                df[emama] = df[ema].rolling(10).mean()

            # simple moving average for bollinger band
            df["20SMA"] = df["4. close"].rolling(20).mean()
            df['STD20'] = df["4. close"].rolling(20).std()
            df['BB20u'] = df['20SMA'] + df['STD20'] * 2
            df['BB20d'] = df['20SMA'] - df['STD20'] * 2
            df['BB20d_SMA10'] = df['BB20d'].rolling(10).mean()

            df['v5_SMA'] =  df["5. volume"].rolling(5).mean()
            df['v10_SMA'] = df["5. volume"].rolling(10).mean()
            df['v15_SMA'] = df["5. volume"].rolling(15).mean()
            df['v20_SMA'] = df["5. volume"].rolling(20).mean()
        self.df = df
        return self

    def find_pivot_simple(self, length):
        """Infer pivots simply using closing price data
        """
        df = self.df.copy(deep=True)

        df['max'] = df['4. close'].rolling(length).max()
        df['min'] = df['4. close'].rolling(length).min()
        df['maxrev'] = df['4. close'][::-1].rolling(length).max()[::-1]
        df['pivot_high'] = np.where((df['4. close'] == df['max']) & (df['4. close'] == df['maxrev']), True, False)
        df['minrev'] = df['4. close'][::-1].rolling(length).min()[::-1]
        df['pivot_low'] = np.where((df['4. close'] == df['min']) & (df['4. close'] == df['minrev']), True, False)
        self.df['pivot_simple'] = np.where((df['pivot_high'] | df['pivot_low']), df['4. close'], 0)
        # return df['pivot']
        # self.df = df.drop(['max', 'maxrev', 'min', 'minrev', 'pivot_low', 'pivot_high'], axis=1)
        return self

    def find_pivot_atr(self, length):
        """Infer pivots simply using closing price and ATR data
        """
        self.get_atr(length, forward=True)
        df = self.df.copy(deep=True)

        df['max_atr'] = (df['4. close'] + df['ATR']).rolling(length).min()
        df['max_atr_f'] = (df['4. close'] + df['ATRforward'])[::-1].rolling(length).min()[::-1]
        df['max_atr_final'] = np.where( df['max_atr'] > df['max_atr_f'], df['max_atr'], df['max_atr_f'] )
        df['min_atr'] = (df['4. close'] - df['ATR']).rolling(length).max()
        df['min_atr_f'] = (df['4. close'] - df['ATRforward'])[::-1].rolling(length).max()[::-1]
        df['min_atr_final'] = np.where( df['min_atr'] < df['min_atr_f'], df['min_atr'], df['min_atr_f'] )

        df['max'] = df['4. close'].rolling(length).max()
        df['max_f'] = df['4. close'][::-1].rolling(length).max()[::-1]
        df['max_final'] = np.where(df['max'] > df['max_f'], df['max'], df['max_f'])
        df['min'] = df['4. close'].rolling(length).min()
        df['min_f'] = df['4. close'][::-1].rolling(length).min()[::-1]
        df['min_final'] = np.where(df['min'] < df['min_f'], df['min'], df['min_f'])

        df['pivot_high'] = np.where( (df['4. close'] == df['max_final']) & (df['4. close'] >= df['max_atr_final']), True, False)
        df['pivot_low'] = np.where( (df['4. close'] == df['min_final']) & (df['4. close'] <= df['min_atr_final']), True, False)
        self.df['pivot_atr'] = np.where((df['pivot_high'] | df['pivot_low']), df['4. close'], 0)
        return self

    def find_pivot(self, length):
        """Combination of simple pivots and ATR-based pivots
        """
        self.find_pivot_simple(length*2)
        self.find_pivot_atr(length)
        self.df['pivot'] = np.where(self.df['pivot_simple'] > self.df['pivot_atr'], self.df['pivot_simple'], self.df['pivot_atr'] )
        return self

    def horizon_slice(self, days):
        """Number of pivots in the same zone defined by last close

        Args:
            days (int): recent period in which pivots are considered

        Return:
            (int): number of pivots in the same zone defined by last close
        """

        df = self.df.copy(deep=True)
        if df.shape[0] < 100:
            return 0
        df = df.tail(days)

        # define horizontal zone

        # # use ATR
        # last = df['4. close'][-1]
        # radius1 = df['ATR'][-1]/2   # by half of ATR
        # radius2 = last/100          # by 1% last close
        # up_lim = max(last + radius1, last + radius2)
        # lw_lim = min(last - radius1, last - radius2)

        # use last day's trading range
        # up_lim = df['2. high'][-1]
        # lw_lim = df['3. low'][-1]
        up_lim = df['1. open'][-1]
        lw_lim = df['4. close'][-1]

        self.df['last_trading_range'] = "{},{}".format(lw_lim, up_lim)
        # print (df['4. close'][-1], df['ATR'][-1], up_lim, lw_lim)
        df['pivot_caught'] = np.where( (lw_lim < df['pivot']) & (df['pivot'] < up_lim), 1, 0)
        return df['pivot_caught'].sum()

    def hit_horizontal_support(self, days, length, num, touch_down=True):
        """Close touch down and slice by EMA

        Args:
            days (int): recent period in which pivots are considered
            length (int): length of period (in days) to calculate pivots and to test if 3EMA is above last close
            num (int): minimal number of pivots
            touch_down (boolean): touch down (True) or touch up (False)
        Returns:
              boolean
        """
        # test pivot number
        self.find_pivot(length)
        if self.horizon_slice(days) < num:
            return False

        # test if prices were above support or below support before slicing
        horizontal_support = self.df['4. close'][-1]
        if touch_down:
            stay_above = self.two_dragon_internal(3, horizontal_support, length, self.df, 0.9)
        else:
            stay_above = self.two_dragon_internal(horizontal_support, 3, length, self.df, 0.9)

        if stay_above == 1:
            return True
        else:
            return False

    def get_latest_performance(self, period, benchmark=0):
        """ 
        Get the price change for the last time period (i.e., the lastest 5 days 
        including today)
        
        Argument:
            period  (str): number of days (int) to define this period
            benchmark (float): performance benchmark
        Return : 
            a float representing price change over the period
        """
        performance = 0
        df_latest_period = self.df.tail(period)
        begin = df_latest_period["4. close"][0]
        last = df_latest_period["4. close"][-1]

        if begin > 0:
            performance = (last - begin) / begin

        performance = performance - benchmark

        return performance

    def get_SMAdistance(self, benchmark, date=-1):
        """ get the distance between last closing price and specified SMA
            input  : days , time length to calculate simple moving average
            return : float, the difference in percentage
        """
        df = self.df.copy(deep=True)
        df["SMA"] = df["4. close"].rolling(benchmark).mean()
        distance = 0
        if df["SMA"][date] > 0:
            distance = (df["4. close"][date] - df["SMA"][date]) / df["4. close"][date]
        return distance

    def get_BBdistance(self, days=1):
        df = self.df.copy(deep=True)
        if days > 1:
            df["lowrol"] = df["3. low"].rolling(days).min()
            ratio = (df["lowrol"][-1] - df["BB20d"][-1]) / (df["BB20u"][-1] - df["BB20d"][-1])
        else:
            ratio = (df["3. low"][-1] - df["BB20d"][-1]) / (df["BB20u"][-1] - df["BB20d"][-1])
        return ratio


    # def in_uptrend(self, days, interval=3, cutoff=0.75, blind=0):
    #     status=False
    #     df = self.df
    #
    #     # record length is less than days required to figure out uptrend
    #     # return false since no judgement could be made
    #     if len(df)-blind < abs(days):
    #         return status
    #
    #     # test uptrend signature for one day-point
    #     def ma_inorder(aday):
    #         i = 0
    #         if aday["50MA"]>=aday["150MA"] and aday["150MA"]>=aday["200MA"]:
    #             if days>0:
    #                 i=1
    #         elif days<0 and aday["4. close"] >= aday["50MA"]:
    #                 i=1
    #         return i
    #
    #     count_all=0
    #     count_pass=0
    #     # set the beginning date and ending date of the test period
    #     oldest_date = 0 - abs(days) - blind
    #     latest_date = 0 - 1 - blind
    #     record_length = 0 - len(df)
    #     # if record length is long enough, move the beginning date earlier
    #     if record_length > oldest_date:
    #         oldest_date = record_length
    #
    #     # loop through the test period and make test for each step
    #     for index in range(latest_date, oldest_date, 0-interval):
    #         aday = df.iloc[index,:]
    #         count_pass += ma_inorder(aday)
    #         count_all +=1
    #         #print (sticker, str(index), str(ma_inorder(day)), sep="\t")
    #
    #     if (count_pass/count_all) > cutoff:
    #         status=True
    #     return status

    def macd_cross_up(self, sspan=12, lspan=26, persist=1):
        """MACD crosses above signal line

        Args:
            sspan (int): length of short span for MACD calculation
            lspan (int): length of long span for MACD calculation
            presist (int): days allow after crossing above
        Returns:
            status (boolean):
        """

        df = self.df
        exp1 = df['4. close'].ewm(span=sspan, adjust=False).mean()
        exp2 = df['4. close'].ewm(span=lspan, adjust=False).mean()
        macd = exp1 - exp2
        exp3 = macd.ewm(span=9, adjust=False).mean()
        df["signal"] = macd - exp3
        df["signal"] = np.where(df["signal"] > 0, 1, 0)

        status = 0
        tail = df["signal"][-8:]    # examine the last 8 days
        switch = tail.diff().sum()
        landing = tail.sum()
        if (tail[0] == 0 and                # at the first day macd is below signal line
                tail[-1] == 1 and           # at the last day macd is above signal line
                switch == 1 and             # only one corssing happened
                landing <= persist and      # days elapsed after crossing is less than cutoff (persist)
                exp3[-1] < 0):              # signal line is below zero
            status = 1
        return status

    def ema_cross_up(self, fast, slow, under=2):
        df = self.df.copy(deep=True)
        sma_fast = df['4. close'].ewm(span=fast, adjust=False).mean()
        sma_slow = df['4. close'].ewm(span=slow, adjust=False).mean()
        df["signal"] = sma_fast - sma_slow
        df["signal"] = np.where(df["signal"] > 0, 1, 0)

        if under < 2:
            under = 2

        status = 0
        tail = df["signal"][(0 - under):]    # examine the last 8 days
        switch = tail.diff().sum()
        landing = tail.sum()
        if (tail[0] == 0 and                # at the first day macd is below signal line
                tail[-1] == 1 and           # at the last day macd is above signal line
                switch == 1 and             # only one crossing happened
                landing <= 1):              # days elapsed after crossing is 0
            status = 1
        return status

    def stochastic_cross_internal(self, n, m):
        df = self.df.copy(deep=True)
        high = df['2. high']
        low = df['3. low']
        close = df['4. close']
        STOK = ((close - low.rolling(n).min()) / (high.rolling(n).max() - low.rolling(n).min())) * 100
        STOD = STOK.rolling(m).mean()
        sgnl = STOK - STOD
        # sgnl = STOK - 18
        df["signal"] = np.where(sgnl > 0, 1, 0)
        paction = (df['2. high'] - df['4. close']) / (df['2. high'] - df['3. low'])
        return STOK, STOD, df["signal"].diff(), paction

    def stochastic_cross(self, n, m):
        """ return tuple of 4 values: k, d, k>d?(1/0), candlestick head size
        """
        stok, stod, signal, paction = self.stochastic_cross_internal(n, m)
        return stok[-1], stod[-1], signal[-1], paction[-1]

    def two_dragon_internal(self, MAdays1, MAdays2, TRNDdays, dataframe, cutoff=0.8, vol=False):
        """ Test parallel ema in defined period
        Args:
            MAdays1 (int): length for 1st ema
            MAdays2 (int): length for 2nd ema
            TRNDdays (int): period to test parallel
            dataframe (pandas dataframe): historical data
            cutoff (float): frequency of datapoint supporting parallel
        Returns:
            status (-1, 0 , 1): test result
        """

        status = 0  # =0: undetermined status; =1: 1st ema above 2nd ema; =-1: 1st ema below 2nd ema

        # sma_fast = df['4. close'].ewm(span=fast, adjust=False).mean()
        # sma_slow = df['4. close'].ewm(span=slow, adjust=False).mean()

        df = dataframe.copy(deep=True)

        if vol:
            ma1_key = "v" + str(MAdays1) + "_SMA"
            ma2_key = "v" + str(MAdays2) + "_SMA"
        else:
            ma1_key = str(MAdays1) + "MA"
            ma2_key = str(MAdays2) + "MA"

        # if dataframe length is not sufficient to calculate ema, return 0

        # if (TRNDdays + MAdays1) > df.shape[0] or (TRNDdays + MAdays2) > df.shape[0]:
        #     # print(f"dataframe length {df.shape[0]} is not sufficient to calculate and do test using ema")
        #     return status

        if ma1_key in df.columns and ma2_key in df.columns:
            df['ma01'] = df[ma1_key]
            df['ma02'] = df[ma2_key]
        elif ma1_key not in df.columns:
            df['ma01'] = MAdays1
            df['ma02'] = df[ma2_key]
        elif ma2_key not in df.columns:
            df['ma01'] = df[ma1_key]
            df['ma02'] = MAdays2
        else:
            return status

        sgnl = df["ma01"] - df["ma02"]
        df["signal"] = np.where(sgnl > 0, 1, 0)
        ratio = df.tail(TRNDdays)['signal'].sum() / TRNDdays

        if ratio >= cutoff:
            status = 1
        elif ratio < (1 - cutoff):
            status = -1
        return status

    def two_dragon(self, *args, vol=False):
        """ Test 2 parallel EMAs in defined period
        """
        cutoff = 0.8
        if len(args) == 4: cutoff = float(args[3])
        status = self.two_dragon_internal(args[0], args[1], args[2], self.df, cutoff, vol)
        return status

    def hit_ema_support(self, ema, days):
        """Last close touch down and slice EMA

        Args:
            ema (int): length in days to define ema. When eam equals 0, all key EMAs will be tested
            days (int): period to assess if two EMAs do not cross each other

        Returns
            boolean: test negative or positive
        """
        status = False

        if ema != 0:
            if ema not in self.ema_length:
                return status
            elif not self.ema_slice(ema):
                return status
            else:
                stay_above = self.two_dragon_internal(3, ema, days, self.df, 0.95)
                if stay_above == 1:
                    return True
                else:
                    return False
        else:
            for length in self.ema_length:
                if length < 100:
                    continue
                if not self.ema_slice(length):
                    continue
                stay_above = self.two_dragon_internal(3, length, days, self.df, 0.95)
                if stay_above == 1:
                    return True
        return status

    def ema_3layers(self, query=2, short=10, long=100, days=0, cut=0.8):
        """Query EMA sandwiched between short and long EMAs for recent period

        Args:
            query (int): length in days to define query EMA.
            short (int): length in days to define short EMA.
            long (int): length in days to define long EMA.
            days (int): period to assess if middle EMA is sandwich between short/long EMAs.
                if not provided, assess only the last for EMA formation
            ratio (int): minimal percentage of days meeting the EMA formation
        Returns
            boolean: test negative or positive
        """
        status = False
        df = self.df.copy(deep=True)
        ema_q = f"{query}MA"
        ema_s = f"{short}MA"
        ema_l = f"{long}MA"

        if ema_q not in df.columns:
            df[ema_q] = df['4. close'].ewm(span=query, adjust=False).mean()
        if ema_s not in df.columns:
            df[ema_s] = df['4. close'].ewm(span=short, adjust=False).mean()
        if ema_l not in df.columns:
            df[ema_l] = df['4. close'].ewm(span=long, adjust=False).mean()

        # if no recent period (variable 'days') is defined, test the last day
        if not days:
            if df[ema_l][-1] < df[ema_q][-1] < df[ema_s][-1]:
                status = True
            return status

        df['query-short'] = df[ema_q] - df[ema_s]
        df['query-short_pass'] = np.where(df[ema_q] <= df[ema_s], 1, 0)
        df['query-long_pass'] = np.where(df[ema_l] <= df[ema_q], 1, 0)
        df['short-query-long'] = df['query-short_pass'] + df['query-long_pass']
        df['pass'] = np.where(df['short-query-long'] == 2, 1, 0)
        ratio = df.tail(days)['pass'].sum() / days
        if ratio >= cut:
            status = True

        return status

    def in_uptrend_internal(self, dataframe, TRNDdays, cutoff, blind):
        """ 
            return status (1)  for uptrend
            return status (-1) for downtrend
            return status (0)  for intermediate trend
        """
        status = 0
        df = pd.DataFrame()
        if blind > 0:
            if blind < dataframe.shape[0]:
                last_index = dataframe.shape[0] - blind
                df = dataframe[0:last_index]
            else:
                return status

        if df.shape[0] == 0:
            df = dataframe.copy(deep=True)

        # if df['20MA'][-1] < df['20MASMA'][-1]:
        #     return status
        if '150MA' not in df.columns:
            return status
        elif df['200MA'][-1] < df['200MASMA'][-1]:
            return status
        # if df['100MA'][-1] < df['100MASMA'][-1]:
        #     return status
        # if df['50MA'][-1] < df['50MASMA'][-1]:
        #     return status

        count = 0
        count += self.two_dragon_internal(20, 50, TRNDdays, df, cutoff)
        count += self.two_dragon_internal(50,  100, TRNDdays, df, cutoff)
        count += self.two_dragon_internal(100, 200, TRNDdays, df, cutoff)
        # count += self.two_dragon_internal(150, 200, TRNDdays, df, cutoff)
        if count == 3:
            status = 1
        elif count == -3:
            status = -1
        return status

    def in_uptrend(self, TRNDdays, cutoff=0.8, blind=0, launch=False):
        if launch:
            status = 0
            df = self.df.copy(deep=True).tail(50)
            df['diff1_20-50'] = df['20MA'] - df['50MA']
            df['diff1'] = np.where(df['diff1_20-50']>0, 1 , 0)
            df['diff2_50-100'] = df['50MA'] - df['100MA']
            df['diff2'] = np.where(df['diff2_50-100']>0, 1 , 0)
            df['diff3_100-150'] = df['100MA'] - df['150MA']
            df['diff3'] = np.where(df['diff3_100-150']>0, 1 , 0)
            # df['sum'] = df['diff1'] + df['diff2'] + df['diff3']
            # df['pass'] = np.where(df['sum'] == 3, 1, 0)

            df['sum'] = df['diff1'] + df['diff2']
            df['pass'] = np.where(df['sum'] == 2, 1, 0)

            # the first or second days since uptrend signal
            if df['pass'][-1] == 1 and df['pass'][-5:-2].sum() == 0:
                status = 1

            return status
        else:
            return self.in_uptrend_internal(self.df, int(TRNDdays), float(cutoff), int(blind))

    def in_uptrendx(self, *args):
        TRNDdays = int(args[0])
        cutoff = 0.8
        blind = 0
        if len(args) == 2: cutoff = float(args[1])
        if len(args) == 3: blind = int(args[2])
        return self.in_uptrend_internal(self.df, TRNDdays, cutoff, blind)

    def to_weekly(self):
        logic = {'1. open': 'first',
                 '2. high': 'max',
                 '3. low': 'min',
                 '4. close': 'last',
                 '5. volume': 'sum'}
        # offset = pd.offsets.timedelta(days=-6)
        offset = None
        self.df = self.df.resample('W', loffset=offset).apply(logic)
        self.sma_multiple()

    def to_monthly(self):
        logic = {'1. open': 'first',
                 '2. high': 'max',
                 '3. low': 'min',
                 '4. close': 'last',
                 '5. volume': 'sum'}
        # offset = pd.offsets.timedelta(days=-6)
        offset = None
        self.df = self.df.resample('M', loffset=offset).apply(logic)

    def get_weekly(self):
        self.to_weekly()
        return self.df.copy(deep=True)

    def get_monthly(self):
        self.to_monthly()
        return self.df.copy(deep=True)

    def get_volume(self):
        self.df['vol'] = self.df['5. volume']
        return self
    
    # def sampling_stks_bb(self, n, m):
    #     prediction = 15
    #     stok, stod, signal, paction = self.stochastic_cross_internal(n, m)
    #     sts = self.df.copy(deep=True)
    #     sts['BB20dmax'] = sts["BB20d"].rolling(15).max()
    #     bb_dist_low = (sts["3. low"] - sts['BB20d']) / (sts['BB20u'] - sts['BB20d'])
    #     bb_dist_close = (sts["4. close"] - sts['BB20d']) / (sts['BB20u'] - sts['BB20d'])
    #     length = len(signal)
    #
    #     win = 0
    #     loss = 0
    #     samples = {}
    #     samples_test = {}
    #     R = {}
    #
    #     sampling_window = 220
    #     index_start = length - prediction - sampling_window
    #     if index_start < 0: index_start = 0
    #     for i in range(index_start, length - prediction):
    #         # print (signal[200])
    #         # if stod[i]<20 and signal[i]==1 and paction[i]<0.3 and bb_dist<0.05:
    #
    #         ############## fixed #############
    #         if sts['5. volume'][i] < 100000: continue
    #         # stochastic
    #         if stod[i] > 30: continue
    #         if signal[i] <= 0: continue
    #         # no transaction due to gap up or down price on entry attempting day
    #         if (sts['2. high'][i] > sts['2. high'][i + 1]) or (sts['2. high'][i] < sts['3. low'][i + 1]): continue
    #         # candle pattern
    #         if paction[i] > 0.3: continue
    #         if sts['1. open'][i] > sts['4. close'][i] and paction[i] > 0.15: continue
    #         # close-BB distance
    #         """ bb_dist_low and bb_dist_close adjusted by Ely(20191106) and TPH(20191111)
    #         """
    #         if (bb_dist_low[i] < 0.05 or bb_dist_low[i - 1] < 0 or bb_dist_low[i - 2] < 0) and bb_dist_close[i] < 0.3:
    #             pass
    #         else:
    #             continue
    #             # remove straight down
    #         if sts['BB20d'][i - 14] > sts['BB20d'][i - 10] > sts['BB20d'][i - 5] > sts['BB20d'][i]:
    #             continue
    #
    #         ############## fixed #############
    #
    #         """
    #         # keep straight up
    #         if (
    #             #sts['BB20d'][i] = sts['BB20dmax'][i]
    #             (sts['BB20d'][i-12] < sts['BB20d'][i] and sts['BB20d'][i-6] < sts['BB20d'][i])
    #         ): pass
    #         else: continue
    #         """
    #         if sts['long'][i] <= 0: continue
    #
    #         # print ('6', sts.index[i])
    #         # if not ( sts['50MA'][i] < sts["4. close"][i] and sts["4. close"][i] < sts['20MA'][i]): continue
    #         # if not ( sts['50MA'][i] < sts['20MA'][i]): continue
    #         # if sts['4. close'][i]<sts['20MA'][i]: continue
    #         # print (sts.index[i])
    #
    #         # add days to be predicted
    #         sub = sts.iloc[0:i + prediction - 1]
    #         # add history and observe day
    #         sub_test = sts.iloc[0:i + 1]
    #
    #         # remove downtrend
    #         if self.in_uptrend_internal(sub_test, 90, 0.90, 0) == -1: continue
    #         if self.in_uptrend_internal(sub_test, 60, 0.90, 0) == -1: continue
    #         if self.in_uptrend_internal(sub_test, 20, 0.90, 0) == -1: continue
    #         if self.in_uptrend_internal(sub_test, 120, 0.90, 0) == -1: continue
    #
    #         date = "{}".format(stok.index[i]).rstrip('00:00:00')
    #         date = date.strip()
    #         # if '18-10-' in date or '18-11-' in date or '18-12-' in date or '19-01-' in date: continue
    #
    #         # load test to be plotted
    #         samples[date] = sub.tail(80)
    #         # load show-data to be plotted
    #         samples_test[date] = sub_test.tail(80)
    #
    #         sts['5daymin'] = sts['3. low'].rolling(3).min()
    #         entry = sts['2. high'][i]
    #         sell_stoploss = sts['5daymin'][i]
    #         r_count = self.fate(sub, sts.index[i], entry, sell_stoploss, True)
    #         R[date] = r_count
    #         if r_count > 0: win += 1
    #         if r_count < 0: loss += 1
    #     return samples_test, samples, R, win, loss

    # def sampling_below_bb(self):
    #     samples = {}
    #     sts = self.df.copy(deep=True)
    #     bb_dist_close = (sts["4. close"] - sts['BB20d']) / (sts['BB20u'] - sts['BB20d'])
    #     length = sts.shape[0]
    #     for i in range(100, length - 15):
    #         if bb_dist_close[i] < -0.1 and sts['BB20d'][i] < sts["2. high"][i + 1] and sts["4. close"][i] > \
    #                 sts['100MA'][i]:
    #             sub_show = sts.iloc[i - 100:i + 13]
    #             sub_test = sts.iloc[i - 100:i]
    #             if self.in_uptrend_internal(sub_test, 60, 0.8, 0) == 0: continue
    #             date = "{}".format(sts.index[i]).rstrip('00:00:00')
    #             samples[date] = sub_show
    #     return samples

    # def sampling_plunge_macd(self, recovery=5):
    #     PLUNGE_DEPTH = 0.15
    #     SPAN_FOR_PLUNGE = 20  # days to calculate plunge of price
    #     RSI_CUTFF = 15
    #     AVOID = 20  # the latest day span to avoid from sampling
    #     PRICE = 10
    #     prediction = AVOID
    #     self.macd_cross_up()
    #     self.do_rsi_wilder()
    #
    #     sts0 = self.df.copy(deep=True)
    #     sts = self.df.copy(deep=True)
    #
    #     # calculate necessary parameters
    #     sts = sts.iloc[0:(sts.shape[0] - AVOID)]
    #     # print('row num', sts.shape[0], sts0.shape[0])
    #     sts['RSImin'] = sts['RSI'].rolling(recovery).min()
    #     sts['signal'] = sts['signal'].diff()
    #     sts['signal'] = np.where(sts['signal'] > 0, 1, 0)
    #     sts['max_30days'] = sts['4. close'].rolling(SPAN_FOR_PLUNGE).max()
    #     sts['loss'] = (sts['max_30days'] - sts['4. close']) / sts['max_30days']
    #     sts['paction'] = sts['4. close'] - sts['1. open']
    #
    #     # filter for rows meeting requirement
    #     sts['row_num'] = np.arange(len(sts))
    #     length = sts.shape[0]
    #     sampling_window = 220
    #     index_start = length - prediction - sampling_window
    #     if index_start < 0: index_start = 1
    #     sts2 = sts.iloc[index_start: length - prediction]
    #
    #     """
    #     print (sts.index[index_start], sts.index[length-prediction])
    #     print (sts2.index[0], sts2.index[-1])
    #     print (sts['row_num'][index_start], index_start, sts['row_num'][length-prediction],length-prediction)
    #     print (sts2['row_num'][0], sts2['row_num'][-1])
    #     """
    #
    #     # MACD data line cross up signal line
    #     sts2 = sts2[sts2['signal'] == 1]
    #
    #     sts2 = sts2[sts2['5. volume'] > 100000]
    #     sts2 = sts2[sts2['long'] > 0]
    #     # Minimal price drop to be considered plunge
    #     sts2 = sts2[sts2['loss'] > PLUNGE_DEPTH]
    #     # Maximal RSI to be considered plunge
    #     sts2 = sts2[sts2['RSImin'] < RSI_CUTFF]
    #     # price moves up since openning
    #     sts2 = sts2[sts2['paction'] > 0]
    #
    #     win = 0
    #     loss = 0
    #     samples = {}
    #     samples_test = {}
    #     R = {}
    #     # print('row num', sts2.shape[0])
    #
    #     # print (index_start, length-prediction)
    #     # for i in range(index_start, length-prediction):
    #     back = 150
    #     for i in sts2['row_num']:
    #         # remove names with small price
    #         if sts0['4. close'][i] < PRICE: continue
    #         # trading day price doesn't hit buy stop loss
    #         if sts0['2. high'][i] > sts0['2. high'][i + 1]: continue
    #         # slice 65 days before and 20 days after the timepoint
    #         start = i - back
    #         if start < 0: start = 0
    #         sub_show = sts0.iloc[start:i + AVOID]
    #         sub_test = sts0.iloc[start:i + 1]
    #         # remove poor dataset
    #         if sub_show.shape[0] < 5: continue
    #         # remove late 2018 and early 2019 period
    #
    #         if self.in_uptrend_internal(sub_test, len(sub_test), 0.9, 0) == -1:
    #             print('heavy downtrend')
    #             continue
    #
    #         date = "{}".format(sts.index[i]).rstrip('00:00:00')
    #         # if '18-10-' in date or '18-11-' in date or '18-12-' in date or '19-01-' in date: continue
    #
    #         samples[date] = sub_show
    #         samples_test[date] = sub_test
    #
    #         sts['5daymin'] = sts['3. low'].rolling(5).min()
    #         entry = sts['2. high'][i]
    #         sell_stoploss = sts['5daymin'][i]
    #         r_count = self.fate(sub_show, sts.index[i], entry, sell_stoploss)
    #         R[date] = r_count
    #         if r_count > 0: win += 1
    #         if r_count < 0: loss += 1
    #     return samples_test, samples, R, win, loss

#     def get_fate(self, df, observe_date, test_period=40, entry='next', stoploss=3, strategy='2R'):
    def get_fate(self, observe_date, test_period=40, entry='next', stoploss=3, strategy='2R'):
        """Get outcome of a trade
        
        Args:
            df (dataframe): time series data to go through (holding period)
            observe_dat (str): date when buy signal is emitted
            entry (str): entry price defined by today (this) or next day (next)
            stoploss (int): lookback period (in days) to define stop loss price (the lowest low)
            strategy (str): 1) 2R, fixed profit taking at 2R;
                            2) sticky, raise stop loss as price goes up until it is hit by price
                            3) investment, no stop loss
        
        Returns:
            a tuple contains:
                1) R (float): number of R made in this trade
                2) exit price (float)
                3) exit_date (str): exit date
        """
        
        # print('in get_fate')
        # print(observe_date, test_period, entry, stoploss, strategy)
        
        R = 0
        exit = ''
        exit_date = ''
        entry_price = ''
        action_lines = []
        stoploss_price = ''
        risk = 0
        df = self.df

        # buy for sure the next day
        if strategy == "investment":
            entry = "this"
        
        # invalid trading date
        if observe_date not in df.index:
            print ("observe_date is invalid; {}".format(observe_date))
            # print ('-->', R, exit, exit_date)
            return R, exit, exit_date

        # get data for holding period for loop through
        observe_date_index = df.index.get_loc(observe_date)
        onboard = df.iloc[observe_date_index + 1:]
        onboard = onboard.head(test_period)      # fixed holding period

        # get stop loss price
        observed = df.iloc[:(observe_date_index + 1)]
        stoploss_price = observed.tail(stoploss)['3. low'].min()
        
        # get entry price
        if entry == 'next':
            entry_price = df['2. high'][observe_date]
            trade_miss = False
            if onboard.iloc[0]['2. high'] < entry_price:    # next price doesnt go up
                trade_miss = True
            elif onboard.iloc[0]['3. low'] > entry_price:    # next price jump over
                trade_miss = True
            if trade_miss:
                # print('-->', R, exit, exit_date)
                return 'missing', exit, exit_date
        elif entry == 'this':
            entry_price = df['4. close'][observe_date]
        risk = entry_price - stoploss_price + 0.000001

        # record key prices 
        action_lines.append(stoploss_price)
        action_lines.append(entry_price)

        # set up strategy
        profit_take = 2000000
        sticky = False
        if strategy.endswith('R'):
            fixed_R = float(strategy.rstrip('R'))
            profit_take = entry_price + risk * fixed_R

            for i in range(1,10):
                key_price = entry_price + risk * i
                if key_price <= profit_take:
                    action_lines.append(key_price)
                else:
                    break
        elif strategy == 'sticky':
            sticky = True
        
        # no trade if next day price does not go higher than anticipated entry
        # if onboard.iloc[0,:]['2. high'] < entry: return 0
        # holding period less than 2 (poor data) -> skip
        if onboard.shape[0] < 2:
            print ('2->', onboard.shape[0],  R, exit, exit_date)
            return R, exit, exit_date

        exit = 0
        exit_date = ''
        if strategy != "investment":
            count_2MA_below_10MA = 0
            for date, row in onboard.iterrows():
                if row['2MA'] <= row['10MA']:
                    count_2MA_below_10MA += 1
                else:
                    count_2MA_below_10MA = 0                

                # price goes below stop loss and exit trade
                if row['3. low'] <= stoploss_price:
                    if row['2. high'] < stoploss_price:
                        exit = row['4. close']
                    else:
                        exit = stoploss_price
                    exit_date = date
                    break
                # exit when 2EMA stay below 10EMA for 2 successive days                    
#                 elif count_2MA_below_10MA>=2:
#                     exit = row['4. close']
#                     exit_date = date
#                     break
                # take profit or move up stop loss
                else:
                    dist = row['4. close'] - stoploss_price
                    if sticky:
                        dist_byR = dist // risk
                        if dist_byR > 1:
                            stoploss_price = stoploss_price + risk * (dist_byR - 1)
                            action_lines.append(stoploss_price)
                    elif row['2. high'] > profit_take:
                        exit = profit_take
                        exit_date = date
                        break
        
        # No exit transaction is made in test period. exit at last closing price
        if exit == 0:
            exit = onboard['4. close'][-1]
            exit_date = onboard.index[-1]
        
        exit_date = str(exit_date).split(' ')[0]
        
        # print(exit, entry_price)
        
        R = (exit - entry_price)/risk
        if strategy == "investment":
            R = (exit - entry_price)*100/entry_price
        R = round(R, 3)
        if abs(R) < 0.001: 
            R = 0

        # print  ('entry_price', 'exit', 'stoploss_price', 'risk', 'R', 'exit_date')
        # print  (entry_price, exit, stoploss_price, risk, R, exit_date)
        # print ("//")
        # action_lines = action_lines.insert(0, exit)
        action_lines.append(exit)
        action_lines_string = '#'.join([str(a) for a in action_lines])
        return R, action_lines_string, exit_date

    def get_atr(self, length, forward=False):
        df = self.df.copy(deep=True)
        high = df['2. high']
        low = df['3. low']
        close = df['4. close']

        def do_atr(df, high, low, close):
            df = df.copy(deep=True)
            df['atr1'] = abs(high - low)
            df['atr2'] = abs(high - close.shift())
            df['atr3'] = abs(low - close.shift())
            df['atrmax'] = df[['atr1', 'atr2', 'atr3']].max(axis=1)
            return df['atrmax'].rolling(length).mean()

        self.df['ATR'] = do_atr(df, high, low, close)

        if forward:
            high = high[::-1]
            low = low[::-1]
            close = close[::-1]
            self.df['ATRforward'] = do_atr(df, high, low, close)[::-1]
        return self

    def do_rsi(self, n=14):
        df = self.df.copy(deep=True)
        df['delta'] = df['4. close'].diff()
        df['dltup'] = np.where(df['delta'] < 0, 0, df['delta'])
        df['dltdw'] = np.where(df['delta'] > 0, 0, df['delta'])
        #        df['dltup_rol']=df['dltup'].ewm(span=n,adjust=False).mean()
        #        df['dltdw_rol']=df['dltdw'].ewm(span=n,adjust=False).mean().abs()
        df['dltup_rol'] = df['dltup'].rolling(n).mean()
        df['dltdw_rol'] = df['dltdw'].rolling(n).mean().abs()

        df['RSI'] = 100 - (100 / (1 + df['dltup_rol'] / df['dltdw_rol']))

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

    def do_rsi_ema(self, n=14):
        df = self.df.copy(deep=True)
        # print (df.shape)
        df['delta'] = df['4. close'].diff()
        df['dltup'] = np.where(df['delta'] < 0, 0, df['delta'])
        df['dltdw'] = np.where(df['delta'] > 0, 0, df['delta'])
        df['dltup_rol']=df['dltup'].ewm(span=n,adjust=False).mean()
        df['dltdw_rol']=df['dltdw'].ewm(span=n,adjust=False).mean().abs()
        df['RSI'] = 100 - (100 / (1 + df['dltup_rol'] / df['dltdw_rol']))
        self.df['RSI'] = df['RSI']

    def do_rsi_wilder(self, n=14):
        """Wilder’s Smoothing Method

            SPANwilder = SPANema*2 -1 (this is the commonly used calculation)

        Args:
            n (int): span
        """
        n = n*2 -1
        self.do_rsi_ema(n)
        return self

    def get_rsi(self, n=14):
        self.do_rsi_wilder(n)
        return self.df['RSI'][-1]

    def get_relative_volume(self, n=10):
        """Get ratio between last volume vs. defined volume SMA

        Args:
            n (int): length to define SMA
        Returns:
            ratio (float): last volume / volume-SMA
        """
        # df = self.df.copy(deep=True)
        ratio = 0
        df = self.df
        df['Volume_MA'] = df['5. volume'].rolling(n).mean()
        df['Volume_background'] = df['5. volume'].rolling(30).mean()
        last = df['5. volume'][-1]
        average = df['Volume_MA'][-1]
        average_background = df['Volume_background'][-1]
        # print ('-->> ', last, average)
        if average_background > 0:
            ratio = average/average_background
        return ratio

    def get_volume_index(self, n=10, m=30, hold=""):
        """Get index for volume contraction

        Args:
            n (int): short look-back period for high volume day
            m (int): long look-back period for volume moving average
            hold (str): if hold equals 'h', test if price is held well above high volume days's low
        return:
            float: high volume / low volume ratio
            string: maximum relative volume in look-back period and current relative volume
        """
        ratio = 0
        df = self.df
        df["date"] = df.index

        # get relative volume in the short look-back period
        recent = df.copy(deep=True).tail(n)
        average_volume = recent['5. volume'].median()
        recent['relative_volume'] = recent['5. volume'] / (average_volume + 1)
        relative_volume_short_max = recent['relative_volume'].max()
        relative_volume_short_current = recent['relative_volume'][-1]

        # get relative volume in the long look-back period
        average_volume_long = df['5. volume'].rolling(m).median()[-1]
        relative_volume_long_current = df['5. volume'][-1] / (average_volume_long + 1)

        # get the greater value for current relative volume
        relative_volume_current = max(relative_volume_short_current, relative_volume_long_current)
        # relative_volume_current = relative_volume_short_current

        # test if price stays above the low of the highest volume date
        hold_well = False
        if hold:
            date_highest_volume = df['5. volume'][(0-n):].idxmax()
            index_highest_volume = date_to_index(date_highest_volume, df["date"])
            date_lowest_closing =  df['3. low'][index_highest_volume:].idxmin()
            days_after_highVol = df.shape[0] - 1 - index_highest_volume
            # print(date_highest_volume, date_lowest_closing, index_highest_volume)
            if date_highest_volume == date_lowest_closing and days_after_highVol >= 3:
                if hold == 'h':
                    hold_well = True
            elif hold == 'x':
                hold_well = True
        else:
            hold_well = True

        # calculate ratio only if last day's relative volume is lower than median
        if hold_well: # and 0 < relative_volume_current <= 1
            ratio = relative_volume_short_max/relative_volume_current
        return ratio, f"{relative_volume_short_max} {relative_volume_current}"

    def get_zigzag_score(self, days):
        # test = self.df.tail(days)['4. close']
        #
        # std = test.rolling(days).std()[-1]
        # mean = test.rolling(days).mean()[-1]
        # z_score = (test - mean).abs() / std

        df2 = df = self.df.copy(deep=True).tail(days)
        std = df2['4. close'].rolling(days).std()[-1]
        mean = df2['4. close'].rolling(days).mean()[-1]
        df2['z_score'] = (df2['4. close'] - mean).abs() / std

        df3 = df2.loc[df2['z_score'] < 2]

        if df3.shape[0] < df2.shape[0] * 0.75:
            return 1

        days = df3.shape[0]
        test = df3['4. close']

        high = test.max()
        low  = test.min()
        mid_price = (high + low)/2
        mid_day_index = int(days/2)
        test1 = test[:mid_day_index]
        test2 = test[mid_day_index:]
        s1_high = np.where(test1 > mid_price, 1, 0).sum()
        s1_low  = np.where(test1 < mid_price, 1, 0).sum()
        s2_high = np.where(test2 > mid_price, 1, 0).sum()
        s2_low  = np.where(test2 < mid_price, 1, 0).sum()

        #
        std = df2['1. open'].rolling(days).std()[-1]
        mean = df2['1. open'].rolling(days).mean()[-1]
        df2['z_score'] = (df2['1. open'] - mean).abs() / std

        df3 = df2.loc[df2['z_score'] < 2]

        if df3.shape[0] < df2.shape[0] * 0.75:
            return 1

        days = df3.shape[0]
        test = df3['1. open']

        high = test.max()
        low  = test.min()
        mid_price = (high + low)/2
        mid_day_index = int(days/2)
        test1 = test[:mid_day_index]
        test2 = test[mid_day_index:]
        s1_high += np.where(test1 > mid_price, 1, 0).sum()
        s1_low  += np.where(test1 < mid_price, 1, 0).sum()
        s2_high += np.where(test2 > mid_price, 1, 0).sum()
        s2_low  += np.where(test2 < mid_price, 1, 0).sum()

        # print(s1_high, s2_high, s1_low, s2_low)
        p = chisquare([s1_high, s2_high], [s1_low, s2_low])
        # print (p)

        return p.pvalue

    def get_trading_uprange(self, day):
        """
        Get the distance between last closing price and the maximum price in specified time

        Argument
            day : time length to calculate maximum price
        Return
            float, the difference in percentage
        """
        df = self.df.copy(deep=True)
        prices = df["4. close"][-1]
        history = df["10MA"].tail(day)
        return (history.max() - prices) / history.max()

    def get_price_change_to_close(self):
        df = self.df
        df['change_to_close'] = df['4. close'].diff()/df['4. close'].shift()
        # print (df['change_to_close'][-1], df['4. close'][-1], df['4. close'].diff()[-1])
        return df['change_to_close'][-1]/df['4. close'][-1]

    def cross_up(self, indicator1, indicator2, days):
        # print ('*', days)
        df = self.df.copy(deep=True)
        df['signal'] = df[indicator1] - df[indicator2]
        df['signal'] = np.where(df['signal'] > 0, 1, 0)
        cross = df.tail(days)["signal"].diff().abs().sum()
        if cross == 0:
            # print (df.tail(10)["signal"])
            return False
        else:
            return True

    def converge(self, indicator1, indicator2, days):
        # print ('*', days)
        df = self.df.copy(deep=True)
        df['signal'] = df[indicator1] - df[indicator2]
        df['signal'] = np.where(df['signal'] > 0, 1, 0)
        cross = df.tail(days)["signal"].diff().abs().sum()
        if cross == 0:
            # print (df.tail(10)["signal"])
            return True
        else:
            return False

    def ema_slice(self, indicator):
        indicator = str(indicator) + 'MA'
        last_day = self.df.iloc[-1, :]
        status = False
        if indicator not in last_day:
            return status
        if last_day['3. low'] <= last_day[indicator] <= last_day['4. close']:
            status = True
        return status


    #     def get_referenced_change(self, reference_date, days):
    #         self.df["date"] = self.df.index
    #         reference_index = date_to_index(pd.to_datetime(reference_date), self.df["date"])
    #         price_date0 = self.df["4. close"][reference_index]+ 0.00001
    #         price_examine=0
    #         date_added = 0
    #         for i in range(reference_index+1, reference_index+days+1, 1):
    #             #print (i, dfPrice.shape[0])
    #             if i > (self.df.shape[0]-1): break
    #             date_added = date_added + 1
    #             #print (price_date0, self.df["4. close"][i] )
    #             price_examine += self.df["4. close"][i]
    #             #print (date_added, price_examine)
    #         if date_added==0 or price_examine==0:
    #             ratio = 100
    #         else:
    #             ratio=(price_examine/date_added - price_date0)/price_date0
    #         return ratio

    def get_referenced_change(self, reference_date, subject):
        ratio = ""

        # set reference date
        self.df["date"] = self.df.index
        reference_index = date_to_index(pd.to_datetime(reference_date), self.df["date"])
        price_date0 = self.df["4. close"][reference_index] + 0.00001

        # handle a single subject date
        if '-' in subject:
            mymatch = re.match(r'\d+\-\d+\-\d+', subject)
            if mymatch:
                subject_index = date_to_index(pd.to_datetime(subject),
                                              self.df["date"])
                price_subject = self.df["4. close"][subject_index]
                ratio = (price_subject - price_date0) / price_date0
            else:
                print("x-> invalid input {reference_date},{subject}")
                exit(0)
        # handle multiple subject dates
        else:
            subject = int(subject)
            price_examine = 0
            date_added = 0
            for i in range(reference_index + 1, reference_index + subject + 1, 1):
                # print (i, dfPrice.shape[0])
                if i > (self.df.shape[0] - 1): break
                date_added = date_added + 1
                # print (price_date0, self.df["4. close"][i] )
                price_examine += self.df["4. close"][i]
                # print (date_added, price_examine)
            if date_added == 0 or price_examine == 0:
                ratio = 100
            else:
                ratio = (price_examine / date_added - price_date0) / price_date0

        return ratio

    def get_consolidation(self, period):
        # self.do_rsi_wilder()
        df = self.df.copy(deep=True)
        average = df['4. close'].rolling(period).mean()[-1]
        # print(average)

        sub = df.copy(deep=True).tail(period)
        sub['std_error'] = (sub['4. close'] - average) ** 2
        sub['diff_close'] = (sub['4. close'] - average).abs()
        sub['diff_open'] = (sub['1. open'] - average).abs()
        sub['diff_abs'] = np.where(sub['diff_close'] > sub['diff_open'], sub['diff_close'], sub['diff_open'])

        sub['trading_range'] = sub['1. open'] - sub['4. close']
        sub['trading_range_abs'] = sub['trading_range'].abs()

        std = sub['diff_abs'].rolling(period).mean()[-1]/sub['trading_range_abs'].rolling(period).median()[-1]

        # print(sub['std_error'])
        # print(std)
        # print('//')

        return std

    def ema_attraction(self, ema_len, period):
        # self.do_rsi_wilder()
        df = self.df.copy(deep=True)
        # average = df['4. close'].rolling(period).mean()[-1]
        ema = self.df[f"{ema_len}MA"]
        # print(average)

        sub = df.copy(deep=True).tail(period)
        # sub['std_error'] = ((sub['4. close'] - ema) ** 2) / ema

        sub['diff1'] = sub['10MA'] - sub['100MA']
        sub['diff2'] = sub['10MA'] - sub['200MA']
        sub['diff3'] = sub['100MA'] - sub['200MA']

        sub['diffSum'] = sub['diff1'].abs() + sub['diff2'].abs() + sub['diff3'].abs()
        sub['diffSum'] = sub['diffSum'] / sub['150MA']

        std = sub['diffSum'].rolling(period).mean()[-1]

        sub['diffLarge'] = np.where(sub['diffSum'] > std, 1, 0)

        ratio = sub['diffLarge'].sum() / sub['diffLarge'].size

        return ratio


    def ema_entanglement(self, ema_fast, ema_slow, period):
        """Count how many times 2 EMAs cross each in defined recent period
        
        Args:
            ema_fast (int): number of days to define fast moving average
            ema_slow (int): number of days to define slow moving average
            period (int): number of days to define recent lookback period
            
        Returns:
            int (int): number of crossings between the two EMAs
        """
        
        df = self.df.copy(deep=True)
        df['fast'] = df["4. close"].ewm(span=ema_fast, adjust=False).mean()
        df['slow'] = df["4. close"].ewm(span=ema_slow, adjust=False).mean()
        df = df.tail(period)
        df['diff'] = df['fast'] - df['slow']
        df['signal'] = np.where(df['diff'] > 0, 1, 0)
        
        # total number of times two EMA cross each other
        return df['signal'].diff().abs().sum()
        


