#!/usr/local/bin/python

import sys
import argparse
import pandas as pd
from getAnnotation import sort_growth_value
from module.utility import get_delimiter

def df_add_newframe(old, new):
    """Add a 'new' dataframe  on top of 'old' dataframe.
        Priority is given to 'new' in case of  conflict
    
    Args:
        old: a pandas dataframe
        new: a second dataframe    
        *** the order of input arguments matters ***
    
    Returns:
        dataframe: a new dataframe combining 'old' and 'new'
    """
    return new.combine_first(old)


def df_add_newframes(alist):
    """Add new dataframes on top of old dataframes step by step.

    In each step, Priority is given to 'new' dataframe in case of
        conflict.

    Args:
        alist (list): a list of dataframe. The oldest dataframe at the
            right most first and the newest dataframe at the left most
            *** the order of elements in list matters.
            Oldest-> old->new->newest ***

    Returns:
        dataframe: a new dataframe combining all dataframes
    """
    base = pd.DataFrame()
    for df in alist:
        base = df_add_newframe(base, df)
        print(base.shape)
    return base


if __name__ == "__main__":

    # set up argument parser
    text = "Merge two or more descriptive tables (eg, Zacks download table)"
    parser = argparse.ArgumentParser(description=text)

    mandatory = parser.add_argument_group('mandatory arguments')
    mandatory.add_argument("query", nargs='*',
                           help=": A list of csv files")
    mandatory.add_argument("--out", help=": Output file")

    # get parser ready
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()

    # population key parameters
    output = args.out
    tables = args.query

    # read in input tables into dataframes and collect them into a list
    dataframes = []
    for table in tables:
        delimiter = get_delimiter(table)
        if not delimiter:
            print(f"No recognisable delimiter. Input file {table} is "
                  "neither .csv nor .tsv.")
            exit(0)

        try:
            df = pd.read_csv(table, sep=delimiter)
        except:
            print(f"Pandas error with opening {table}, ", sys.exc_info()[0])
            raise

        if 'Ticker' in df:
            df.set_index('Ticker')
        elif 'Symbol' in df:
            df.set_index('Symbol')
        else:
            print(f"No Ticker/Symbol column in dataframe in {table}")
            exit(0)

        dataframes.append(df)
    print(len(dataframes), " input tables")

    # merge a list of dataframes and export resulting dataframe to output file
    df = df_add_newframes(dataframes)
    if "Ticker" in df:
        df = df.set_index("Ticker")
    elif "Symbol" in df:
        df = df.set_index("Symbol")

    # sort dataframe by growth and value scores
    df = sort_growth_value(df)
    df = df.fillna(0)
    df.to_csv(output, sep="\t")
