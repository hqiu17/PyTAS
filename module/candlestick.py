"""
Security class and methods for candlestick
"""

import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from module.time_series_plus import TimeSeriesPlus

moving_average_parameters = [2, 10, 20, 50, 100, 200]


class Security:
    """A class bundling timeseries data with security attributes
    """

    def __init__(self, df):
        """Initializer

        Args (df): timeseries price data
        """
        self.df = df.copy(deep=True)
        self.note = ""
        self.date_added = ""
        self.date_sold = ""
        self.industry = ""
        self.annotation = ""
        self.sortvalue = ""
        self.exit_price = ""
        self.profit_loss = ""

    def set_date_added(self, date):
        self.date_added = date

    def set_date_sold(self, date):
        self.date_sold = date

    def set_exit_price(self, price):
        self.exit_price = price

    def set_note(self, note):
        self.note = note

    def set_industry(self, industry):
        self.industry = industry

    def set_annotation(self, annotation):
        self.annotation = annotation

    def set_sortvalue(self, sortvalue):
        self.sortvalue = sortvalue

    def set_profit_loss(self, profit_loss):
        self.profit_loss = profit_loss

    def get_price(self):
        return self.df.copy(deep=True)

    def get_date_added(self):
        return self.date_added

    def get_date_sold(self):
        return self.date_sold

    def get_note(self):
        return self.note

    def get_industry(self):
        return self.industry

    def get_annotation(self):
        return self.annotation

    def get_sortvalue(self):
        return self.sortvalue

    def get_exit_price(self):
        return self.exit_price


def candlestick_gradient_width(df, ratio=10):
    """Set width gradient and update coordination for candlesticks

        Given a dataframe, this method add below columns
        1) "xcord": scaled candlestick x-axis coordinates
        2) "width": scaled candlestick width
        3) "color": daily change color (green or red)
        4) "Date close" transaction date for each row
        5) set index using "xcord" column

    Args:
        df: (dataframe): df containing price timeseries data
        ratio (int): the ratio of candlestick width (the last day / the
            earliest day)

    Returns
        df: (dataframe): df with additional colmns and altered index
    """

    df = df.copy(deep=True)

    # figure out the maximum/minimum of x axis
    sample_size = len(df.index)
    fig_xmin = 0
    fig_xmax = sample_size

    # figure out asceding gradient "alpha" of bar width over time
    alpha = ratio ** (1 / (sample_size - 1))
    total_bar_width = 1
    bar_width = 1
    for i in range(1, sample_size):
        bar_width = bar_width * alpha
        total_bar_width += bar_width
        i += 1
    # actual width of bar for day #1
    bar1_width = (fig_xmax - fig_xmin) / total_bar_width

    # iterate through days and apply alpha
    bar_xcord = []
    bar_width = []
    bar_color = []

    right_edge = 0
    width_bar = bar1_width
    count = 0
    for date, data in df.iterrows():

        right_edge += width_bar
        # price open, close, high, an low information
        price_range = abs(data["2. high"] - data["3. low"])
        try:
            body_low = np.minimum(data["1. open"], data["4. close"])
        except:
            body_low = ''
        body_range = abs((data["1. open"] - data["4. close"]))
        if body_range < 0.01:
            body_range = 0.01
        if price_range < 0.01:
            price_range = 0.01
        # set color
        color = "red"
        if not body_low:
            color = 'yellow'
        elif data["1. open"] == body_low:
            color = "green"

        bar_width.append(width_bar)
        bar_xcord.append(right_edge - width_bar / 2)
        bar_color.append(color)

        width_bar = width_bar * alpha
        count += 1

    df["xcord"] = pd.Series(bar_xcord, index=df.index)
    df["width"] = pd.Series(bar_width, index=df.index)
    df["color"] = pd.Series(bar_color, index=df.index)
    df['Date close'] = df.index
    df['index'] = df['xcord']
    df = df.set_index("index")
    return df


def date_to_index(date, series):
    """Get index number for a given target date
        If the given target date is not a trading day, a new target day will be assigned as
        the closet trading day before the input date.

    Args:
        date (str): date (eg, 2020-20-20)
        series (pandas series): series containing a list of dates
    """

    date_close = pd.to_datetime(series).copy(deep=True)
    date_series = pd.Series(date, index=series.index)
    date_series = pd.to_datetime(date_series).copy(deep=True)

    # Get index for days after target days and turn their corresponding value to minus 200
    difference = (date_close - date_series).dt.days
    daysAfterAddtion = difference > 0
    myseries = difference.copy(deep=True)
    myseries[daysAfterAddtion] = -200

    # The day with the largest value is the target or its
    return myseries.values.argmax()


def date_to_xy(date, df):
    """Get x- and y- coordinates for the closing of a trading day in a plot

    Args:
        date (str): date (eg, 2020-20-20)
        df (pandas dataframe): time series data containing price data

    Returns:
        x (int): index of the input date in dataframe
        y (float): closing price of the input date
    """

    x = date_to_index(date, df['Date close'])
    y = df.iloc[x]['4. close']

    return x, y


def draw_a_candlestick(ax, df, sticker="", fold_change_cutoff=3,
                       date_added="", date_sold="", exit_price='',
                       industry="", annotation="", sort="", pl=0):
    """Draw a plot for a security

    Args:
        ax (ax) : ???
        df (pandas dataframe): dataframe containing time series price data
        sticker (str): a string to be used as figure head
        fold_change_cutoff (float): If price decrease larger than the cutoff, re-draw signal is to be emitted
        date_added (str): date when security is bought (eg, 2020-20-20)
        date_sold (str): date when security is sold (eg, 2020-20-20)
        exit_price (string): a series of prices connected with '#'. These prices include stop loss, entry, exit in backtest.
        industry (str): the industry the security belongs to (to be added to the bottom left of figure)
        annotation (str): addition info about the security (to be added beneath figure head)
        sort (float): the parameter used to sort multiple security (this value is added beneath annotation)
        pl (float): profit or loss

    Returns
        redraw (int): If meet draw requirement, return 1. Otherwise, return 0.
    """
    redraw = 0
    # print (df0)
    # df = df0  # .copy(deep=True)

    # Figure out the maximum/minimum of x/y axis
    sample_size = len(df.index)
    fig_ymin = df.min(axis=0)["3. low"]
    fig_ymax = df.max(axis=0)["2. high"]
    fig_xmin = 0
    fig_xmax = sample_size
    
    # Market benchmark data is available, re-adjust x/y range 
    if "weather" in df.columns:
        fig_ymax = fig_ymax + (fig_ymax - fig_ymin) * 0.0526

    # Initialize plot
    plt.xlim(fig_xmin, fig_xmax)
    plt.ylim(fig_ymin, fig_ymax)

    # Emmit re-draw signal if dramatic price change occurred within the length of data
    fold_change = fig_ymax / df["4. close"].iloc[-1]
    if fold_change > fold_change_cutoff:
        redraw = 1

    # Draw last day's trading zone (to highlight pivots)
    if "last_trading_range" in df.columns:
        try:
            (lw_lim, up_lim) = list(map(float, df.iloc[-1]["last_trading_range"].split(',')))
        except ValueError:
            print ("x-> Error in parsing last_trading_range")
            print (ValueError)

        plt.axhspan(lw_lim, up_lim, color="gray", alpha=0.3)

    # Plot year by year vertical lines
    # if sample_size > 480:
    #     plt.axvspan(df.index[-480],df.index[-241],color="grey", alpha=0.1)
    # elif sample_size > 240:
    #     plt.axvspan(df.index[0],df.index[-241],color="grey", alpha=0.1)
    # if sample_size > 80 and sample_size < 240:
    #     plt.axvspan(df.index[-80],df.index[-60],color="grey", alpha=0.1)
    # if sample_size > 40 and sample_size < 240:
    #     plt.axvspan(df.index[-40],df.index[-20],color="grey", alpha=0.1)

    # Plot important events
    # # plot 2018 dip / trade war
    # index1 = date_to_index(pd.to_datetime("2018-12-26 00:00:00"), df['Date close'])
    # index2 = date_to_index(pd.to_datetime("2018-10-4 00:00:00"), df['Date close'])
    # plt.axvspan(df.index[index1], df.index[index2], color="orange", alpha=0.1)
    #
    # # plot 2019 May dip / trade war
    # index1 = date_to_index(pd.to_datetime("2019-5-1 00:00:00"), df['Date close'])
    # index2 = date_to_index(pd.to_datetime("2019-6-3 00:00:00"), df['Date close'])
    # plt.axvspan(df.index[index1], df.index[index2], color="orange", alpha=0.1)
    #
    # # plot 2019 July dip / trade war
    # index1 = date_to_index(pd.to_datetime("2019-7-31 00:00:00"), df['Date close'])
    # index2 = date_to_index(pd.to_datetime("2019-8-27"), df['Date close'])
    # plt.axvspan(df.index[index1], df.index[index2], color="orange", alpha=0.1)
    # # plot 2019 July dip / trade war
    # index1 = date_to_index(pd.to_datetime("2019-9-20"), df['Date close'])
    # index2 = date_to_index(pd.to_datetime("2019-10-8"), df['Date close'])
    # plt.axvspan(df.index[index1], df.index[index2], color="orange", alpha=0.1)

    # Add buy/sell points
    y_buy = 0
    y_sell = 0
    if date_added:
        x, y = date_to_xy(date_added, df)
        y_buy = y
        plt.axvline(x=x, color="blue", dashes=[5, 10], linewidth=1)
        plt.axhline(y=y, color="blue", dashes=[5, 10], linewidth=1)
    if date_sold:
        x, y = date_to_xy(date_sold, df)
        y_sell = y
        plt.axvline(x=x, color="orange", dashes=[5, 10], linewidth=1)
        plt.axhline(y=y, color="orange", dashes=[5, 10], linewidth=1)

    # Plot profit/loss range
    color = 'yellow'
    pl_red = False
    # Add horizontal lines for stop loss, entry, exit and other prices differ from them by Rs
    if exit_price:
        prices = [float(a) for a in exit_price.split('#')]
        for p in prices:
            p = float(p)
            plt.axhline(y=p, color="grey", linewidth=1)
        y_buy = prices[1]
        y_sell = prices[-1]
    # Add colored background for profit (green) & loss (red)
    if y_buy and y_sell:
        # if y_buy * 0.97 >= y_sell:
        if pl < 0:
            color = 'red'
            # print('PL2color', y_buy, y_sell, 'redLoss')
            plt.axhspan(y_sell, y_buy, color=color, alpha=0.3)
            pl_red = True
        elif pl > 0:
            color = 'green'
            # print('PL2color', y_buy, y_sell, color)
            plt.axhspan(y_buy, y_sell, color=color, alpha=0.3)
            pl_red = True
        else:
            # print('PL2color', y_buy, y_sell, color)
            plt.axhspan(y_buy, y_sell, color=color, alpha=0.3)
            pl_red = True

    # If no horizontal lines are made for trading profit & loss, add horizontal lines
    # for last day's trading open and close
    if not pl_red:
        color_closing = "black"
        if df.iloc[-1]["4. close"] > df.iloc[-1]["1. open"]:
            color_closing = "green"
        elif df.iloc[-1]["4. close"] < df.iloc[-1]["1. open"]:
            color_closing = "red"
        plt.axhline(y=df.iloc[-1]["1. open"], color=color_closing, linewidth=0.2)
        plt.axhline(y=df.iloc[-1]["4. close"], color=color_closing, linewidth=0.2)
        plt.axhspan(df.iloc[-1]["1. open"], df.iloc[-1]["4. close"], color=color_closing, alpha=0.3)

    # Plot closing price
    df["4. close"].plot(color='black')

    alpha = 0.8
    
    # Add volume plot
    if 'vol' in df.columns:
        df['vol'] = df['vol'] + 100 # eliminate zero volume
        
        # Normalize volume data so it overlap well with price plot
        ratio = (fig_ymax - fig_ymin)/(df['vol'].max() - df['vol'].min())
        df['vol_adjusted'] = df['vol'] * ratio
        base = df['vol_adjusted'].min() - fig_ymin
        df['vol_adjusted'] = (df['vol_adjusted'] - base)
        
        # Do plot
        df['vol_adjusted'].plot(color="blue", alpha=alpha/2)
        
        # make trend lines and bollinger band lighter
        alpha = alpha/3

    # Add SMA and bollinger band
    if sample_size > 50:
        for days in moving_average_parameters[1:]:
            ma = str(days) + "MA"
            if ma in df:
                df[ma].plot(alpha=alpha/2)

        if sample_size <= 60:
            if 'BB20u' in df and 'BB20d' in df:
                df['BB20u'].plot(color='#1f77b4', alpha=alpha)
                df['BB20d'].plot(color='#1f77b4', alpha=alpha)
                plt.fill_between(df.index, df['BB20u'], df['BB20d'], color='blue', alpha=alpha/5)
             # pandas plot's default color
             #    >>> prop_cycle = plt.rcParams['axes.prop_cycle']
             #    >>> prop_cycle.by_key()['color']
             #    ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
             #     '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            if 'BB20d_SMA10' in df:
                df['BB20d_SMA10'].plot()

    # Add pivot
    if 'pivot' in df.columns:
        pivot = df.copy(deep=True)
        pivot = pivot[pivot['pivot']>0]
        plt.plot(pivot['xcord'],pivot['pivot'], 
                 linestyle='-', marker='o', markersize=6, color='#1f77b4', linewidth=2)

    # Plot candlesticks (core data) for the most recent period
    recent_days = 60
    if 15 < df.shape[0] <= 120:
        df_recent = df.tail(recent_days)
        for num, data in df_recent.iterrows():
            price_low = data["3. low"]
            price_range = data["2. high"] - data["3. low"]
            body_low = np.minimum(data["1. open"], data["4. close"])
            body_range = abs((data["1. open"] - data["4. close"]))
            if body_range < 0.01:
                body_range = 0.01
            if price_range < 0.01:
                price_range = 0.01

            # Plot volume
            if 'vol_adjusted' in df.columns:
                # plt.bar(data["xcord"], data['vol_adjusted'], data["width"], bottom=df_recent['vol_adjusted'].min(), color='yellow', alpha=0.4)
                plt.bar(data["xcord"], data['vol_adjusted'], data["width"],
                        color='yellow', alpha=0.4)

            # Plot day open and day close
            plt.bar(data["xcord"], body_range, data["width"], bottom=body_low, color=data["color"])
            # Plot day high and day low
            if sample_size < 360:
                plt.bar(data["xcord"], price_range, data["width"]/5, bottom=price_low, color=data["color"])
                

            # # plot market benchmark data S&P500
            # if sample_size < 200 and "weather" in df.columns:
            #     mchange = data["weather"]
            #     mycolor = "yellow"
            #     if mchange > 0:
            #         mycolor = "green"
            #         height = (fig_ymax - fig_ymin) * mchange * 50  # 50X change percentage, 2% hit ceiling
            #         plt.bar(data["xcord"], height, data["width"], bottom=fig_ymin, color=mycolor, alpha=0.2)
            #     elif mchange < 0:
            #         mycolor = "red"
            #         height = (fig_ymax - fig_ymin) * (0 - mchange) * 50  # 50X change percentage, -2% touch ground
            #         plt.bar(data["xcord"], height, data["width"], bottom=fig_ymax - height, color=mycolor, alpha=0.2)
                # plt.bar(data["xcord"], (fig_ymax-fig_ymin)*0.05, data["width"], bottom=fig_ymin+(fig_ymax-fig_ymin)*0.95, color=mycolor )
                # plt.bar(data["xcord"], (fig_ymax-fig_ymin), data["width"], bottom=fig_ymin, color=mycolor, alpha=0.2 )

    # Plot figure title
    facecolor = 'white'
    if re.search(r'-[\d\.]+R', sticker):
        facecolor = 'yellow'
    elif re.search(r'\s[\d\.]+R', sticker):
        facecolor = 'green'
    # coloring based on RSI
    if 'RSI-7' in sticker or 'RSI-8' in sticker or 'RSI-9' in sticker:
        facecolor = '#f38ed9'
    elif 'RSI-2' in sticker or 'RSI-1' in sticker:
        facecolor = '#c5f38e'
    # coloring based on Zacks ranking
    if 'A/' in sticker or 'B/' in sticker or 'C/' in sticker or 'zr1' in sticker or 'zr2' in sticker:
        color = "blue"
        if 'A/' in sticker or 'B/' in sticker or 'zr1' in sticker:
            color = "red"
        if facecolor == 'white':
            facecolor = 'yellow'
        plt.gca().text(
            fig_xmin + fig_xmax * 0.005, fig_ymax,
            sticker,
            fontsize=20, color=color,
            bbox=dict(facecolor=facecolor, alpha=0.8)
        )
    else:
        plt.gca().text(
            fig_xmin + fig_xmax * 0.005, fig_ymax,
            sticker,
            fontsize=20, color='blue',
            bbox=dict(facecolor=facecolor, alpha=0.8)
        )

    # Write figure annotation (beneath figure head)
    interval = 0.11
    y_position = interval
    if annotation:
        mymatch = re.match("\S+peg([\.\d]+)eday.+", annotation)
        peg = 0
        font_color = 'blue'
        if mymatch:
            peg = float(mymatch.group(1))
        if 0 < peg < 2:
            if peg < 1.6:
                alpha = 0.9
                font_color = 'red'
            else:
                alpha = 0.5
            plt.gca().text(fig_xmin + fig_xmax * 0.005,
                           fig_ymax - (fig_ymax - fig_ymin) * y_position,
                           annotation,
                           fontsize=17, color=font_color,
                           bbox=dict(facecolor='yellow', alpha=alpha)
                           )
        else:
            plt.gca().text(fig_xmin + fig_xmax * 0.005,
                           fig_ymax - (fig_ymax - fig_ymin) * y_position,
                           annotation,
                           fontsize=17, color='blue'
                           )
        y_position += interval

    # Plot price changes relative to different reference dates
    # Price change relative to recent one month high
    bleedout_1mon = bleedout(df.tail(20)["4. close"])
    # Price change relative to plotted period high
    bleedout_full_rang = bleedout(df["4. close"])
    # Price change relative to the first day of plotted data
    growth_full_range = up(df["4. close"])
    plt.gca().text(
        fig_xmin + fig_xmax * 0.005,
        fig_ymax - (fig_ymax - fig_ymin) * y_position,
        f"v{bleedout_full_rang} {bleedout_1mon} ^{growth_full_range}",
        fontsize=17, color='blue'
    )
    y_position += interval

    # Plot sort value if available
    if sort:
        color = "black"
        facecolor = "white"
        if sort < 0:
            color = "white"
            facecolor = "gray"
        sort = sort * 100
        sort = sort if abs(sort) >= 0.001 else '0.00000'
        plt.gca().text(
            fig_xmin + fig_xmax * 0.005, fig_ymax - (fig_ymax - fig_ymin) * y_position,
            f"Sort {str(sort)[:5]}" + '%', fontsize=17, color=color, bbox=dict(facecolor=facecolor)
        )

    # Add industry information if available
    if industry:
        plt.gca().text(
            fig_xmin + fig_xmax * 0.005, fig_ymin * 1.01,
            industry, fontsize=19, color="black"
        )

    return redraw


def draw_many_candlesticks(securities,
                           output="candlesticks.jpg",
                           num_row=3, num_col=3,
                           f_width=40, f_height=24,
                           dayspan=200,
                           widthgradient=8,
                           dualscale=False,
                           drawbyrow=False
                           ):
    """Draw plot for multiple securities

    Args:
        securities (dict): a dictionary of security object with key as security symbol
        output (str): path to the output plot file
        num_row (int): number of rows in the multi-panel figure
        num_col (int): number of columns in the multi-panel figure
        f_width (float): width of ouput figure
        f_height (float): height of ouput figure
        dayspan (int): number of unit (day, week or month)in the length of data
        widthgradient (float): the ratio between the widths of last day and first day in the data
        dualscale (boolean): if every one security to be plotted twice in different scale
        drawbyrow (boolean): plot images row after row if ture. Otherwise do column by column

    Returns
        recycle (list): a list of securities with dramatic price drops that potentially need to be
            re-drawn for clarity
    """

    # setup the plot
    plt.figure(figsize=(f_width, f_height))
    dualscale = False
    dayspan2 = ""

    # If 2 scales, turn dual scale on and parse the 2 scales from relevant argument
    if ',' in dayspan:
        dualscale = True
        num_col = num_col * 2

        spans = dayspan.split(',')
        dayspan = int(spans[0])
        try:
            dayspan2 = int(spans[1])
        except:
            dayspan2 = spans[1]
    else:
        dayspan = int(dayspan)

    # Set the order that panels to be filled in plot
    if drawbyrow:
        transposed_pos = list(range(1, num_row * num_col + 1))
    else:
        transposed_pos = index_transposed(num_row, num_col)
        # print(transposed_pos)
        # print(num_row, num_col, len(securities))
        if dualscale:
            new_order = []
            mycount = 0
            for i in range(0, len(transposed_pos)):
                position = transposed_pos[i]
                if position != 0:
                    new_order.append(position)
                    # print (i, position, end="\t")
                    transposed_pos[i] = 0
                    new_order.append(transposed_pos[(i + num_row)])
                    # print(i+num_row, transposed_pos[(i+num_row)])
                    transposed_pos[i + num_row] = 0
                    mycount += 1
                    if mycount > len(securities):
                        break
            transposed_pos = new_order

    # Loop through a dictionary of securities and make plot one by one
    pos = 0
    recycle = []
    for ticker, mysecurity in securities.items():
        df = mysecurity.get_price()
        df_copy = mysecurity.get_price()

        # Initialize a subplot
        pos += 1
        ax = plt.subplot(num_row, num_col, transposed_pos[pos - 1])
        ax.yaxis.tick_right()
        # Do a plot
        df = candlestick_gradient_width(df.tail(dayspan), widthgradient)
        redraw = draw_a_candlestick(ax, df, ticker, 3,
                                    mysecurity.get_date_added(),
                                    mysecurity.get_date_sold(),
                                    mysecurity.get_exit_price(),
                                    mysecurity.get_industry(),
                                    mysecurity.get_annotation(),
                                    mysecurity.get_sortvalue(),
                                    mysecurity.profit_loss
                                    )

        if (redraw):
            recycle.append(ticker)

        if dualscale:
            pos += 1
            ax = plt.subplot(num_row, num_col, transposed_pos[pos - 1])
            ax.yaxis.tick_right()

            # Daily scale but different length
            if isinstance(dayspan2, int):
                df = TimeSeriesPlus(df_copy).sma_multiple().df
                df = candlestick_gradient_width(df.tail(dayspan2), widthgradient)
            # Weekly scale
            elif dayspan2 == "w":
                df = df_copy.copy(deep=True)
                df = candlestick_gradient_width(TimeSeriesPlus(df).get_weekly().tail(dayspan), widthgradient)
            # Monthly scale
            elif dayspan2 == "m":
                df = df_copy.copy(deep=True)
                df = candlestick_gradient_width(TimeSeriesPlus(df).get_monthly().tail(dayspan), widthgradient)

            redraw = draw_a_candlestick(ax, df, ticker, 3,
                                        mysecurity.get_date_added(),
                                        mysecurity.get_date_sold(),
                                        mysecurity.get_exit_price(),     
                                        mysecurity.get_industry(),
                                        mysecurity.get_annotation(),
                                        mysecurity.get_sortvalue(),
                                        mysecurity.profit_loss
                                        )

    # !!! another way to reduce margin:
    # fig=plt.figure(); fig.tight_layout()

    # If only one security in the entire plot, change the output plot file name by the name of the security
    if num_row == 1:
        mymatch = re.match("(\S+)\:.+", ticker)
        output = mymatch.group(1)
        output = output + ".pdf"
        # output= mysecurity.get_date_added() + output
        output = mysecurity.date_added + output

    # Save all plots into output plot, and close plot engine
    plt.savefig(output, bbox_inches='tight')
    plt.close("all")

    return recycle


def bleedout(series):
    """Get price drop between last closing and the high in full length of the data

    Args:
        series (pandas series): series containing time series price data

    Returns:
        (str) : price drop since high in percentage
    """
    top = series.max()
    latest = series.iloc[-1]
    return f"{int(((top - latest)/top) * 100)}%"


def up(series):
    """Get relative price change between the first day and last day in data

    Args:
        series (pandas series): series containing time series price data

    Returns:
        (str) : price change in percentage
    """
    start = series.iloc[0]
    end = series.iloc[-1]
    # return f"{end:.2f}/{start:.2f}:{int(((end-start)/start)*100):>4}%"
    c = "NA"
    if np.isnan(start) or np.isnan(end):
        pass
    else:
        percentage = 0
        if start:
            percentage = ((end - start) / start) * 100
            percentage = round(percentage, 1)
        c = f"{percentage}%"
    return c


def set_row_num(num):
    """Get square root (whole number) of input number

    Args:
        num (int):

    Return
        int: whole number of square root
    """
    row = num ** (1/2)
    row_whole_num = int(row)
    if row_whole_num < row:
        row_whole_num += 1
    return row_whole_num


def index_transposed(num_row, num_col):
    b = np.arange(1, num_row * num_col + 1)
    return b.reshape([num_row, num_col]).transpose().reshape(num_row * num_col)
