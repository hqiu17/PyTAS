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
                        type=int, default=7,
                        help=": number of rows per image file")
    parser.add_argument("-w", "--weekly",
                        default=False,
                        help=": analyze using weekly data",
                        action='store_true')
    parser.add_argument("-wc", "--weekly_chart",
                        default=False,
                        help=": chart using weekly data",
                        action='store_true')   
    # FILTERING
    parser.add_argument("-cvg", "--vgm" ,
                        default=False,
                        help=": set filter on for VGM",
                        action='store_true')
    parser.add_argument("-upw", "--filter_upward" ,
                        type=str, default="",
                        help=": going upward in defined recent period [eg, 60,0.8,30 (window length,cutoff,"
                             "recent ignore]")
    parser.add_argument("-cbr", "--cutBrokerbyRatio",
                        type=float, default=0,
                        help=": set cut-off for broker buy recommendation ratio")
    parser.add_argument("-cbc", "--cutBrokerbyCount",
                        type=float, default=0,
                        help=": set cut-off for broker buy recommendation count")
    parser.add_argument("-str", "--sort_trange",
                        type=str, default="",
                        help=": sort names by trading range and filter data when this value is"
                             " greater than zero (eg, -str 20,0.05 means 20-day trading range with 0.05 cutoff)")
    parser.add_argument("-macd", "--filter_macd_sgl",
                        type=str, default="",
                        help=": filter for macd signal crossing upward")                 
    parser.add_argument("-stcs", "--filter_stochastic_sgl",
                        type=str, default="",
                        help=": filter for stochastic K>D signal. example 14,3,20,all or 14,3,20,crs")
    parser.add_argument("-mslc", "--filter_ema_slice",
                        type=str, default="",
                        help=": last price range is sliced (or intersected) by key EMA (20, 50, 100, 200)")
    parser.add_argument("-2dgn", "--two_dragon",
                        type=str, default="",
                        help=": filter for uptrend defined by 2 moving average. example 20,50,60 or 20,50,60,0.8")
                        
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
    parser.add_argument("-ssk", "--sort_sink", help=": sort by ratio of price down relative to reference date",
                        type=str, default="")

    parser.add_argument("-scr", "--sort_change_to_ref", type=str, default="",
                        help=": sort by price change given reference date(s), eg 2019-10-01,2019-10-010")


    parser.add_argument("-spfm", "--sort_performance", help=": sort by ratio of price down relative to reference date",
                        type=int, default=0)
    parser.add_argument("-smd", "--sort_ema_distance", help=": sort by last close to SMA distance",
                        type=int, default=0)
    parser.add_argument("-sbd", "--sort_bbdistance", type=str, default="",
                        help=": sort by distance to bollinger band bottom (eg, -sbd 0.05,3: distance <0.05 in any of "
                             "the last 3 days)")
    parser.add_argument("-bld", "--blind", help=": ignore recent period defined in days (for hypothesis test)",
                         type=int, default=0)

    # SAMPLING                        
    parser.add_argument("-smpl", "--sample",
                        type=str, default="",
                        help=": strategical sampling of historical data point: stks_bb, below_bb, plunge_macd")

    # SKIP CHARTING
    parser.add_argument("-f", "--filterOnly",
                        default=False,
                        help=": filter names only",
                        action='store_true')

    return parser

