import sys
import argparse

def get_parser():
    #print('get_parsed 1')
    # parser
    text= "Given a symbol list, draw candlesticks for each of item"
    parser = argparse.ArgumentParser(description = text)
    
    parser.add_argument("list", 
                        nargs='+',
                        help=": a list of symbol in TSV")
    parser.add_argument("-d", "--dir" , 
                        default="/Users/air/watchlist/daliyPrice",
                        help=": a directory holding price data for symbols")
    parser.add_argument("-day","--days",
                        type=str, default="200",
                        help=": length of period (days) to plot")
    parser.add_argument("-g","--gradient",
                        type=int, default=1,
                        help=": width gradient of candlestick")
    parser.add_argument("-r","--row_number",
                        type=int, default=5,
                        help=": number of rows per image file")
    parser.add_argument("-w", "--weekly",
                        default=False,
                        help=": analyze using weekly data",
                        action='store_true')
    parser.add_argument("-m", "--monthly",
                        default=False,
                        help=": analyze using monthly data",
                        action='store_true')
    parser.add_argument("-ts", "--time_scale",
                        type=str, default='',
                        help=": specify time scale such as weekly or monthly (eg, week,c: weekly"
                             " transformation for charting only)"
                        )
    parser.add_argument("-wc", "--weekly_chart",
                        default=False,
                        help=": chart using weekly data",
                        action='store_true')
    parser.add_argument("-pv", "--plot_volumne",
                        default=False,
                        help=": plot volumne data",
                        action='store_true')
    parser.add_argument("-rms", "--remove_sector",
                        type=str, default='',
                        help=": sectors to be removed, e.g., Medical,Oil",
                        )


    # FILTERING
    parser.add_argument("-cvg", "--vgm" , default=False, action='store_true',
                        help=": set filter on for VGM")
    parser.add_argument("-upw", "--filter_upward", type=str, default="",
                        help=": going upward in defined recent period [eg, 60,0.8,30 (window length,cutoff,"
                             "recent ignore]")
    parser.add_argument("-cbr", "--cutBrokerbyRatio", type=float, default=0,
                        help=": set cut-off for broker buy recommendation ratio")
    parser.add_argument("-cbc", "--cutBrokerbyCount", type=float, default=0,
                        help=": set cut-off for broker buy recommendation count")
    parser.add_argument("-str", "--sort_trange", type=str, default="",
                        help=": sort names by trading range and filter data when this value is"
                             " greater than zero (eg, -str 20,0.05 means 20-day trading range with 0.05 cutoff)")
    parser.add_argument("-macd", "--filter_macd_sgl", type=str, default="",
                        help=": filter for macd signal crossing upward signal, eg, 12,24,3")
    parser.add_argument("-emas", "--filter_ema_sgl", type=str, default="",
                        help=": filter for ema crossing upward signal, eg, 5,10,3")
    parser.add_argument("-stcs", "--filter_stochastic_sgl", type=str, default="",
                        help=": filter for stochastic K>D signal. example 14,3,20,all or 14,3,20,crs")
    parser.add_argument("-mslc", "--filter_ema_slice", type=str, default="",
                        help=": last price range is sliced (or intersected) by key EMA (20, 50, 100, 200)")
    parser.add_argument("-pslc", "--filter_horizon_slice", type=str, default="",
                        help=": last price hitting support defined by 2 pivots in the past 200 days, e.g., 200,2")
    parser.add_argument("-hspt", "--filter_hit_horizontal_support", type=str, default="",
                        help=": last price touches from above support defined by 2 pivots in the past 200 days, e.g., 200,2")
    parser.add_argument("-hrst", "--filter_hit_horizontal_resistance", type=str, default="",
                        help=": last price touches from below resistance defined by 2 pivots in the past 200 days, e.g., 200,2")
    parser.add_argument("-pema", "--filter_parallel_ema", type=str, default="",
                        help=": filter for 2 ema that are largely parallel in defined period, e.g., 20,50,60 or 20,50,60,0.8")
    parser.add_argument("-espt", "--filter_hit_ema_support", type=str, default="",
                        help=": filter for last close hitting ema from above, e.g., 100,10")
    parser.add_argument("-frsi", "--filter_rsi", type=str, default="",
                        help=": filter for rsi within defined rang, eg, 0,30")
    parser.add_argument("-fsvl", "--filter_surging_volume", type=str, default="",
                        help=": filter for volume contraction given two length, eg, 10,30")
    parser.add_argument("-fevl", "--filter_exploding_volume", type=str, default="",
                        help=": filter for high volume relative to its SMA value, eg, 10")
    parser.add_argument("-fprc", "--filter_price", type=str, default="",
                        help=": filter for last closing price within defined range, eg, 20,500")
    parser.add_argument("-fcsd", "--filter_consolidation_p", type=str, default="",
                        help=": filter for consolidation score for defined most recent period, eg, 30,0.1")
    parser.add_argument("-fema3", "--filter_ema_3layers", type=str, default="",
                        help=": filter for query EMA sandwiched between two defined EMAs (eg, 2,20,100) "
                             "for a recent period (eg, 2,20,100,20,0.8)")


    # SORT
    parser.add_argument("-szk","--sort_zacks", type=str, default="",
                        help=': sort (and filter)symbols by zacks type value(V) or growth(G) rank. example -szk V,a')
    parser.add_argument("-sda","--sort_dateAdded", help=": sort by date added",
                        action='store_true')
    parser.add_argument("-sed","--sort_earningDate", help=": sort by next earning report date",
                        action='store_true')
    parser.add_argument("-sbr", "--sort_brokerrecomm", help=": sort by up trading range",
                        action='store_true')
    parser.add_argument("-sid", "--sort_industry", help=": sort by industry",
                        default=False, action='store_true')
    parser.add_argument("-ssk", "--sort_sink", type=str, default="",
                        help=": sort by ratio of price down relative to reference date")
    parser.add_argument("-scr", "--sort_change_to_ref", type=str, default="",
                        help=": sort by price change given reference date(s), eg 2019-10-01,2019-10-010")
    parser.add_argument("-spfm", "--sort_performance", type=str, default=0,
                        help=": sort by relative price change in defined recent period, eg, 20 or 20,SPY")
    parser.add_argument("-smd", "--sort_ema_distance", type=int, default=0,
                        help=": sort by last close to SMA distance")
    parser.add_argument("-sbd", "--filter_bbdistance", type=str, default="",
                        help=": sort by distance to bollinger band bottom (eg, -sbd 0.05,3: distance <0.05 in any of "
                             "the last 3 days)")
    parser.add_argument("-bld", "--blind", type=int, default=0,
                        help=": ignore recent period defined in days (for hypothesis test)")
    parser.add_argument("-srs", "--sort_rsi_std", type=str, default='',
                        help=": sort by standard deviation of RSI in look-back period (eg, 20,6)")
    parser.add_argument("-sea", "--sort_ema_attraction", type=str, default='',
                        help=": sort by ema-vs-closing standard deviation in look-back period (eg, 50,10)")
    parser.add_argument("-see", "--sort_ema_entanglement", type=str, default='',
                        help=": filter and sort by ema crosses in defined recent look-back period (eg, 2,20,60,6)")
                        
                        
                        

    #SAMPLING
    parser.add_argument("-smpl", "--sample",
                        type=str, default="",
                        help=": strategical sampling of historical data point: stks_bb, below_bb, plunge_macd")

    parser.add_argument("-bdat", "--backtest_date",
                        type=str, default="",
                        help=": analyzed data using closing at back test date (eg, 2012-12-12,30)")



    # SKIP CHARTING
    parser.add_argument("-f", "--filterOnly", default=False,
                        help=": filter names only", action='store_true')

    return parser
