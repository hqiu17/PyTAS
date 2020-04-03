#!/usr/bin/env python3

import re
import os
import sys
import time
import argparse
from datetime import datetime
import module.utility as utility


def get_key(file):
    """Read a key from input file
    
    Args:
        file (str): a text file containing a key

    Returns:
        mykey (str): return a key string
    """
    try:
        fh = open(file, "r")
    except:
        print (f"Error with opening {file}, ", sys.exc_info()[0])
        raise
        
    key = ""
    for line in fh:
        if line.strip():
            key = line
            break
    return key


def get_filecreation_date(filepath):
    """Get a creation time for a filepath
    
    Args:
        filepath : a path of a file
    Returns:
        a code string for date of creation: such as 20190801
        a code string for weekday of creation: such as 1 for Tuesday
    """

    time_stamp=os.stat(filepath).st_ctime
    datetime_obj=datetime.fromtimestamp(time_stamp)
    date_code=get_datecode(datetime_obj)
    return date_code, datetime_obj.weekday()


def get_datecode(datetime_obj):
    """Turn datetime object (e.g., for 2019, 8, 1) into numeric
       code 20190801
    
    Args:
        datetime_obj: a daytime object

    Returns:
        date_code (str): concatenate digits for year, month and day
        (eg, 20190801)
    """

    date_code=datetime_obj.year*10000
    date_code=date_code + 10000 + datetime_obj.month*100
    date_code=date_code + 100 + datetime_obj.day
    date_code=date_code - 10100
    return date_code


def download_asymbol(symbol, outfile):
    """Download timeseries data and write to local file
    
    Args:
        symbol : a string representing the name of a security
        outfile: a outfile where the price is written to

    Returns:
        status: status equals 1 on failure for whatever reasons
    """

    status = 0
    try:
        prices, metadata = utility.get_daliyprices_inpandas(ts, symbol)
        prices.to_csv(outfile, sep="\t")
    except:
        # Just flag it. Do not raise or exit for individual failure
        status = 1
    return status


def maneuver_asymbol(ticker, outfile, safenest, num=0, pause=11):
    """Manage download file for a security (ticker).

       If prior download file exists, move it to storage directory
       before launching download.
    
    Arguments:
        ticker (str): name of security
        outfile (path): outfile where download will be written into
        safenest (path): directory where prior download to be stashed
        num (int): a number to print for purpose of progress monitor
        pause (int): time (in second) to pause after a download
    """
    
    msg = ""
    # backup outfile
    if os.path.isfile(outfile):
        outfile_basename = os.path.basename(outfile)
        outfile_backup   = os.path.join(safenest, outfile_basename)
        os.rename(outfile, outfile_backup)
        msg = "; previous download is relocated"
    
    # download data for ticker into outfile
    print (f"# {num:>4} {ticker:<6} is to be done", end="\r")
    status = download_asymbol(ticker, outfile)

    print (" "*27, end="\r")
    if status == 1 : 
        print (f"# {num:>4} {ticker:<6} remote retrieval failure")
    else:
        print (f"# {num:>4} {ticker:<6} is done{msg}")


def get_creation_status(filepath):
    """Figure out creation status for a given file
    
    Args:
        filepath : query file
        verbose: whether or not print out file creation details

    Returns:
        status (boolean): True for done and False for not done yet
        file_datecode (str): code for file download date
    """

    status = False
    today_datecode = get_datecode(datetime.today())
    today_weekdaycode = datetime.today().weekday()
    file_datecode, file_weekdaycode = get_filecreation_date(filepath)

    diff_datecode = today_datecode - file_datecode
    if (diff_datecode) == 0:
        status = True
    elif today_weekdaycode == 5 and (diff_datecode) == 1:
        # On Saturday with existing download created on this Friday
        status = True
    elif today_weekdaycode == 6 and (diff_datecode) <= 2:
        # On Sunday with existing download created on this Friday or Saturday
        status = True
    return status, file_datecode


def download_alist(file, directory, pause, refresh=False, stay=False):
    """Download securities listed in input file

    Args:
        file (path): path to a file
        directory (path): path to a directory
        pause (int): time to pause in second
        refresh (boolean): re-download everthing
        stay (boolean): acknowledge existing download
    """

    # open input file containing security list
    try:
        fh = open(file, "r")
    except:
        print (f"Error with opening {list}, ", sys.exc_info()[0])
        raise
    
    # loop through the list
    for num, line in enumerate(fh):
        # remove header line
        if line.startswith('Symbol'):
            continue
        if line.startswith('Ticker'):
            continue
        
        # extract security name and set output file name
        ticker=""
        mymatch = re.match(r'(\S+)\s.*', line)
        if mymatch:
            ticker = mymatch.group(1)
        if ticker and '.' not in ticker:
            outfile = os.path.join(directory, ticker+".txt")
            
            # if output file exits, test if it is outdated
            if os.path.isfile(outfile):
                # acknowledge all prior download files
                # skip download missions
                if stay:
                    print (f"# {num:>4} {ticker:<6} has been done [stay]")
                    continue
                # act based on download date of prior download file
                else:
                    status, datecode = get_creation_status(outfile)
                    if status:
                        # ignore all existing output file
                        # redone all download missions
                        if refresh:
                            maneuver_asymbol(ticker, outfile, storage, num)
                            time.sleep(pause)
                        # download has been done. do nothing
                        else:
                            print (f"# {num:>4} {ticker:<6} "
                                   f"has been done on {datecode}")
                    else:
                        maneuver_asymbol(ticker, outfile, storage, num)
                        time.sleep(pause)
            # if no prior download is found, then download
            else:
                #print (f"# {num:>4} {ticker:<6} is to be done")
                maneuver_asymbol(ticker, outfile, storage, num)
                time.sleep(pause)

    fh.close()
    print ("done with ", file)


if __name__ == "__main__":

    # set up argument parser
    text= "Given a list of securites, download their daily price data " \
          "from Alpha Vantage"
    parser = argparse.ArgumentParser(description=text)
    parser.add_argument("securities",
                        nargs='*',
                        help=": file(s) containing securities (one per row)")
    parser.add_argument("--key",
                        help=": file containing a Alpha Vantage API key")
    parser.add_argument("--dir" ,
                        default="./daily",
                        help=": directory storing all downloaded data"
                             "(default='./daily')")
    parser.add_argument("--refresh", 
                        help=": ignore existing download files",
                        action='store_true')
    parser.add_argument("--stay", 
                        help=": skip securities with prior download"
                             "files regardless of their creation date",
                        action='store_true')
    parser.add_argument("--backup",
                        default=".avbackup",
                        help=": backup directory to hold all previous"
                             "downloads (default='./avbackup')")
    parser.add_argument("--pause",
                        default=11,
                        type=int,
                        help=": time to pause after each download "
                             "(default=11)")

    # get parser ready
    if len(sys.argv)==1: parser.print_help(sys.stderr); sys.exit(1)
    args=parser.parse_args()

    # population key parameters
    directory = args.dir
    storage = args.backup
    stay = args.stay
    refresh = args.refresh
    pause = args.pause

    if args.key:
        mykey=get_key(args.key)
        ts = utility.get_timeseries(mykey)
    else:
        print("A API key is required in order to download data. "
              "A free key can be requested from Alpha Vantage "
              "(https://www.alphavantage.co/support/#api-key)"
              )
        parser.print_help(sys.stderr)
        sys.exit(1)

    # set up directories
    utility.make_dir(directory)
    utility.make_dir(storage)


    today_weekday  = datetime.today().weekday()
    print(str(today_weekday+1), datetime.today())

    for security in args.securities:
        download_alist(security, directory, pause, refresh, stay)
