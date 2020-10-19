#!/usr/bin/env python3
"""
Sort, filter and chart lists of price time series data
"""

import os
import sys
import numpy as np
import pandas as pd
import module.utility as utility
import module.arguments as arguments
import module.candlestick as candlestick
from module.time_series_plus import TimeSeriesPlus
from module.attribute_table import AttributeTable


def make_image_file(file_name, securities, count, panel_row, panel_col,
                    to_be_recycled, day_span=200, gradient=9, fig_wid=40,
                    fig_dep=24, dual_scale=False, draw_by_row=False):
    """Create one image file containing plots for all input securities

    Args:
        file_name (str): a path to file containing the list of input securities
        securities (list): a list of security objects to be plotted together
        count (int): a unique number to tag the output image name
        panel_row (int): number of rows the image is divided into
        panel_col (int): number of columns the image is divided into
        to_be_recycled (list): a list (of security objects) to be extended
        day_span (int): number of days' data to be plotted
        gradient (int): the expansion of candlestick width from the first day to the last day plotted
        fig_wid (float): width of the output image
        fig_dep (float): depth of the output image
        dual_scale (boolean): whether to plot each security for a second time (with different span?)
        draw_by_row (boolean): draw figures row by row. Column by column by default

    Returns:
        to_be_recycled (list): a list of security objects
    """

    # figure out a name for the output image
    file_name = os.path.basename(file_name)
    output = "chart." + file_name + f".{day_span}d." \
             + str(count)[1:] + "i" + ".pdf"

    # create output image with one or multiple figures
    recycle = candlestick.draw_many_candlesticks(securities, output, panel_row, panel_col,
                                                 fig_wid, fig_dep, day_span, gradient, draw_by_row)
    securities.clear()

    return to_be_recycled.extend(recycle)


def attributes_to_securities(tickers, use_volume=False):
    """Get dictionary of securities from AttributeTable object

    Args:
        tickers (AttributeTable object): contains a list of securities and their attributes
        use_volume (boolean): add trading volume data or not

    Returns:
        dict: key (security symbol and head info) -> value (a Security object)
    """
    security_table = tickers.get_attribute_table()
    timeseries_dict = tickers.get_dict_timeseries()

    # Loop through security table and populate a dictionary of securities
    securities = {}
    count = 100000
    for sticker, row in security_table.iterrows():
        count += 1
        if sticker in timeseries_dict:
            # Get daily price time series data and do modifications
            sts = timeseries_dict[sticker]
            daily_price = sts.df
            # Remove price data for the most recent period
            if LAST_REMOVED_ROWS:
                row_num = daily_price.shape[0]
                if row_num <= LAST_REMOVED_ROWS + 100:
                    continue
                else:
                    daily_price = daily_price.head(row_num - LAST_REMOVED_ROWS)
            # Add volume data
            if use_volume: daily_price = TimeSeriesPlus(daily_price).get_volume().df

            # Create security object and add features
            my_security = candlestick.Security(daily_price)
            if row['annotation']:
                my_security.set_annotation(row['annotation'])
            if "Date Added" in row:
                date = row["Date Added"]
                my_security.set_date_added(date)
            if "Date Sold" in row:
                date = row["Date Sold"]
                if date and date != "na" and date != "NA":
                    my_security.set_date_sold(utility.fix_date_added(date))
            if "exit Price" in row:
                my_security.set_exit_price(row["exit Price"])
            if "Industry" in row:
                my_security.set_industry(row["Industry"])
            if "Sort" in row:
                my_security.set_sortvalue(row["Sort"])

            # Make figure head (as key in dict)
            rsi = str(sts.get_rsi(14))[0:4]
            my_key = f"{sticker}: {row['header']} RSI-{rsi}"
            if 'PL' in row:
                r = float(row['PL'])
                my_security.set_profit_loss(r)
                if r > 0:
                    r = '+' + str(round(r, 1))
                else:
                    r = str(round(r, 1))
                my_key = my_key + ' ' + r + 'risk'

            securities[my_key] = my_security

    return securities


def chart_securities(file, **kwargs):
    """Chart a list of securities included in input file

    Args:
        file (str): path to a text input file with rows representing securities and columns representing attributes
        kwargs (dict): command line key word arguments
    """

    # Basic variables
    fig_wid = 42
    fig_dep = 24
    day_span = kwargs["days"]
    gradient = kwargs["gradient"]
    backtest_date = kwargs['backtest_date']
    default_row_num = kwargs['row_number']

    # Read security list
    df = pd.read_csv(file, sep="\t")
    num_stickers = df.shape[0]
    print(f"#->{num_stickers:>4} securities in ", end="")

    # Make output file name
    file_name = os.path.basename(file)
    file_name = utility.file_name_rstrip(file_name)
    if file_name:
        print(file_name)
        file_name = utility.get_output_filename(file_name, **kwargs)
        if backtest_date:
            file_name = backtest_date + '.' + file_name

    # Set the number of rows and columns within each output image based on
    # the total number of input securities and charting related argument
    if "," in day_span:
        default_row_num = 4
    panel_row = candlestick.set_row_num(num_stickers)
    panel_row = default_row_num if panel_row > default_row_num else panel_row
    panel_col = panel_row
    if ',' in day_span:
        panel_col = int((panel_col + 1) / 2)
    num_pic_per_file = panel_col * panel_row

    if default_row_num == 1:
        fig_wid = 10
        fig_dep = 6

    # Securities to be re-charted in different scale (not implemented yet)
    to_be_recycled = []

    # Filter and sort securities
    tickers = AttributeTable(df, directory, kwargs)
    tickers.work()
    df = tickers.get_attribute_table()
    # If not sorted, then sort by symbol
    if "Sort" in df:
        unique_sort_value = len(df["Sort"].unique())
        if unique_sort_value == 1:
            df = df.sort_index()

    # Export filtered/sorted security table
    # df.to_csv("temp.PL.txt", sep="\t")
    if 'PL' in df.columns:
        summarize_profit_loss(df['PL'])

    if kwargs["filterOnly"]:
        # Write processed dataframe to a local file
        df.to_csv(file_name + ".tsv", sep="\t")
    else:
        # Plot multi-panel figure while going through a dictionary of security objects
        securities = attributes_to_securities(tickers, use_volume=kwargs["plot_volumne"])
        print(f"# {len(securities):>5} data to plot")
        num_to_plot = len(securities) if len(securities) > 0 else 0

        if num_to_plot:
            security_batch = {}
            c = 10000

            # Make one image for every certain number of securities
            for key, security in securities.items():
                c += 1
                security_batch[key] = security
                if len(security_batch) % num_pic_per_file == 0:
                    # Create one output file for every 'num_to_plot' securities
                    make_image_file(file_name, security_batch, c, panel_row, panel_col, to_be_recycled,
                                    day_span, gradient, fig_wid, fig_dep)
                    security_batch = {}

            # Make one image for remaining securities
            if len(security_batch) > 0:
                make_image_file(file_name, security_batch, c, panel_row, panel_col, to_be_recycled,
                                day_span, gradient, fig_wid, fig_dep)


def summarize_profit_loss(series):
    """Summarize profit and loss record

    Args:
        series (pandas series object): filled floats representing profits and losses [in R(risk)]
    """
    win = np.where(series > 0.3, 1, 0).sum()
    loss = np.where(series < -0.3, 1, 0).sum()
    even = np.where((series >= -0.3) & (series <= 0.3), 1, 0).sum()
    r_total = series.sum()
    total_trade = win + loss + even

    win_rate = 'NA'
    if total_trade > 0:
        win_rate = round(win / total_trade, 3)
    print("Profit&Loss\t{}\t{}\t{}\t{}\t{}\t{}".format(win, loss, even, total_trade,
                                                       win_rate, round(r_total, 3)))


if __name__ == "__main__":

    LAST_REMOVED_ROWS = 0

    # argument parser
    parser = arguments.get_parser()
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr);
        sys.exit(1)
    args = parser.parse_args()

    # main code
    directory = args.dir
    for file in args.list:
        chart_securities(file, **vars(args))
