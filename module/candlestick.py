#!/Users/air1/anaconda3/bin/python
# cmp v1:  handle multiple datasets and plot multi-panel figure
# cmp v20: given a list ticker and directory holding price data, do multi-panel
#          candlestick plot
# cmp v21: handel zacks data only (need 'Date Added' information)

import os
import re
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

class Security:
    def __init__(self, df):
        self.df=df.copy(deep=True)
        self.note=""
        self.date_added=""
        self.date_sold=""
        self.industry=""
        self.annotation=""
    def set_date_added(self, date):
        self.date_added=date
    def set_date_sold(self, date):
        self.date_sold=date
    def set_note(self, note):
        self.note=note
    def set_industry(self, industry):
        self.industry=industry
    def set_annotation(self, annotation):
        self.annotation=annotation
	
                
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
                
def cstick_sma (df0):
    df=df0.copy(deep=True)    
    df["50MA"] =df["4. close"].rolling(50).mean()
    df["150MA"]=df["4. close"].rolling(150).mean()
    df["200MA"]=df["4. close"].rolling(200).mean()
    return df

def cstick_width_gradient (df0, ratio=10):
    """
        given the dataframe returned by alpha vantage, this function adds
        1) scaled candlestick x-axis coordinates "xcord"
        2) scaled candlestick width "width"
        3) candlestick color green vs. red
        4) set index using values from "xcord"
    """
    df = df0.copy(deep=True)
    
    # figure out the maximum/minimum of x axis
    sample_size = len(df.index)
    fig_xmin=0
    fig_xmax=sample_size
    
    # figure out asceding gradient "alpha" of bar width over time
    alpha = ratio **( 1/(sample_size-1) )
    total_bar_width = 1
    bar_width = 1
    for i in range(1, sample_size):
        bar_width = bar_width * alpha
        total_bar_width += bar_width
        i+=1
    # actual width of bar for day #1
    bar1_width = (fig_xmax - fig_xmin)/total_bar_width

    # iterate through days and apply alpha
    bar_xcord =[]
    bar_width =[]
    bar_color =[]
    
    right_edge = 0
    width_bar  = bar1_width
    count=0
    for date, data in df.iterrows():
        
        right_edge += width_bar
        # price open, close, high, an low information
        price_range = abs(data["2. high"]-data["3. low"])
        body_low = np.minimum(data["1. open"], data["4. close"])
        body_range = abs( (data["1. open"]-data["4. close"]) )
        if body_range <0.01:
            body_range=0.01
        if price_range <0.01:
            price_range=0.01
        # set color
        color="red"
        if data["1. open"]==body_low:
            color="green"
        
        bar_width.append(width_bar)
        bar_xcord.append(right_edge-width_bar/2)
        bar_color.append(color)
        
        width_bar = width_bar*alpha
        count+=1
    
    df["xcord"] = pd.Series(bar_xcord, index=df.index)
    df["width"] = pd.Series(bar_width, index=df.index)
    df["color"] = pd.Series(bar_color, index=df.index)
    df['Date close'] = df.index
    df['index']=df['xcord']
    df = df.set_index("index")
    return df
    
def date_to_index(date, series):
    date_close  = pd.to_datetime(series).copy(deep=True)
    date_series = pd.Series(date, index=series.index)
    date_series = pd.to_datetime(date_series).copy(deep=True)
    difference = (date_close - date_series).dt.days
    daysAfterAddtion = difference >0
    
    myseries = difference.copy(deep=True)
    myseries[daysAfterAddtion] = -200
    index_zacks = myseries.values.argmax()
    return index_zacks    
    return date_close.index[index_zacks]

def draw_a_candlestick(df0, sticker="", foldchange_cutoff=3, 
                       date_added="", date_sold="",
                       industry="",
                       annotation=""):
    redraw = 0
    df = df0.copy(deep=True)
    # figure out the maximum/minimum of x/y axis
    #
    sample_size = len(df.index)
    fig_ymin=df.min(axis=0)["3. low"]
    fig_ymax=df.max(axis=0)["2. high"]
    
    fig_xmin=0
    fig_xmax=sample_size
    
    if "weather" in df.columns:
        fig_ymax = fig_ymax + (fig_ymax-fig_ymin)*0.0526
    
    plt.xlim(fig_xmin, fig_xmax)
    plt.ylim(fig_ymin, fig_ymax)

    # redraw
    #
    fold_change = fig_ymax/df["4. close"].iloc[-1]
    if (fold_change > foldchange_cutoff):
        redraw=1

    #
    # plot last day's low and close
    color_closing="black"
    if   df.iloc[-1]["4. close"]>df.iloc[-1]["1. open"]:
        color_closing="green"
    elif df.iloc[-1]["4. close"]<df.iloc[-1]["1. open"]:
        color_closing="red"
    plt.axhline(y=df.iloc[-1]["1. open"],color=color_closing,linewidth=0.2)
    plt.axhline(y=df.iloc[-1]["4. close"]  ,color=color_closing,linewidth=0.2)

    #
    # plot vertical lines
    if sample_size > 480:
        plt.axvspan(df.index[-480],df.index[-241],color="grey", alpha=0.1)
    elif sample_size > 240:
        plt.axvspan(df.index[0],df.index[-241],color="grey", alpha=0.1)
    if sample_size > 80 and sample_size < 240:
        plt.axvspan(df.index[-80],df.index[-60],color="grey", alpha=0.1)
    if sample_size > 40 and sample_size < 240:
        plt.axvspan(df.index[-40],df.index[-20],color="grey", alpha=0.1)
    
    # plot 2018 dip
    index = date_to_index(pd.to_datetime("2018-12-26 00:00:00"), df['Date close'])
    dip_xcoordiante = df.index[index]
    plt.axvline(x=dip_xcoordiante,color="brown",dashes=[5,10],linewidth=1)
    index = date_to_index(pd.to_datetime("2018-10-4 00:00:00"), df['Date close'])
    dip_xcoordiante = df.index[index]
    plt.axvline(x=dip_xcoordiante,color="brown",dashes=[5,10],linewidth=1)
    
    # plot specified dates
    if date_added:
        index = date_to_index(date_added, df['Date close'])
        x_coordinate = df.index[index]
        plt.axvline(x=x_coordinate,color="blue",linewidth=1) #dashes=[5,10],
        close_onbefore_zacks = df.iloc[index]['4. close']
        plt.axhline(y=close_onbefore_zacks,color="blue",linewidth=1) #dashes=[5,10],
    if date_sold:
        index = date_to_index(date_sold, df['Date close'])
        x_coordinate = df.index[index]
        plt.axvline(x=x_coordinate,color="orange",dashes=[5,10],linewidth=1)
        #close_onbefore_zacks = df.iloc[index]['4. close']
        #plt.axhline(y=close_onbefore_zacks,color="black",dashes=[5,10],linewidth=0.3)

    #
    # plot SMA
    if sample_size > 50:
        df["50MA"].plot()
        df["150MA"].plot()
        df["200MA"].plot()

    #
    # plot candlesticks
    for num, data in df.iterrows():
        price_low = data["3. low"]
        price_range = data["2. high"]-data["3. low"]
        body_low = np.minimum(data["1. open"], data["4. close"])
        body_range = abs( (data["1. open"] - data["4. close"]) )
        if body_range <0.01:
            body_range=0.01
        if price_range <0.01:
            price_range=0.01
        
        plt.bar(data["xcord"], body_range,  data["width"],   bottom=body_low,  color=data["color"] )
        if sample_size < 500:
            plt.bar(data["xcord"], price_range, data["width"]/5, bottom=price_low, color=data["color"] )
            
        # plot market market benchmark data
        if sample_size < 200 and "weather" in df.columns:
            mchange = data["weather"]
            mycolor = "yellow"
            if mchange>0:
                mycolor="green"
                height = (fig_ymax-fig_ymin)*mchange*50  # 50X change percentage, 2% hit ceiling 
                plt.bar(data["xcord"], height, data["width"], bottom=fig_ymin, color=mycolor, alpha=0.2 )
            elif mchange<0:
                mycolor="red"
                height = (fig_ymax-fig_ymin)*(0-mchange)*50 # 50X change percentage, -2% touch ground
                plt.bar(data["xcord"], height, data["width"], bottom=fig_ymax-height, color=mycolor, alpha=0.2 )
            #plt.bar(data["xcord"], (fig_ymax-fig_ymin)*0.05, data["width"], bottom=fig_ymin+(fig_ymax-fig_ymin)*0.95, color=mycolor )            
            #plt.bar(data["xcord"], (fig_ymax-fig_ymin), data["width"], bottom=fig_ymin, color=mycolor, alpha=0.2 )
    
    #
    # plot stock name
    font=FontProperties()
    font=font.copy()
    font.set_weight('bold')
    font.set_style('italic')
    #font.set_size('large')
    
    #
    # plot figure title
    plt.gca().text(
                   fig_xmin+fig_xmax*0.005,
                   fig_ymax, #+(fig_ymax-fig_ymin)*0.05,
                   sticker,
                   fontsize=20,
                   #fontproperties=font,
                   color='blue'
                   )
                   
    #
    # write within figure area
    y_position=0.08
    if annotation:
        mymatch=re.match("\S+peg([\.\d]+)eday.+", annotation)
        peg=0
        if mymatch:
            peg=float(mymatch.group(1))
        if peg>0 and peg <1.5:
            plt.gca().text(fig_xmin+fig_xmax*0.005,
                           fig_ymax-(fig_ymax-fig_ymin)*y_position,
                           annotation,
                           fontsize=17, color='red',
                           bbox=dict(facecolor='yellow')
                           )
        else:
            plt.gca().text(fig_xmin+fig_xmax*0.005,
                       fig_ymax-(fig_ymax-fig_ymin)*y_position,
                       annotation,
                       fontsize=17, color='blue'
                       )
        y_position += 0.08
    #
    # plot price drop compared to 30/120 days ago
    bleedout_1mon  = bleedout( df.tail(20)["4. close"] )
    bleedout_3mon  = bleedout( df.tail(60)["4. close"] )
    growth_alltime = up( df["4. close"] )
    plt.gca().text(
                   fig_xmin+fig_xmax*0.005,
                   fig_ymax-(fig_ymax-fig_ymin)*y_position,
                   f"v{bleedout_1mon}{bleedout_3mon}^{growth_alltime}",
                   fontsize=17, color='blue'
                   )

    if industry:
        plt.gca().text(
                        fig_xmin+fig_xmax*0.005,
                        fig_ymin*1.01,
                        industry,
                        fontsize=19, color="black"
                        )

    return redraw

def draw_many_candlesticks(securities,
                           output="candlesticks.jpg",
                           num_row=3, num_col=3,
                           f_width=40, f_height=24,
                           dayspan=200,
                           widthgradient=8,
                           #dualscale=False,
                           drawbyrow=False
                           ):
    """
        Given a dict ( {ticker: dataframe derived from alpha vantage} ) as input,
        plot all price datasets into a multi-panel figure
    """

    # setup the plot
    plt.figure(figsize=(f_width,f_height))
    dualscale = False
    dayspan2=""
    if ',' in dayspan:
        dualscale=True
        num_col=num_col*2
        spans=list(map(int, dayspan.split(',')))
        dayspan =spans[0]
        dayspan2=spans[1]
    else:
        dayspan=int(dayspan)
         
    # set the order that panels to be filled in plot
    if drawbyrow:
        transposed_pos = list(range(1, num_row*num_col+1))
    else:
        transposed_pos = index_transposed(num_row, num_col)
        #print(transposed_pos)
        #print(num_row, num_col, len(securities))
        if dualscale:
            new_order=[]
            mycount=0
            for i in range(0,len(transposed_pos)):
                position = transposed_pos[i]
                if position != 0:
                    new_order.append(position)
                    #print (i, position, end="\t")
                    transposed_pos[i]=0
                    new_order.append(transposed_pos[(i+num_row)])
                    #print(i+num_row, transposed_pos[(i+num_row)])
                    transposed_pos[i+num_row]=0
                    mycount+=1
                    if mycount > len(securities):
                        break
            transposed_pos=new_order

    pos=0
    recycle = []
    for ticker, mysecurity in securities.items():
        df = mysecurity.get_price()
        df_copy = mysecurity.get_price()
        
        pos+=1
        
        ax=plt.subplot(num_row, num_col, transposed_pos[pos-1])
        #print ("#1", ticker, num_row, num_col, pos-1)
        ax.yaxis.tick_right()
        

        #df=cstick_sma(df)
        df=cstick_width_gradient( df.tail(dayspan), widthgradient )
        redraw = draw_a_candlestick(df, ticker, 3, 
                                    mysecurity.get_date_added(),
                                    mysecurity.get_date_sold(),
                                    mysecurity.get_industry(),
                                    mysecurity.get_annotation()
                                    )
        
        if (redraw):
            recycle.append(ticker)
        
        if dualscale:
            pos+=1
            ax=plt.subplot(num_row, num_col, transposed_pos[pos-1])
            ax.yaxis.tick_right()
            #print ("#2", ticker, num_row, num_col, pos-1)
            
            df=cstick_sma(df_copy)
            df=cstick_width_gradient( df.tail(int(dayspan2)), widthgradient )
            redraw = draw_a_candlestick(df, ticker, 3, 
                                        mysecurity.get_date_added(),
                                        mysecurity.get_date_sold(),
                                        mysecurity.get_industry(),
                                        mysecurity.get_annotation()
                                        )

    #!!! another way to reduce margin:
    #fig=plt.figure(); fig.tight_layout()
    if num_row==1:
        mymatch=re.match("(\S+)\:.+", ticker)
        output=mymatch.group(1)
        output=output+".pdf"
    plt.savefig(output, bbox_inches='tight')

    plt.close("all")
    return recycle

def bleedout(pands_series):
    top   = pands_series.max()
    latest= pands_series.iloc[-1]
    #return f"{latest:.2f}/{top:.2f}:{int(((top-latest)/top)*100):>3}%"
    return f"{int(((top-latest)/top)*100)}%"

def up(pandas_series):
    start = pandas_series.iloc[0]
    end   = pandas_series.iloc[-1]
    #return f"{end:.2f}/{start:.2f}:{int(((end-start)/start)*100):>4}%"
    return f"{int(((end-start)/start)*100)}%"

def set_row_num(total):
    row = total ** (1/2)
    row = int(row) + 1
    return row

def file_strip_txt (file):
    name=file
    mymatch = re.match(r'^(\S+)(?:.txt)+', file)
    if mymatch:
        name = mymatch.group(1)
    return name

def index_transposed(num_row, num_col):
    b=np.arange(1,num_row*num_col+1)
    return b.reshape([num_row,num_col]).transpose().reshape(num_row*num_col)

if __name__ == "__main__":
    pass
