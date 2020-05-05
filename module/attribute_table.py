"""
AttributeTable class and methods
"""

import os
import sys
import math
import numpy as np
import pandas as pd
import module.utility as utility
from module.time_series_plus import TimeSeriesPlus
from module.candlestick import date_to_index



class AttributeTable:
    """A class representing a list of securities and their attributes
    
    Attributes:
        attribute_table (dataframe): with symbol column as index
        data_dir (str): location of directory containing price data
        sts_daily (dict): dictionary holding timeseries data for each security
        kwargs (dict): dictionary holding pairs of arguments and values
    Methods:
        get_new_attribute_table():
            return securities attribute table
        basic_processing():
            default data cleaning and sorting
        make_header():
            create columns for header and annotation information
        read_timeseries():
            read in price data of securities
        work():
            keyword argument-based filtering and sorting
    """

    def __init__(self, attribute_table, data_dir, kwargs):
        self._attribute_table = attribute_table.copy(deep=True)
        self.data_dir = data_dir
        # self.file_name = file_name
        # self.kwargs_backup = kwargs
        self.kwargs = kwargs
        # self.new_file_name = ""
        self.sts_daily = {}
        self.basic_processing()
        self.make_header()
        self.sts_daily = self.read_timeseries()

    def get_attribute_table(self):
        return self._attribute_table

    def basic_processing(self):
        """Basic data processing (update self.description)
        
            Remove oil and gas related securities (high volatility);
            Add buy- and sold-dates;
            Sort securities by purchase date followed by security name;
        """
        df = self._attribute_table
        if "Industry" in df:
            df = df[~df["Industry"].str.contains("Oil and Gas")]

        # format data-added and -sold information
        if "Date Added" in df.columns:
            df["Date Added"] = df["Date Added"].apply(utility.fix_date_addeddded)
            df["Date Added"] = pd.to_datetime(df["Date Added"])
        if "Date Sold" in df.columns:
            df["Date Sold"] = df["Date Sold"].apply(utility.fix_date_added)
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
            print("#-x No 'Symbol' column in the input security data sheet")
            exit(1)

        self._attribute_table = df

    def make_header(self):
        """Create header and annotation for each security
        
           Header summarizes zacks rank, value/growth score, buy
           recommendation, long-term growth, etc. Annotation summarize
           PE, PEG and next earning report date. 
        """
        df = self._attribute_table
        df["header"] = ""
        df["annotation"] = ""
        for sticker, row in df.iterrows():
            row_copy = row.copy(deep=True)

            # prepare figure header
            header = ""
            annot = ""
            # prepare header for display in chart
            if "Zacks Rank" in row:
                if row["Zacks Rank"] and not math.isnan(row["Zacks Rank"]):
                    header = header + " zr{}".format(str(int(row["Zacks Rank"])))
            if "Value Score" in row:
                header = header + "{}/{}".format(row["Value Score"], row["Growth Score"])
            if "# Rating Strong Buy or Buy" in row and "# of Brokers in Rating" in row:
                header = header + "br{}/{}".format(int(row["# Rating Strong Buy or Buy"]),
                                                   int(row["# of Brokers in Rating"]))
            if "Long-Term Growth Consensus Est." in row:
                header = header + "ltg{}".format(row["Long-Term Growth Consensus Est."])
            df.loc[sticker, "header"] = header
            if "P/E (Trailing 12 Months)" in row:
                annot = annot + "pe" + str(row["P/E (Trailing 12 Months)"])
            if "PEG Ratio" in row:
                annot = annot + "peg" + str(row["PEG Ratio"])
            if "Next EPS Report Date " in row:
                annot = annot + "eday" + str(row["Next EPS Report Date "])
            df.loc[sticker, "annotation"] = annot

        self._attribute_table = df

    def df_rename_columns(self, df):
        if 'Date' in df.columns:
            df.rename(columns={'Date':'date'}, inplace=True)
        if 'Open' in df.columns:
            df.rename(columns={'Open':'1. open'}, inplace=True)
        if 'High' in df.columns:
            df.rename(columns={'High':'2. high'}, inplace=True)
        if 'Low' in df.columns:
            df.rename(columns={'Low':'3. low'}, inplace=True)
        if 'Close' in df.columns:
            df.rename(columns={'Close':'4. close'}, inplace=True)
        if 'Volume' in df.columns:
            df.rename(columns={'Volume':'5. volume'}, inplace=True)
        return df

    def read_timeseries(self):
        """Read price data for each security and load into memory
           Securities without price data are dropped.
        """

        dict_sts = {}
        for symbol, row in self._attribute_table.iterrows():
            file = self.data_dir + "/" + symbol + ".txt"
            if os.path.exists(file):
                try:
                    price = pd.read_csv(file, sep="\t", parse_dates=['date'], index_col=['date'])
                except ValueError:
                    price = pd.read_csv(file, sep="\t", parse_dates=['Date'], index_col=['Date'])
                    price = self.df_rename_columns(price)
                except:
                    e = sys.exc_info()[0]
                    print("x-> Error while reading historical data; ", e)

                # remove rows with NA and remove df with <200 rows
                price.replace('', np.nan, inplace=True)
                price = price.dropna(axis='index')
                if price.shape[0] < 200:
                    self._attribute_table = self._attribute_table.drop(symbol, axis=0)
                    continue

                price = price.sort_index(axis = 0)

                # remove df without data in backtest date
                if self.kwargs['backtest_date']:
                    backtest_date = self.kwargs['backtest_date']
                    if backtest_date in price.index:
                        loci = price.index.get_loc(self.kwargs['backtest_date'])
                        price = price[0:loci+1]
                    else:
                        self._attribute_table = self._attribute_table.drop(symbol, axis=0)
                        continue

                # sts = TimeSeriesPlus(price).sma_multiple()
                print ('x', symbol)
                sts = TimeSeriesPlus(price)
                dict_sts[symbol] = sts
            else:
                self._attribute_table = self._attribute_table.drop(symbol)
        return dict_sts

    def work(self):
        """Filter and sort securities based on keyword arguments
        """

        if self.kwargs["sort_brokerrecomm"] and "# Rating Strong Buy or Buy" in self._attribute_table:
            self._attribute_table = self._attribute_table.sort_values(["# Rating Strong Buy or Buy"],
                                                                      ascending=False)
            del self.kwargs['sort_brokerrecomm']

        if self.kwargs["sort_industry"] and "Industry" in self._attribute_table:
            self._attribute_table = self._attribute_table.sort_values(["Industry"])
            del self.kwargs["sort_industry"]

        if self.kwargs["sort_earningDate"]:
            if "Next EPS Report Date  (yyyymmdd)" in self._attribute_table:
                self._attribute_table["Next EPS Report Date "] = self._attribute_table[
                    "Next EPS Report Date  (yyyymmdd)"]
                self._attribute_table = self._attribute_table.drop("Next EPS Report Date  (yyyymmdd)", axis=1)

            if "Next EPS Report Date " in self._attribute_table:
                # sort symbols by last earning date
                self._attribute_table["Next EPS Report Date "] = self._attribute_table.to_numeric(
                    self.df["Next EPS Report Date "])
                self._attribute_table = self._attribute_table.sort_values(["Next EPS Report Date "], ascending=True)

        if self.kwargs["sort_zacks"]:
            sort_zacks = self.kwargs["sort_zacks"]
            type = ''
            cut = ''
            if ',' in sort_zacks:
                (type, cut) = sort_zacks.split(',')
                cut = cut.upper()
            else:
                type = sort_zacks

            if type == 'V' and "Value Score" in self._attribute_table:
                if cut:
                    self._attribute_table = self._attribute_table[self._attribute_table["Value Score"] <= cut]
                    print(f"# {self._attribute_table.shape[0]:>5} symbols meeting Value cutoff {cut}")
                self._attribute_table = self._attribute_table.sort_values(["Value Score"])
            elif type == 'G' and "Growth Score" in self._attribute_table:
                if cut:
                    self._attribute_table = self._attribute_table[self._attribute_table["Growth Score"] <= cut]
                    print(f"# {self._attribute_table.shape[0]:>5} symbols meeting Growth cutoff {cut}")
                self._attribute_table = self._attribute_table.sort_values(["Growth Score"])
            else:
                print(f"invalide input for -szk: {sort_zacks}")
                exit(1)
            del self.kwargs["sort_zacks"]

        if len(self.kwargs) > 0:

            # method sort_trange
            if self.kwargs["sort_trange"]:
                """
                Sort a list of securities based on their filter_upward trading range for a defined recent 
                period
                
                Outcome: update instance variable 'description'
                """
                argument = self.kwargs["sort_trange"]
                days, cutoff = argument.split(',')
                trange_days = int(days)
                trange_cutoff = float(cutoff)
                self._attribute_table["Sort"] = 0
                if trange_days > 0:
                    for symbol, row in self._attribute_table.iterrows():
                        self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].get_trading_uprange(
                            trange_days)
                if trange_cutoff >= 0:
                    self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] >= trange_cutoff]
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=False)
                print(len(self._attribute_table), " symbols meet user criterion")

            # method filter_macd_sgl
            if self.kwargs["filter_macd_sgl"]:
                # Filter securities based on MACD cross above signal line
                # Outcome: shorten instance variable 'description'
                # example: input variable "14,20"
                #     K line with 14-day EMA and D line with 20-day EMA

                filter_macd_sgl = self.kwargs["filter_macd_sgl"]
                args = filter_macd_sgl.split(',')
                if len(args) == 2:
                    (sspan, lspan) = list(map(int, args))
                    days = 1
                elif len(args) == 3:
                    (sspan, lspan, days) = list(map(int, args))
                else:
                    print(f"macd argument cannot be recognized: {filter_macd_sgl}")
                    exit(1)

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].macd_cross_up(sspan, lspan, days)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > 0]
                print(len(self._attribute_table), " symbols meet user criterion")

            if self.kwargs["filter_rsi"]:
                args = self.kwargs["filter_rsi"].split(',')
                try:
                    (low, high) = list(map(int, args))
                except ValueError:
                    print ("Invalid rsi argument: " + args)

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].get_rsi()
                #     print ( self.sts_daily[symbol].get_rsi() )
                # print ( self._attribute_table["Sort"] )
                self._attribute_table = self._attribute_table.loc[ low < self._attribute_table["Sort"] ]
                self._attribute_table = self._attribute_table.loc[ self._attribute_table["Sort"] < high]
                print("# {:>5} symbols meet rsi criteria".format(len(self._attribute_table)))

            if self.kwargs["sort_ema_distance"] > 0:
                # sort symbols by last close-to-SMA distance

                sort_ema_distance = self.kwargs["sort_ema_distance"]

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].get_SMAdistance(
                        sort_ema_distance)
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=True)

            # method filter based on stochastic signal
            if self.kwargs["filter_stochastic_sgl"]:
                # filter for oversold (d < cutoff) tickers with stochastic K > D and
                # bullish price action (paction < cutoff)
                # input string: stochastic long term,
                #               stochastic short term,
                #               stochastic d cutoff,
                #               k>d ('all') or k just cross d up ('crs' or any string)

                filter_stochastic_sgl = self.kwargs["filter_stochastic_sgl"]
                try:
                    (n, m, cutoff, mode) = filter_stochastic_sgl.split(',')
                    n = int(n)
                    m = int(m)
                    cutoff = float(cutoff)
                except:
                    e = sys.exc_info()[0]
                    print("x-> invalid stochastic argument input ", e)
                    sys.exit(1)

                for symbol in self._attribute_table.index:
                    (k, d, cross, bullish) = self.sts_daily[symbol].stochastic_cross(n, m)
                    status = True
                    if k > cutoff + 15 or d > cutoff:
                        status = False
                    if mode == 'all':
                        if k < d: status = False
                    elif cross <= 0:
                        status = False
                    if not status:
                        self._attribute_table.drop(symbol, inplace=True)
                print("# {:>5} symbols meet stochastic criteria".format(len(self._attribute_table)))

            if self.kwargs["filter_parallel_ema"]:
                args = self.kwargs["filter_parallel_ema"]
                array = args.split(',')
                array2 = []
                try:
                    array2 = list(map(int, array[0:3]))
                except ValueError:
                    print(f" argument {args} is invalid")
                    exit(1)
                if len(array) == 4:
                    array2.append(float(array[3]))

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].two_dragon(*array2)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > 0]

                print("# {:>5} symbols meet filter_parallel_ema criteria {}".format(len(self._attribute_table), args))

            if self.kwargs["filter_hit_ema_support"]:
                args = self.kwargs["filter_hit_ema_support"]
                array = args.split(',')
                try:
                    (ema, days) = list(map(int, array))
                except ValueError:
                    raise

                self._attribute_table["Sort"] = False
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].hit_ema_support(ema, days)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"]]
                print("# {:>5} symbols meet filter_hit_ema_support {}".format(len(self._attribute_table), args))

            if self.kwargs["sort_change_to_ref"]:
                # Sort securities by price change in a defined date or 
                #   period relative to a reference date
                # 
                # example: input varialbe "2020-20-01,4"
                #   set 2020-20-01 as reference date, calculate the average price of the
                #   following 4 day, and report the change that led to this average price and from
                #   the reference date
                # 
                # Outcome: update instance variable 'description'

                arg = self.kwargs["sort_change_to_ref"]
                aa = arg.split(',')
                # reference_date = aa[0]
                # days = aa[1]
                if len(aa) != 2:
                    raise ValueError("Argument \'{}\' does not contains exactly one comma".format(arg))
                else:
                    reference, subject = arg.split(',')

                self._attribute_table["Sort"] = 0
                for symbol, row in self._attribute_table.iterrows():
                    self._attribute_table.loc[symbol, "Sort"] = \
                        self.sts_daily[symbol].get_referenced_change(reference, subject)

                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=True)
                self._attribute_table["Date Added"] = reference
                if subject.count('-') == 2:
                    self._attribute_table["Date Sold"] = subject

            # method filter and sort by last close to bollinger band bottom border distance
            if self.kwargs["filter_bbdistance"]:
                filter_bbdistance = self.kwargs["filter_bbdistance"]
                list_arg = filter_bbdistance.split(',')
                cutoff = float(list_arg[0])
                days = 1
                test_bband_uptrend = False
                if len(list_arg) >= 2:
                    days = int(list_arg[1])
                if len(list_arg) == 3 and list_arg[2] =='up':
                    test_bband_uptrend = True

                self._attribute_table["Sort"] = 0
                for symbol, row in self._attribute_table.iterrows():
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].get_BBdistance(days)
                    df = self.sts_daily[symbol].df
                    if df.shape[0] < 100:
                        self._attribute_table.loc[symbol, "Sort"] = 1
                        continue

                    if test_bband_uptrend:
                        BB20d_uptrend = True
                        if df['BB20d'][-1] <= df['BB20d_SMA10'][-1]:
                            BB20d_uptrend = False
                        elif df['BB20d'][-3] <= df['BB20d_SMA10'][-3]:
                            BB20d_uptrend = False
                        elif df['BB20d'][-5] <= df['BB20d_SMA10'][-5]:
                            BB20d_uptrend = False
                        if not BB20d_uptrend:
                            self._attribute_table.loc[symbol, "Sort"] = 1

                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] <= cutoff]
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=True)

            if self.kwargs["sort_performance"]:
                arg = self.kwargs["sort_performance"]

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].get_latest_performance(
                        arg)

                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=False)

            if self.kwargs["filter_upward"]:
                filter_upward = self.kwargs["filter_upward"]
                args = filter_upward.split(',')

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].in_uptrend(*args)

                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > 0]
                print(
                    "# {:>5} symbols meet filter_upward criteria {}".format(len(self._attribute_table), filter_upward))

            if self.kwargs["filter_horizon_slice"]:
                try:
                    args = self.kwargs["filter_horizon_slice"].split(',')
                    days, num = list(map(int, args))
                except ValueError:
                    print(f" argument {args} is invalid")
                    exit(1)

                self._attribute_table["Sort"] = False
                for symbol in self._attribute_table.index:
                    pivot_caught = self.sts_daily[symbol].horizon_slice(days)
                    if pivot_caught >= num:
                        # print (symbol, pivot_caught, num)
                        self._attribute_table.loc[symbol, "Sort"] = True
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"]]
                print("# {:>5} symbols meet support slice criteria: {}".format(len(self._attribute_table), args))

            if self.kwargs["filter_ema_slice"]:
                # TBD: add look-back non-converge period
                filter_ema_slice = int(self.kwargs["filter_ema_slice"])

                self._attribute_table["Sort"] = False
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].ema_slice(filter_ema_slice)

                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"]]
                print("# {:>5} symbols meet EMA slice criteria: {}".format(len(self._attribute_table), filter_ema_slice))

            if self.kwargs["filter_hit_horizontal_support"]:
                try:
                    args = self.kwargs["filter_hit_horizontal_support"].split(',')
                    days, length, num = list(map(int, args))
                except ValueError:
                    print(f" argument {args} is invalid")
                    exit(1)

                self._attribute_table["Sort"] = False
                for symbol in self._attribute_table.index:
                    print('x3 ', symbol)
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily[symbol].hit_horizontal_support(days, length, num)

                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"]]
                print("# {:>5} symbols meet support slice criteria: {}".format(len(self._attribute_table), args))
