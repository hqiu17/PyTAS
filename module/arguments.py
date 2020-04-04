import sys
import argparse

def get_parsed(args):
    # parser
    text= "Given a symbol list, draw candlesticks for each of item"
    parser = argparse.ArgumentParser(description = text)
    
    parser.add_argument("list", 
                        nargs='*',
                        help=": a list of symbol in TSV")
    parser.add_argument("-d", "--dir" , 
                        default="/Users/air/watchlist/daliyPrice",
                        help=": a direcotry holding price data for symbols")
    parser.add_argument("-day","--days",
                        type=str, default="200",
                        help=": length of period (days) to plot")
    parser.add_argument("-g","--gradient",
                        type=int, default=1,
                        help=": size gradient of plot box")
    parser.add_argument("-r","--rownumber",
                        type=int, default=5,
                        help=": size gradient of plot box")
    parser.add_argument("-w", "--weekly",
                        default=False,
                        help=": analyze and chart data in weekly timeframe",
                        action='store_true')
    parser.add_argument("-wc", "--weeklyChart",
                        default=False,
                        help=": only chart data in weekly timeframe",
                        action='store_true')   
    # FILTERING
    parser.add_argument("-cvg", "--vgm" ,
                        default=False,
                        help=": set filter on for VGM",
                        action='store_true')
    parser.add_argument("-upw", "--filter_upward" ,
                        type=str, default="",
                        help=": filter for uptrend. example: 60,0.8,30 (window length,cutoff,ignore recent)")
    parser.add_argument("-cbr", "--cutBrokerbyRatio",
                        type=float, default=0,
                        help=": set cut-off for broker buy recommendation ratio")
    parser.add_argument("-cbc", "--cutBrokerbyCount",
                        type=float, default=0,
                        help=": set cut-off for broker buy recommendation count")
    parser.add_argument("-str", "--sort_trange",
                        type=str, default="",
                        help=": sort names by trading range and filter data with this value >0 (e.g., -str 20,0.05: 20-day trading range with 5% cutoff)")
    parser.add_argument("-macd", "--filter_macd_sgl",
                        type=str, default="",
                        help=": filter for macd signal crossing upward")                 
    parser.add_argument("-stcs", "--filter_stochastic_sgl",
                        type=str, default="",
                        help=": filter for stochastic K>D signal. example 14,3,20,all or 14,3,20,crs")
    parser.add_argument("-mslc", "--filter_ema_slice",
                        type=str, default="",
                        help=": filter for price range contain MA or last close sandwiched between 2 MAs. example 20 or 20,50")
    parser.add_argument("-2dgn", "--two_dragon",
                        type=str, default="",
                        help=": filter for uptrend defined by 2 moving average. example 20,50,60 or 20,50,60,0.8")
                        
    # SORT
    parser.add_argument("-szk","--sort_zacks",
                        type=str, default="",
                        help='sort (and filter)symbols by zacks type value(V) or growth(G) rank. example -szk V,a')    
    parser.add_argument("-sda","--sort_dateAdded",
                        help=": sort by date added",
                        action='store_true')
    parser.add_argument("-sed","--sort_earningDate",
                        help=": sort by next earning report date",
                        action='store_true')
    parser.add_argument("-sbr", "--sort_brokerrecomm",  help=": sort by up trading range",
                        action='store_true')
    parser.add_argument("-sid", "--sort_industry", help=": sort by industry",
                        default=False, action='store_true')
    parser.add_argument("-ssk", "--sort_sink",     help=": sort by ratio of price down relative to reference date",
                        type=str, default="")
    parser.add_argument("-spfm", "--sort_performance",   help=": sort by ratio of price down relative to reference date",
                        type=int, default=0)
    parser.add_argument("-smd", "--sort_ema_distance",    help=": sort by last close to SMA distance",
                        type=int, default=0)
    parser.add_argument("-sbd", "--sort_bbdistance",
                        type=str, default="",
                        help=": sort by bollinger band bottom border distance. Example -sbd 0.05,3 (minimal bd <0.05 in the last 3 days)")
    parser.add_argument("-bld", "--blind",          help=": ignore the latest preriod (for hypothesis test)",
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

    #parser.print_help(sys.stdout)
    #if len(args)==0: parser.print_help(); sys.exit(1)                        
    #if len(args)==0: parser.print_help(); sys.exit(1)                        
    
    args=parser.parse_args(args)
    
    return args
