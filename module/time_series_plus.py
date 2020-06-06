import re
import numpy as np
import pandas as pd
from module.candlestick import date_to_index


class TimeSeriesPlus:
    def __init__(self, df):
        self.df = df.copy(deep=True)
        self.ema_length = [3, 20, 50, 100, 150, 200]
        self.sma_multiple()

    def sma_multiple(self):
        # ma_days = [3, 20, 50, 100, 150, 200]
        df = self.df
        if '4. close' in df.columns:
            # for days in ma_days:
            for days in self.ema_length:
                # df[str(days)+'MA'] = df["4. close"].rolling(days).mean()
                df[str(days) + 'MA'] = df["4. close"].ewm(span=days, adjust=False).mean()
            # simple moving average for bollinger band
            df["20SMA"] = df["4. close"].rolling(20).mean()
            df['STD20'] = df["4. close"].rolling(20).std()
            df['BB20u'] = df['20SMA'] + df['STD20'] * 2
            df['BB20d'] = df['20SMA'] - df['STD20'] * 2
            df['BB20d_SMA10'] = df['BB20d'].rolling(10).mean()
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

    def hit_horizontal_support(self, days, length, num):
        """Close touch down and slice by EMA

        Args:
            days (int): recent period in which pivots are considered
            length (int): length of period (in days) to calculate pivots and to test if 3EMA is above last close
            num (int): minimal number of pivots

        Returns:
              boolean
        """
        # test pivot number
        self.find_pivot(length)
        if self.horizon_slice(days) < num:
            return False

        # test if prices were above support
        horizontal_support = self.df['4. close'][-1]
        stay_above = self.two_dragon_internal(3, horizontal_support, length, self.df, 0.9)

        if stay_above == 1:
            return True
        else:
            return False

    def get_latest_performance(self, period):
        """ 
        Get the price change for the last time period (i.e., the lastest 5 days 
        including today)
        
        Argument:
            period  : number of days (int) to define this period
        Return : 
            a float representing price change over the period
        """
        df_latest_period = self.df.tail(period)
        begin = df_latest_period["4. close"][0]
        last = df_latest_period["4. close"][-1]
        performance = 0
        if begin > 0:
            performance = (last - begin) / begin
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

    def get_trading_uprange(self, day):
        """ 
        Get the distance between last closing price and the maximum price in specified time
        
        Argument
            day : time length to calculate maximum price
        Return
            float, the difference in percentage
        """
        df = self.df.copy(deep=True)
        prices = df["4. close"].tail(day)
        return (prices.max() - prices[-1]) / prices.max()

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

    def two_dragon_internal(self, MAdays1, MAdays2, TRNDdays, dataframe, cutoff=0.8):
        """ Test parallel ema in defined period
        Args:
            MAdays1 (int): length for 1st ema
            MAdays2 (int): length for 2nd ema
            TRNDdays (int): period to test parallel
            dataframe (pandas dataframe): historical data
            cutoff (float): frequency of datapoint supporting parallel
        Returns:
            status (boolean): test result
        """

        status = 0  # =0: undetermined status; =1: 1st ema above 2nd ema; =-1: 1st ema below 2nd ema

        df = dataframe.copy(deep=True)
        ma1_key = str(MAdays1) + "MA"
        ma2_key = str(MAdays2) + "MA"

        # if dataframe length is not sufficient to calculate ema, return 0
        if (TRNDdays + MAdays1) > df.shape[0] or (TRNDdays + MAdays2) > df.shape[0]:
            # print(f"dataframe length {df.shape[0]} is not sufficient to calculate and do test using ema")
            return status

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

    def two_dragon(self, *args):
        """ Test 2 parallel EMAs in defined period
        """
        cutoff = 0.8
        if len(args) == 4: cutoff = args[3]
        status = self.two_dragon_internal(args[0], args[1], args[2], self.df, cutoff)
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
                if length < 50:
                    continue
                if not self.ema_slice(length):
                    continue
                stay_above = self.two_dragon_internal(3, length, days, self.df, 0.95)
                if stay_above == 1:
                    return True
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
        count = 0
        count += self.two_dragon_internal(20, 50, TRNDdays, df, cutoff)
        count += self.two_dragon_internal(50, 100, TRNDdays, df, cutoff)
        count += self.two_dragon_internal(100, 150, TRNDdays, df, cutoff)
        if count == 3:
            status = 1
        elif count == -3:
            status = -1
        # print("    ", status) #%
        return status

    def in_uptrend(self, TRNDdays, cutoff=0.8, blind=0):
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
        offset = pd.offsets.timedelta(days=-6)
        self.df = self.df.resample('W', loffset=offset).apply(logic)

    def get_weekly(self):
        self.to_weekly()
        dataframe = self.df.copy(deep=True)
        return dataframe

    def get_volume(self):
        self.df['vol'] = self.df['5. volume']
        return self
    
    def sampling_stks_bb(self, n, m):
        prediction = 15
        stok, stod, signal, paction = self.stochastic_cross_internal(n, m)
        sts = self.df.copy(deep=True)
        sts['BB20dmax'] = sts["BB20d"].rolling(15).max()
        bb_dist_low = (sts["3. low"] - sts['BB20d']) / (sts['BB20u'] - sts['BB20d'])
        bb_dist_close = (sts["4. close"] - sts['BB20d']) / (sts['BB20u'] - sts['BB20d'])
        length = len(signal)

        win = 0
        loss = 0
        samples = {}
        samples_test = {}
        R = {}

        sampling_window = 220
        index_start = length - prediction - sampling_window
        if index_start < 0: index_start = 0
        for i in range(index_start, length - prediction):
            # print (signal[200])
            # if stod[i]<20 and signal[i]==1 and paction[i]<0.3 and bb_dist<0.05:

            ############## fixed #############
            if sts['5. volume'][i] < 100000: continue
            # stochastic
            if stod[i] > 30: continue
            if signal[i] <= 0: continue
            # no transaction due to gap up or down price on entry attempting day
            if (sts['2. high'][i] > sts['2. high'][i + 1]) or (sts['2. high'][i] < sts['3. low'][i + 1]): continue
            # candle pattern
            if paction[i] > 0.3: continue
            if sts['1. open'][i] > sts['4. close'][i] and paction[i] > 0.15: continue
            # close-BB distance
            """ bb_dist_low and bb_dist_close adjusted by Ely(20191106) and TPH(20191111)
            """
            if (bb_dist_low[i] < 0.05 or bb_dist_low[i - 1] < 0 or bb_dist_low[i - 2] < 0) and bb_dist_close[i] < 0.3:
                pass
            else:
                continue
                # remove straight down
            if sts['BB20d'][i - 14] > sts['BB20d'][i - 10] > sts['BB20d'][i - 5] > sts['BB20d'][i]:
                continue

            ############## fixed #############                

            """
            # keep straight up                
            if (
                #sts['BB20d'][i] = sts['BB20dmax'][i]
                (sts['BB20d'][i-12] < sts['BB20d'][i] and sts['BB20d'][i-6] < sts['BB20d'][i])
            ): pass
            else: continue            
            """
            if sts['long'][i] <= 0: continue

            # print ('6', sts.index[i])
            # if not ( sts['50MA'][i] < sts["4. close"][i] and sts["4. close"][i] < sts['20MA'][i]): continue
            # if not ( sts['50MA'][i] < sts['20MA'][i]): continue
            # if sts['4. close'][i]<sts['20MA'][i]: continue
            # print (sts.index[i])

            # add days to be predicted
            sub = sts.iloc[0:i + prediction - 1]
            # add history and observe day
            sub_test = sts.iloc[0:i + 1]

            # remove downtrend
            if self.in_uptrend_internal(sub_test, 90, 0.90, 0) == -1: continue
            if self.in_uptrend_internal(sub_test, 60, 0.90, 0) == -1: continue
            if self.in_uptrend_internal(sub_test, 20, 0.90, 0) == -1: continue
            if self.in_uptrend_internal(sub_test, 120, 0.90, 0) == -1: continue

            date = "{}".format(stok.index[i]).rstrip('00:00:00')
            date = date.strip()
            # if '18-10-' in date or '18-11-' in date or '18-12-' in date or '19-01-' in date: continue

            # load test to be plotted
            samples[date] = sub.tail(80)
            # load show-data to be plotted
            samples_test[date] = sub_test.tail(80)

            sts['5daymin'] = sts['3. low'].rolling(3).min()
            entry = sts['2. high'][i]
            sell_stoploss = sts['5daymin'][i]
            r_count = self.fate(sub, sts.index[i], entry, sell_stoploss, True)
            R[date] = r_count
            if r_count > 0: win += 1
            if r_count < 0: loss += 1
        return samples_test, samples, R, win, loss

    def sampling_below_bb(self):
        samples = {}
        sts = self.df.copy(deep=True)
        bb_dist_close = (sts["4. close"] - sts['BB20d']) / (sts['BB20u'] - sts['BB20d'])
        length = sts.shape[0]
        for i in range(100, length - 15):
            if bb_dist_close[i] < -0.1 and sts['BB20d'][i] < sts["2. high"][i + 1] and sts["4. close"][i] > \
                    sts['100MA'][i]:
                sub_show = sts.iloc[i - 100:i + 13]
                sub_test = sts.iloc[i - 100:i]
                if self.in_uptrend_internal(sub_test, 60, 0.8, 0) == 0: continue
                date = "{}".format(sts.index[i]).rstrip('00:00:00')
                samples[date] = sub_show
        return samples

    def sampling_plunge_macd(self, recovery=5):
        PLUNGE_DEPTH = 0.15
        SPAN_FOR_PLUNGE = 20  # days to calculate plunge of price
        RSI_CUTFF = 15
        AVOID = 20  # the latest day span to avoid from sampling
        PRICE = 10
        prediction = AVOID
        self.macd_cross_up()
        self.do_rsi_wilder()

        sts0 = self.df.copy(deep=True)
        sts = self.df.copy(deep=True)

        # calculate necessary parameters
        sts = sts.iloc[0:(sts.shape[0] - AVOID)]
        # print('row num', sts.shape[0], sts0.shape[0])
        sts['RSImin'] = sts['RSI'].rolling(recovery).min()
        sts['signal'] = sts['signal'].diff()
        sts['signal'] = np.where(sts['signal'] > 0, 1, 0)
        sts['max_30days'] = sts['4. close'].rolling(SPAN_FOR_PLUNGE).max()
        sts['loss'] = (sts['max_30days'] - sts['4. close']) / sts['max_30days']
        sts['paction'] = sts['4. close'] - sts['1. open']

        # filter for rows meeting requirement
        sts['row_num'] = np.arange(len(sts))
        length = sts.shape[0]
        sampling_window = 220
        index_start = length - prediction - sampling_window
        if index_start < 0: index_start = 1
        sts2 = sts.iloc[index_start: length - prediction]

        """
        print (sts.index[index_start], sts.index[length-prediction])
        print (sts2.index[0], sts2.index[-1])
        print (sts['row_num'][index_start], index_start, sts['row_num'][length-prediction],length-prediction)
        print (sts2['row_num'][0], sts2['row_num'][-1])
        """

        # MACD data line cross up signal line
        sts2 = sts2[sts2['signal'] == 1]

        sts2 = sts2[sts2['5. volume'] > 100000]
        sts2 = sts2[sts2['long'] > 0]
        # Minimal price drop to be considered plunge
        sts2 = sts2[sts2['loss'] > PLUNGE_DEPTH]
        # Maximal RSI to be considered plunge
        sts2 = sts2[sts2['RSImin'] < RSI_CUTFF]
        # price moves up since openning
        sts2 = sts2[sts2['paction'] > 0]

        win = 0
        loss = 0
        samples = {}
        samples_test = {}
        R = {}
        # print('row num', sts2.shape[0])

        # print (index_start, length-prediction)
        # for i in range(index_start, length-prediction):
        back = 150
        for i in sts2['row_num']:
            # remove names with small price
            if sts0['4. close'][i] < PRICE: continue
            # trading day price doesn't hit buy stop loss
            if sts0['2. high'][i] > sts0['2. high'][i + 1]: continue
            # slice 65 days before and 20 days after the timepoint
            start = i - back
            if start < 0: start = 0
            sub_show = sts0.iloc[start:i + AVOID]
            sub_test = sts0.iloc[start:i + 1]
            # remove poor dataset
            if sub_show.shape[0] < 5: continue
            # remove late 2018 and early 2019 period

            if self.in_uptrend_internal(sub_test, len(sub_test), 0.9, 0) == -1:
                print('heavy downtrend')
                continue

            date = "{}".format(sts.index[i]).rstrip('00:00:00')
            # if '18-10-' in date or '18-11-' in date or '18-12-' in date or '19-01-' in date: continue

            samples[date] = sub_show
            samples_test[date] = sub_test

            sts['5daymin'] = sts['3. low'].rolling(5).min()
            entry = sts['2. high'][i]
            sell_stoploss = sts['5daymin'][i]
            r_count = self.fate(sub_show, sts.index[i], entry, sell_stoploss)
            R[date] = r_count
            if r_count > 0: win += 1
            if r_count < 0: loss += 1
        return samples_test, samples, R, win, loss

    def fate(self, df, observe_date, entry, sell_stoploss, sticky=False):
        observe_date_index = df.index.get_loc(observe_date)

        risk = entry - sell_stoploss + 0.000001

        onboard = df.iloc[observe_date_index + 1:]
        # no trade if next day price does not go higher than anticipated entry
        # if onboard.iloc[0,:]['2. high'] < entry: return 0
        # holding period less than 2 (poor data) -> skip
        if onboard.shape[0] < 2: return 0

        exit = 0
        last = 0

        for date, row in onboard.iterrows():
            if row['3. low'] <= sell_stoploss:
                if row['2. high'] < sell_stoploss:
                    exit = row['4. close']
                else:
                    exit = sell_stoploss
                break
            else:
                # print('live', str(sell_stoploss) )
                dist = row['4. close'] - sell_stoploss
                if sticky:
                    dist_byR = dist // risk
                    if dist_byR > 1:
                        sell_stoploss = sell_stoploss + risk * (dist_byR - 1)
                exit = row['4. close']
        # print ("//\n")
        # print  (exit, entry, risk)
        r = (exit - entry) / risk
        if r > 0 and r < 0.001: r = 0
        return r

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
        last = df['5. volume'][-1]
        average = df['Volume_MA'][-1]
        # print ('-->> ', last, average)
        if last > 0:
            ratio = last/average
        return ratio

    def get_volume_index(self, n=10, m=30):
        ratio = 0
        df = self.df
        df['Volume_MA'] = df['5. volume'].rolling(n).mean()
        df['Volume_MA_long'] = df['5. volume'].rolling(m).mean()
        df['relative_volume'] = df['5. volume'] / (df['Volume_MA']+ 1)
        df['relative_volume_max'] = df['relative_volume'].rolling(n).max()
        relative_volume_max_last = df['relative_volume_max'][-1]
        relative_volume_current = df['5. volume'][-1]/(df['Volume_MA_long'][-1]+1)

        # too stringent
        # df['volume_adjusted'] = np.where(df['5. volume'] > df['Volume_MA_long'], df['Volume_MA_long'], df['5. volume'])
        # df['volume_adjusted_ma'] = df['volume_adjusted'].rolling(m).mean()
        # relative_volume_current = df['5. volume'][-1]/(df['volume_adjusted_ma'][-1]+1)

        relative_volume_current = df['5. volume'][-1] / (df['Volume_MA_long'][-1] + 1)
        if relative_volume_max_last > 2 and 0 < relative_volume_current < 1:
            ratio = relative_volume_max_last/relative_volume_current

        # print(df['relative_volume'][-6:])
        # print (df['relative_volume_max'][-1], df['relative_volume'][-1], ratio)
        return ratio, f"{relative_volume_max_last} {relative_volume_current}"

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
