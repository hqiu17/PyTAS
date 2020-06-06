#!/usr/bin/env python3
"""

"""

import os
import re
import sys
import numpy as np
import pandas as pd
import module.utility as utility
import module.arguments as arguments
import module.candlestick as candlestick
from module.time_series_plus import TimeSeriesPlus
from module.attribute_table import AttributeTable
import argparse

def make_image_file(file_name, securities, count, panel_row, panel_col,
                    to_be_recycled, dayspan=200, gradient=9, fig_wid=40,
                    fig_dep=24, dualscale=False, drawbyrow=False):
    # create an image file containing plots for all input securities

    file_name = os.path.basename(file_name)
    output = "chart." + file_name + f".{dayspan}d." \
             + str(count)[1:] + "i" + ".pdf"
    recycle = candlestick.draw_many_candlesticks(securities, output,
                                                 panel_row, panel_col,
                                                 fig_wid, fig_dep,
                                                 dayspan, gradient,
                                                 drawbyrow)
    securities.clear()
    to_be_recycled.extend(recycle)


def chart_securities(file, **kwargs):
    #
    # Chart a list of securities included in the input file
    #
    # Argument:
    #     file (str): location of text input file with each row
    #         representing a security and each column representing
    #         for an attribute of securities
    #     kwargs : a list of user input key word arguments

    fig_wid = 42
    fig_dep = 24
    dayspan = kwargs["days"]
    gradient = kwargs["gradient"]
    weekly = kwargs['weekly']
    backtest_date = kwargs['backtest_date']

    # Basic processing the security data based on descriptive attributes

    df = pd.read_csv(file, sep="\t")

    num_stickers = df.shape[0]
    print (f"#->{num_stickers:>4} securities in ", end="")

    file_name = os.path.basename(file)
    file_name = utility.file_name_rstrip(file_name)
    if file_name:
        print(file_name)
        file_name = utility.get_output_filename(file_name, **kwargs)
        if backtest_date:
            file_name = backtest_date + '.' + file_name

    # set the number of rows and columns within each output chart based on
    # the total number of input securities and charting related argument (-p)
    default_row_num = 4 if "," in dayspan else 5
    panel_row = candlestick.set_row_num(num_stickers)
    panel_row = default_row_num if panel_row > default_row_num else panel_row
    panel_col=panel_row
    if ',' in dayspan: panel_col = int((panel_col+1)/2)
    num_pic_per_file = panel_col * panel_row

    if default_row_num == 1:
        fig_wid = 10
        fig_dep = 6

    # securities to be charted in different scale
    # (not implemented yet)
    to_be_recycled = []

    # filter and sort securities
    tickers = AttributeTable(df, directory, kwargs)
    tickers.work()
    df = tickers.get_attribute_table()



    # check for SPY data and add it to dataframe as background
    spy = directory+"/"+"SPY"+".txt"
    ref = get_benchmark(spy, LAST_REMOVED_ROWS)

    # loop through filtered symbol table and collect securities
    securities = {}
    count = 1000
    #securities_filtered = pd.DataFrame()

    # loop through security list, create Security instances
    # and load into a dictionary
    for sticker, row in df.iterrows():
        count+=1
        note = row['header']
        antt = row['annotation']

        sts_daily = tickers.sts_daily
        if sticker in sts_daily:
            sts = sts_daily[sticker]
            daily_price = sts.df

            if LAST_REMOVED_ROWS:
                row_num = daily_price.shape[0]
                if row_num <= LAST_REMOVED_ROWS + 100:
                    continue
                else:
                    daily_price = daily_price.head(row_num-LAST_REMOVED_ROWS)

            rsi = str( sts.get_rsi(14))[0:4]

            # if kwargs["weekly_chart"]:
            #     print(ref.head(5))
            #     ref = TimeSeriesPlus(ref).get_weekly()
            #     ref = TimeSeriesPlus(ref).sma_multiple().df
            # else:
            #     if len(ref) > 30:
            #         daily_price = daily_price.join(ref)
            # daily_price=daily_price.tail(500)

            if kwargs["plot_volumne"]:
                daily_price = TimeSeriesPlus(daily_price).get_volume().df

            mysecurity = candlestick.Security(daily_price)

            if antt:
                mysecurity.set_annotation(antt)
            if "Date Added" in row:
                date = row["Date Added"]
                mysecurity.set_date_added(date)
            if "Date Sold" in row:
                date = row["Date Sold"]
                if date and date != "na" and date != "NA":
                    mysecurity.set_date_sold(utility.fix_date_added(date))
            if "Industry" in row:
                mysecurity.set_industry(row["Industry"])

            if "Sort" in row:
                mysecurity.set_sortvalue(row["Sort"])

            securities[f"{sticker}: {note} RSI-{rsi}"] = mysecurity

    # write processed dataframe to local file
    if kwargs["filterOnly"]:
        df.to_csv(file_name+".tsv", sep="\t")
    # plot multi-panel figure while going through a dictionary of
    # Security instances
    else:
        print(f"# {len(securities):>5} data to plot")
        num_to_plot = len(securities) if len(securities) > 0 else 0

        if num_to_plot:
            security_batch = {}
            c = 1000
            for key, security in securities.items():
                c += 1
                security_batch[key] = security
                if len(security_batch) % num_pic_per_file == 0:
                    # create one output file for every 'num_to_plot' securities
                    make_image_file(file_name, security_batch, c,
                                 panel_row, panel_col, to_be_recycled,
                                 dayspan, gradient, fig_wid, fig_dep)
                    security_batch = {}
            if len(security_batch) > 0:
                # create one output file for remaining securities
                make_image_file(file_name, security_batch, c,
                             panel_row, panel_col, to_be_recycled,
                             dayspan, gradient, fig_wid, fig_dep)


def get_benchmark(file, remove_recent=0):
    """Make a dataframe for long period

    Args:
        file (path): file location of timeseries data
        remove_recent (int): number of recent days to ignore

    Returns:
        dataframe: dataframe contains 2 columns: 1) 'weather', daily
            change (relative to prior day's closing); 2) 'long', if
            closing is greater than 20MA or not.
    """
    ref = pd.DataFrame()
    if os.path.exists(file):
        try:
            mydf = pd.read_csv(file, sep="\t", parse_dates=['date'], index_col=['date'])
        except ValueError:
            mydf = pd.read_csv(file, sep="\t", parse_dates=['Date'], index_col=['Date'])
            mydf['4. close'] = mydf['Close']
        except:
            e = sys.exc_info()[0]
            print("x-> Error while reading historical data; ", e)
        mydf = mydf.sort_index(axis=0)

        # find go-long period
        mydf = candlestick.add_moving_averages(mydf)
        mydf['last-20MA'] = mydf['4. close'] - mydf['20MA']
        mydf['long'] = np.where(mydf['last-20MA']>0, 1, 0)
        mydf["close_shift1"] = mydf["4. close"].shift(periods=1)
        mydf["weather"] = (mydf["4. close"]-mydf["close_shift1"])/mydf["close_shift1"]

        row_num = mydf.shape[0]

        # if LAST_REMOVED_ROWS and row_num > LAST_REMOVED_ROWS + 100:
        if remove_recent and row_num > (remove_recent + 100):
            mydf = mydf.head(row_num-LAST_REMOVED_ROWS)

        # turn a series into dataframe (for record)
        ref = pd.DataFrame(mydf["weather"], index=mydf.index)
        ref['long'] = mydf['long']

    return ref


if __name__ == "__main__":

    LAST_REMOVED_ROWS = 0
    FIGWIDTH = 42
    FIGDEPTH = 24

    # argument parser
    parser = arguments.get_parser()
    if len(sys.argv)==1:
        parser.print_help(sys.stderr); sys.exit(1)
    args=parser.parse_args()

    # main code
    directory = args.dir
    for file in args.list:
        chart_securities(file, **vars(args))
