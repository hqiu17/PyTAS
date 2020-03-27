#!/usr/local/bin/python

import os
import sys
import argparse
import pandas as pd


def get_query_data(qryfile, data, keep_all):
    """Retrieve data for a list of queries from a dataframe
    
    Arguments:
        qryfile: a file containing list of queries with security names
            at the first column. If more than one columns present, the
            file should be tab delimited.
        data: a pandas dataframe containing information to be
            retrieved. The index is a list of security name
        keep_all: a boolean. If true, query securities not present in
            'data' will not be discarded. Instead, their attributes
            are filled with '0'
             
    Return:
        dataframe:  with rows representing query securities
    """

    # set up empty dataframe and rows    
    df = pd.DataFrame()
    df.index.name = "Symbol"
    empty_row = pd.Series('0', data.columns)

    # read query file, loop through and append rows to empty dataframe
    try:
        queries = open(qryfile, "r")
    except OSError:
        print(f"fail to open/read file {qryfile}")

    hit = 0
    for line in queries:
        # security name is at the 1st column
        symbol = line.rstrip().split("\t")[0]

        if symbol == "Symbol":
            continue
        if symbol in data.index:
            df = df.append(data.loc[symbol], ignore_index=False)
            hit += 1
        else:
            if keep_all:
                empty_row.name = symbol
                df = df.append(empty_row, ignore_index=False)
    print("{}/{} output securities have annotations".format(hit, str(len(df))))

    return df


def sort_growth_value(df):
    """Sort dataframe by growth score and by value score

    Arguments:
        df: a pandas dataframe
    
    Return:
        df: a pandas dataframe after sorting
    """

    if "Growth Score" in df and "Value Score" in df:
        df["Growth Score"].replace('0', 'X', inplace=True)
        df["Value Score"].replace('0', 'X', inplace=True)
        df = df.sort_values(["Growth Score", "Value Score"], ascending=True)
    elif "Growth Score" in df:
        df["Growth Score"].replace('0', 'X', inplace=True)
        df = df.sort_values(["Growth Score"], ascending=True)
    elif "Value Score" in df:
        df["Value Score"].replace('0', 'X', inplace=True)
        df = df.sort_values(["Value Score"], ascending=True)
    return df


if __name__ == "__main__":

    # set up argument parser
    text = ("Given list(s) of securites, retrieve their descriptive information from a "
            "local database")
    parser = argparse.ArgumentParser(description=text)

    mandatory = parser.add_argument_group('mandatory arguments')
    mandatory.add_argument("qryfiles", nargs='*',
                           help=": file(s) containing a list of securities")
    mandatory.add_argument("--data", help=": a file containing security attribute data")

    optional = parser.add_argument_group('more optional arguments')
    optional.add_argument("--dlmt", help=": specify if the database is delimited by 'comma'"
                                         " or tab. Default: comma",
                          default="comma")
    optional.add_argument("--all", help=": retain all securities regardless of availability"
                                        " of their information in database",
                          action='store_true')

    # get parser ready
    if len(sys.argv) == 1: parser.print_help(sys.stderr); sys.exit(1)
    args = parser.parse_args()

    # population key parameters
    data_file = args.data

    keep_all = False
    if args.all: keep_all = True

    delimiter = args.dlmt
    if not delimiter or delimiter == "comma":
        delimiter = ","
    elif delimiter == "tab":
        delimiter = "\t"
    else:
        print("invalid delimiter {}\n".format(delimiter))
        parser.print_help(sys.stderr)
        sys.exit(1)

    # load database file to dataframe and set 'Symbol' column as index
    data = pd.DataFrame()
    if os.path.exists(data_file):
        try:
            data = pd.read_csv(data_file, sep=delimiter)
        except:
            print(f"Pandas error with opening {data_file}, ", sys.exc_info()[0])
            raise

        # use ticker column as replacement of symbol column
        if "Ticker" in data and "Symbol" not in data:
            data["Symbol"] = data["Ticker"]

        # test existence of symbol column. if true, set it as index
        if "Symbol" in data.columns:
            data = data.set_index("Symbol")
        else:
            print(f"No 'Symbol' column found in database file {data_file}")
            sys.exit(1)

    # loop through query files, data retrieval and write output file
    for query in args.qryfiles:
        df = get_query_data(query, data, keep_all)
        df = sort_growth_value(df)
        df.to_csv(query + ".tsv", sep="\t")
