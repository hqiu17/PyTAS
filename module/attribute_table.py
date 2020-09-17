"""
AttributeTable class and methods
"""
import os
import sys
import math
import numpy as np
import pandas as pd
import threading
import multiprocessing
import module.utility as utility
from module.time_series_plus import TimeSeriesPlus
from module.candlestick import date_to_index


class AttributeTable():
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
        self.kwargs = kwargs
        self.backtest_date = ''
        self.backtest_date_extension = ''
        self.backtest_strategy = '2R'
        self.check_date = ''
        self.sts_daily_test = {}
        self.sts_daily_plot = {}
        self.attribute_table_bythread = []
        self.sts_daily_test_bythread = []
        self.sts_daily_plot_bythread = []

        # warming up steps
        self.basic_processing()
        self.backtest()
        self.make_header()
        self.read_timeseries()
        
    def combine_thread_output(self):
        attribute_table = pd.DataFrame()
        sts_daily_test = {}
        sts_daily_plot = {}
        
        if len(self.attribute_table_bythread) > 1:
            print("# {:>5} run with {} threads to read input data".format('', len(self.attribute_table_bythread)))
        
        for table in self.attribute_table_bythread:
#             print('subset', table.shape[0])
            if attribute_table.shape[0] < 1:
                attribute_table = table
            else:
                attribute_table = attribute_table.append(table)
        for i in self.sts_daily_test_bythread:
            sts_daily_test = {**sts_daily_test, **i}
        for i in self.sts_daily_plot_bythread:
            sts_daily_plot = {**sts_daily_plot, **i}

        self._attribute_table = attribute_table.copy(deep=True)
        self.sts_daily_test = sts_daily_test
        self.sts_daily_plot = sts_daily_plot
        

    def get_attribute_table(self):
        if self.check_date:
            self._attribute_table["Date Sold"] = self.check_date
        if self.backtest_date:
            self._attribute_table["Date Added"] = self.backtest_date

        # print('get_attribute_table', self._attribute_table.shape)
        return self._attribute_table

    def get_dict_timeseries(self):
        if len(self.sts_daily_plot) > 0:
            return self.sts_daily_plot
        else:
            return self.sts_daily_test

    def basic_processing(self):
        """Basic attribute data processing (update self.description)
        
            Remove oil and gas related securities (high volatility);
            Add buy- and sold-dates if available;
            Sort securities by purchase date followed by security name;
        """
        df = self._attribute_table.copy(deep=True)
        if "Industry" in df:
            df = df[~df["Industry"].str.contains("Oil and Gas")]

        # format data-added and -sold information
        if "Date Added" in df.columns:
            df["Date Added"] = df["Date Added"].apply(utility.fix_date_added)
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
            df.rename(columns={'Date': 'date'}, inplace=True)
        if 'Open' in df.columns:
            df.rename(columns={'Open': '1. open'}, inplace=True)
        if 'High' in df.columns:
            df.rename(columns={'High': '2. high'}, inplace=True)
        if 'Low' in df.columns:
            df.rename(columns={'Low': '3. low'}, inplace=True)
        if 'Close' in df.columns:
            df.rename(columns={'Close': '4. close'}, inplace=True)
        if 'Volume' in df.columns:
            df.rename(columns={'Volume': '5. volume'}, inplace=True)
        return df

    def backtest(self):
        """Set up backtest parameters if keyword argument is given
        """
        extension = ''
        backtest_date = ''
        strategy = ''
        if self.kwargs['backtest_date']:
            arg = self.kwargs['backtest_date']
            if ',' in arg:
                backtest_date, extension, strategy = arg.split(',')
                print ("backtest_date {}; extension {} strategy {}".format(backtest_date, extension, strategy))
                self.backtest_date_extension = int(extension)
                self.backtest_strategy = strategy
                self._attribute_table["PL"] = 0
                self._attribute_table["exit Price"] = ''
                self._attribute_table["Date sold"] = ''
            else:
                backtest_date = arg

        self.backtest_date = backtest_date

    def read_timeseries(self, minimal_rows=60):
        """Read price data for each security and load into memory
           Securities without price data are dropped.
        """
        minimal_volume = 100000

        # set up 
        df = self._attribute_table

        number_threads = 1
        step = round(self._attribute_table.shape[0]/number_threads)

        # split attribute_table into smaller subsets
        subsets = []    
        starter = 0
        for i in range(number_threads):
            if i == (number_threads - 1):
                subsets.append(df.iloc[starter:])
            else:
                subsets.append(df.iloc[starter : (starter + step)])
            starter = starter + step

        # read each sebset with a separate thread
        threads = []
        for subset in subsets:
            th = threading.Thread(target=self.read_timeseries_thread, args=(subset,))
#             multiprocessing does not work (can't share information across processor)
#             th = multiprocessing.Process(target=self.read_timeseries_thread, args=(subset,))
            threads.append(th)
            th.start()
        
        # wait for all threads to complete
        for th in threads:
            th.join()

        self.combine_thread_output()
        
        # Report
        if self.kwargs["remove_sector"]:
            print("# {:>5} symbols have valid time series data "
                  "(length>{}, volume>{} and not associated with sector(s) {}".format(
                len(self._attribute_table), minimal_rows, minimal_volume, self.kwargs["remove_sector"]))
        else:
            print("# {:>5} symbols with valid time series data (length>{} and volume>{})".format(
                len(self._attribute_table), minimal_rows, minimal_volume))


    def read_timeseries_thread(self, df, minimal_rows=60, minimal_volume = 100000):
        """Read price data for each security and load into memory
           Securities without price data are dropped.
        """
        dict_sts = {}
        dict_sts_plot = {}
        backtest_date_invalid = 0
        df_symbols = df.copy(deep=True)
        
        for symbol, row in df_symbols.iterrows():
#             print ('reading', symbol) #xxx
            # remove symbol associated with defined sectors
            removed_sector = ""
            if self.kwargs["remove_sector"]:
                arg = self.kwargs["remove_sector"]
                removed_sector = arg
                args = arg.split(",")
                remove = False
                if 'Sector' in row:
                    sector = row['Sector']
                    for a in args:
                        if a in sector:
                            remove = True
                            break
                if remove:
                    df_symbols = df_symbols.drop(symbol)
                    continue

            # read in data files
            file = self.data_dir + "/" + symbol + ".txt"
            if not os.path.exists(file):
                df_symbols = df_symbols.drop(symbol)            
            else:
                # read in data into dataframe
                try:
                    price = pd.read_csv(file, sep="\t", parse_dates=['date'], index_col=['date'])
                except ValueError:
                    price = pd.read_csv(file, sep="\t", parse_dates=['Date'], index_col=['Date'])
                    price = self.df_rename_columns(price)
                except:
                    e = sys.exc_info()[0]
                    print("x-> Error while reading historical data for {}\t error: {}".format(symbol, e))
                    df_symbols = df_symbols.drop(symbol)

                # remove rows with NA, remove df with insufficient rows or with low trading volume
                price.replace('', np.nan, inplace=True)
                price = price.dropna(axis='index')
                if symbol in df_symbols.index:
                    if price.shape[0] < minimal_rows or price["5. volume"][-1] < minimal_volume:
                        df_symbols = df_symbols.drop(symbol, axis=0)
                        continue

                price_for_test = price

                if self.backtest_date:
                    # handle backtest date
                    # 1) guess if backtest date is valid
                    # 2) add trading outcome to attribute_table
                    # 3) load time series data for display purpose
                    backtest_date = self.backtest_date

                    # test backtest date
                    # if date is missing in 10 consecutive symbols, the date is deemed invalid
                    if backtest_date_invalid >= 10:
                        print(f"Backtest date is likely not a trading day: {backtest_date}")
                        exit(0)

                    if backtest_date not in price.index:
                        backtest_date_invalid += 1
                        df_symbols = df_symbols.drop(symbol, axis=0)
                        continue
                    else:
                        backtest_date_invalid = 0

                    # Given valid backtest date, do trade
                    if backtest_date in price.index:
                        # assign back test dates
                        df_symbols.loc[symbol, 'Date Added'] = backtest_date
                        loci = price.index.get_loc(backtest_date) + 1
                        price_for_test = price[0:loci]


                        if self.backtest_date_extension:
                            extension = self.backtest_date_extension
                            loci_check = loci + 1 + extension
                            length = price.shape[0]
                            if loci_check > length-1:
                                loci_check = -1
                            price_plot = price[0:loci_check]
                            dict_sts_plot[symbol] = TimeSeriesPlus(price_plot).sma_multiple()

#                             r, key_prices, date = TimeSeriesPlus.get_fate(
#                                 'xxx', price, backtest_date, extension, 'next', 5, self.backtest_strategy)

                            r, key_prices, date = TimeSeriesPlus(price).get_fate(
                                backtest_date, extension, 'next', 5, self.backtest_strategy)
                                
#                             print(symbol, r, key_prices, date) #xxx
                 
                            if r == 'missing':
                                df_symbols = df_symbols.drop(symbol)
                            else:
                                df_symbols.loc[symbol, 'PL'] = r
                                df_symbols.loc[symbol, 'exit Price'] = key_prices
                                df_symbols.loc[symbol, 'Date Sold'] = date

                if self.kwargs["time_scale"]:
                    arg = self.kwargs["time_scale"]
                    scale = ""
                    mode = ""
                    if ',' in arg:
                        scale, mode = arg.split(",")
                    else:
                        scale = arg

                    if mode == "c": # =chartOnly
                        if scale == "week":
                            price_scaled = TimeSeriesPlus(price_for_test).get_weekly()
                            dict_sts_plot[symbol] = TimeSeriesPlus(price_scaled)
                        if scale == "month":
                            price_scaled = TimeSeriesPlus(price_for_test).get_monthly()
                            dict_sts_plot[symbol] = TimeSeriesPlus(price_scaled)
                    else:
                        if scale == "week":
                            price_for_test = TimeSeriesPlus(price_for_test).get_weekly()
                        if scale == "month":
                            price_for_test = TimeSeriesPlus(price_for_test).get_monthly()

                dict_sts[symbol] = TimeSeriesPlus(price_for_test)

        # # read SPY as benchmark
        # ref = self.data_dir + "/" + 'SPY' + ".txt"
        # if os.path.exists(ref):
        #     try:
        #         price = pd.read_csv(ref, sep="\t", parse_dates=['date'], index_col=['date'])
        #     except ValueError:
        #         price = pd.read_csv(ref, sep="\t", parse_dates=['Date'], index_col=['Date'])
        #         price = self.df_rename_columns(price)
        #     except:
        #         e = sys.exc_info()[0]
        #         print("x-> Error while reading historical data for {}\t error: {}".format(ref, e))
        #
        #     dict_sts['SPY'] = TimeSeriesPlus(price)

        self.attribute_table_bythread.append(df_symbols)
        self.sts_daily_test_bythread.append(dict_sts)
        self.sts_daily_plot_bythread.append(dict_sts_plot)
#         print(df_symbols.index)
#         print(dict_sts.keys())

    def work(self):
        """Filter and sort securities based on keyword arguments
        """

        # sort securities by attributes
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

            if self.kwargs["filter_price"]:
                arg = self.kwargs["filter_price"]
                args = arg.split(',')
                pmin = 0
                pmax = 10000
                if len(args) == 2:
                    (pmin, pmax) = list(map(float, args))
                else:
                    print(f"last closing price argument cannot be recognized: {arg}")
                    exit(1)
                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].df['4. close'][-1]
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > pmin]
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] < pmax]
                print("# {:>5} symbols meet price criteria".format(len(self._attribute_table)))

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
                        self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].get_trading_uprange(
                            trange_days)
                if trange_cutoff >= 0:
                    self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] >= trange_cutoff]
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=False)
                print("# {:>5} symbols meet sort_trange".format(len(self._attribute_table)))

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
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].macd_cross_up(sspan, lspan, days)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > 0]
                print("# {:>5} symbols meet macd criteria".format(len(self._attribute_table)))

            if self.kwargs["filter_ema_sgl"]:
                # Filter securities based on MACD cross above signal line
                # Outcome: shorten instance variable 'description'
                # example: input variable "14,20"
                #     K line with 14-day EMA and D line with 20-day EMA

                arg = self.kwargs["filter_ema_sgl"]
                args = arg.split(',')
                if len(args) == 2:
                    (fast, slow) = list(map(int, args))
                    days = 1
                elif len(args) == 3:
                    (fast, slow, days) = list(map(int, args))
                else:
                    print(f"macd argument cannot be recognized: {arg}")
                    exit(1)

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].ema_cross_up(fast, slow, days)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > 0]
                print("# {:>5} symbols meet ema crossing up criteria".format(len(self._attribute_table)))

            if self.kwargs["filter_rsi"]:
                # filter for rsi within define range, e.g., 20,50
                args = self.kwargs["filter_rsi"].split(',')
                try:
                    (low, high) = list(map(int, args))
                except ValueError:
                    print("Invalid rsi argument: " + args)

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].get_rsi()
                self._attribute_table = self._attribute_table.loc[low < self._attribute_table["Sort"]]
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] < high]
                self._attribute_table = self._attribute_table.sort_values(["Sort"])
                print("# {:>5} symbols meet rsi criteria".format(len(self._attribute_table)))

            if self.kwargs["filter_surging_volume"]:
                # filter for combination of volume increase with price going down
                args = self.kwargs["filter_surging_volume"].split(',')
                if len(args) <2:
                    print ("Invalid filter_surging_volume argument: {}".format(args))
                    exit(0)
                length = int(args[0])
                ratio = float(args[1])
                hold_up = ''
                if len(args)>2:
                    hold_up = args[2]
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"], details = \
                        self.sts_daily_test[symbol].get_volume_index(length, hold=hold_up)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > ratio]
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=False)
                print("# {:>5} symbols meet filter_surging_volume".format(len(self._attribute_table)))

            if self.kwargs["filter_exploding_volume"]:
                args = self.kwargs["filter_exploding_volume"]
                (length, cutoff) = args.split(',')
                length = int (length)
                cutoff = float(cutoff)
                for symbol in self._attribute_table.index:
                    sort_value = 0
                    if self.sts_daily_test[symbol].two_dragon(5, 15, 5, 0.9, vol=True) > 0:
                        sort_value = self.sts_daily_test[symbol].get_relative_volume(length)
                    self._attribute_table.loc[symbol, "Sort"] = sort_value

                    # self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].get_relative_volume(length)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > cutoff]
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=False)
                print("# {:>5} symbols meet exploding_surging_volume".format(len(self._attribute_table)))

            if self.kwargs['filter_consolidation_p']:
                args = self.kwargs['filter_consolidation_p']
                (length, cutoff) = args.split(',')
                length = int (length)
                cutoff = float(cutoff)
                for symbol in self._attribute_table.index:
                    sort_value = 0
                    if self.sts_daily_test[symbol].get_zigzag_score(length) > 0:
                        sort_value = self.sts_daily_test[symbol].get_zigzag_score(length)
                    self._attribute_table.loc[symbol, "Sort"] = sort_value
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > cutoff]
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=False)
                print("# {:>5} symbols meet filter_consolidation_p criteria".format(len(self._attribute_table)))
#                 print(self._attribute_table['Sort']) #xxx

            # method filter based on stochastic signal
            if self.kwargs["filter_stochastic_sgl"]:
                # filter for oversold (d < cutoff) tickers with stochastic K > D and
                # bullish price action (paction < cutoff)
                # input string: stochastic long term,
                #               stochastic short term,
                #               stochastic d cutoff,
                #               k>d ('all') or k just cross d up ('crs' or any string)

                arg = self.kwargs["filter_stochastic_sgl"]
                try:
                    (n, m, cutoff, mode) = arg.split(',')
                    n = int(n)
                    m = int(m)
                    cutoff = float(cutoff)
                except:
                    e = sys.exc_info()[0]
                    print("x-> invalid stochastic argument input ", e)
                    sys.exit(1)

                for symbol in self._attribute_table.index:
                    (k, d, cross, bullish) = self.sts_daily_test[symbol].stochastic_cross(n, m)
                    status = True
                    if k > cutoff + 15 or d > cutoff:
                        status = False
                    if mode == 'all':
                        if k < d: status = False
                    elif cross <= 0:
                        status = False
                    if not status:
                        self._attribute_table.drop(symbol, inplace=True)
                print("# {:>5} symbols meet stochastic criteria {}".format(len(self._attribute_table)), )

            if self.kwargs["filter_parallel_ema"]:
                # Query EMA sandwiched between short and long EMAs for recent period
                #
                # Args:
                #   query (int): length in days to define query EMA.
                #   short (int): length in days to define short EMA.
                #   long (int): length in days to define long EMA.
                #   days (int): period to assess if middle EMA is sandwich between short/long EMAs.
                #       if not provided, assess only the last for EMA formation
                #   ratio (int): minimal percentage of days meeting the EMA formation

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
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].two_dragon(*array2)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > 0]

                print("# {:>5} symbols meet filter_parallel_ema criteria {}".format(len(self._attribute_table), args))

            if self.kwargs["filter_ema_3layers"]:
                args = self.kwargs["filter_ema_3layers"]
                array = args.split(',')
                days = 0
                cutoff = 0.85
                if len(array) == 3:
                    try:
                        (query, short, long) = list(map(int, array))
                    except ValueError:
                        raise
                elif len(array) == 5:
                    try:
                        (query, short, long, days) = list(map(int, array[:4]))
                        cutoff = float(array[-1])
                    except ValueError:
                        raise
                else:
                    print("Invalid argument {args}")

                self._attribute_table["Sort"] = False
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].ema_3layers(query, short, long,
                                                                                                   days, cutoff)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"]]
                print("# {:>5} symbols meet filter_hit_ema_support {}".format(len(self._attribute_table), args))

            if self.kwargs["filter_hit_ema_support"]:
                args = self.kwargs["filter_hit_ema_support"]
                array = args.split(',')
                try:
                    (ema, days) = list(map(int, array))
                except ValueError:
                    raise

                self._attribute_table["Sort"] = False
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].hit_ema_support(ema, days)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"]]
                print("# {:>5} symbols meet filter_hit_ema_support {}".format(len(self._attribute_table), args))

            # method filter and sort by last close to bollinger band bottom border distance
            if self.kwargs["filter_bbdistance"]:
                filter_bbdistance = self.kwargs["filter_bbdistance"]
                list_arg = filter_bbdistance.split(',')
                cutoff = float(list_arg[0])
                days = 1
                test_bband_uptrend = False
                if len(list_arg) >= 2:
                    days = int(list_arg[1])
                if len(list_arg) == 3 and list_arg[2] == 'up':
                    test_bband_uptrend = True

                self._attribute_table["Sort"] = 0
                for symbol, row in self._attribute_table.iterrows():
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].get_BBdistance(days)
                    df = self.sts_daily_test[symbol].df
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
                print("# {:>5} symbols meet bollinger band distance criteria {}".
                      format(len(self._attribute_table), filter_bbdistance))


            if self.kwargs["sort_rsi_std"]:
                arg = self.kwargs["sort_rsi_std"]
                period = 20
                cutoff = 10
                if ',' in arg:
                    alist = arg.split(',')
                    period = int(alist[0])
                    cutoff = float(alist[1])
                else:
                    period = int(arg)

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].get_consolidation(period)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] <= cutoff]
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=True)
                print("# {:>5} symbols meet sort_rsi_std requirement: {}".format(len(self._attribute_table), arg))

            if self.kwargs["sort_ema_attraction"]:
                arg = self.kwargs["sort_ema_attraction"]
                ema_len = 50
                period = 10
                if ',' in arg:
                    alist = arg.split(',')
                    ema_len = int(alist[0])
                    period = int(alist[1])
                else:
                    print(f"Invalid sort_ema_attraction argument {arg}")
                    exit(1)

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].ema_attraction(ema_len, period)
                # self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] <= cutoff]
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=True)
                print(self._attribute_table["Sort"])
                print("# {:>5} symbols meet sort_ema_attraction requirement: {}".format(len(self._attribute_table), arg))
                
            if self.kwargs["sort_ema_entanglement"]:
                arg = self.kwargs["sort_ema_entanglement"]
                try:
                    args = arg.split(",")
                    ema_fast = int(args[0])
                    ema_slow = int(args[1])
                    span = int(args[2])
                    cutoff = int(args[3])
                except:                 
                    print(f"Invalid sort_ema_entanglement argument {arg}")
                    exit(1)

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].ema_entanglement(ema_fast, ema_slow, span)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] >= cutoff]
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=False)
                print("# {:>5} symbols meet sort_ema_entanglement requirement: {}".format(len(self._attribute_table), arg))
                    
            if self.kwargs["filter_upward"]:
                filter_upward = self.kwargs["filter_upward"]
                args = filter_upward.split(',')

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].in_uptrend(*args)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] > 0]
                print("# {:>5} symbols meet filter_upward criteria {}".
                      format(len(self._attribute_table), filter_upward))

            if self.kwargs["filter_horizon_slice"]:
                try:
                    args = self.kwargs["filter_horizon_slice"].split(',')
                    days, num = list(map(int, args))
                except ValueError:
                    print(f" argument {args} is invalid")
                    exit(1)

                self._attribute_table["Sort"] = False
                for symbol in self._attribute_table.index:
                    pivot_caught = self.sts_daily_test[symbol].horizon_slice(days)
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
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].ema_slice(filter_ema_slice)

                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"]]
                print("# {:>5} symbols meet EMA slice criteria: {}"
                      .format(len(self._attribute_table), filter_ema_slice))

            if self.kwargs["filter_hit_horizontal_support"]:
                try:
                    args = self.kwargs["filter_hit_horizontal_support"]
                    days, length, num = list(map(int, args.split(',')))
                except ValueError:
                    print(f" argument {args} is invalid")
                    exit(1)

                self._attribute_table["Sort"] = False
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] \
                        = self.sts_daily_test[symbol].hit_horizontal_support(days, length, num)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"]]
                print("# {:>5} symbols meet support slice criteria: {}".format(len(self._attribute_table), args))

            if self.kwargs["filter_hit_horizontal_resistance"]:
                try:
                    args = self.kwargs["filter_hit_horizontal_resistance"]
                    days, length, num = list(map(int, args.split(',')))
                except ValueError:
                    print(f" argument {args} is invalid")
                    exit(1)

                self._attribute_table["Sort"] = False
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] \
                        = self.sts_daily_test[symbol].hit_horizontal_support(days, length, num, touch_down=False)
                self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"]]
                print("# {:>5} symbols meet support slice criteria: {}".format(len(self._attribute_table), args))


            if self.kwargs["sort_ema_distance"] > 0:
                # sort symbols by last close-to-SMA distance

                sort_ema_distance = self.kwargs["sort_ema_distance"]

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = self.sts_daily_test[symbol].get_SMAdistance(
                        sort_ema_distance)
                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=True)

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
                        self.sts_daily_test[symbol].get_referenced_change(reference, subject)

                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=True)
                self._attribute_table["Date Added"] = reference
                if subject.count('-') == 2:
                    self._attribute_table["Date Sold"] = subject

            if self.kwargs["sort_performance"]:
                arg = self.kwargs["sort_performance"]
                days = 0
                ref = ''
                ref_performance = 0
                cut = -1
                if ',' in arg:
                    args = arg.split(",")
                    days = int(args[0])
                    cut = float(args[1])
                    if len(args) == 3:
                        ref = args[2]
                else:
                    try:
                        days = int(arg)
                    except:
                        print("Invalid sort_performance argument: {}".format(arg))
                        exit(0)

                if ref:
                    try:
                        ref_performance = self.sts_daily_test[ref].get_latest_performance(days)
                        print("spy", ref_performance)
                    except:
                        print("Error in getting performance data for {}".format(ref))
                        exit(0)

                self._attribute_table["Sort"] = 0
                for symbol in self._attribute_table.index:
                    self._attribute_table.loc[symbol, "Sort"] = \
                        self.sts_daily_test[symbol].get_latest_performance(days, ref_performance)

                self._attribute_table = self._attribute_table.sort_values(["Sort"], ascending=False)
                if -1 < cut < 10:
                    self._attribute_table = self._attribute_table.loc[self._attribute_table["Sort"] >= cut]
                # get symbols with top sort scores ???
                elif cut > 100:
                    cut = int (cut/100)
                    self._attribute_table = self._attribute_table.head(cut)

                print("# {:>5} symbols meet sort_performance criteria {}".
                      format(len(self._attribute_table), arg))

                # print( self._attribute_table["Sort"] )
