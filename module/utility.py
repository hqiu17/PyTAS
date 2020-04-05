"""
Miscellaneous functions
"""

import os
import sys
import time
import pandas as pd
from alpha_vantage.timeseries import TimeSeries


def get_delimiter(file):
    """Get delimiter used inside of an input file based on file suffix

    Args:
        file (str): a file
    Returns:
        delimiter (char): the actual delimiter (eg, ',' and '\t')
    """
    delimiter = ""
    if file.endswith('.csv') or file.endswith('.CSV'):
        delimiter = ','
    elif file.endswith('.tsv') or file.endswith('.TSV'):
        delimiter = "\t"
    return delimiter


def get_timeseries(key):
    """Set up a timeseries object with output format and indexing
       type setups

    Args:
        key (str): alpha vantage API key
            (https://www.alphavantage.co/support/#api-key)
    Returns:
        ts (timeseries object): a timeseries object
    """

    ts = TimeSeries(key, output_format='pandas', indexing_type='date')
    return ts


def get_daliyprices_inpandas(timeseries, aticker):
    """Retrieve timeseries data from alpha vantage

    Args:
        timeseries: a Timeseries object
        aticker (str): name of a security

    Returns:
        data (df): a pandas dataframe holding the timeseries data
        meta_data (dict): meta-data of the downloaded timeseries
    """

    data, meta_data = timeseries.get_daily(
        symbol=aticker,
        outputsize='full'
    )
    return data, meta_data


# def setup_outdir(file):
#     """
#         substract dir name from file name (i.e., remove '.txt')
#         and create dir if no already exists
#         retrun dir name
#     """
#     mymatch = re.match(r'^(\S+).txt', file)
#     if mymatch:
#         dir = mymatch.group(1)
#     else:
#         dir = file + ".dir"
#
#     make_dir(dir)
#     return dir


def make_dir(directory):
    """Create a directory"""

    if not os.path.exists(directory):
        try:
            os.mkdir(directory)
        except:
            print(f"Error with creating directory {directory}, "
                  f"", sys.exc_info()[0])
            raise
        else:
            print("directory ", directory, " is created")
    else:
        print("directory ", directory, " already exists")


def file_name_rstrip(file_name):
    """Trim file suffix"""
    patterns = ['.txt','.tsv','.TSV','.csv','.CSV']
    for p in patterns:
        file_name = file_name.rstrip(p)
    return file_name



def fix_date_added(day):
    """Reword months"""

    day = day.replace(",", ", ")
    day = day.replace("Jan", "January")
    day = day.replace("Feb", "February")
    day = day.replace("Mar", "March")
    day = day.replace("Apr", "April")
    day = day.replace("Jun", "June")
    day = day.replace("Jul", "July")
    day = day.replace("Aug", "August")
    day = day.replace("Sep", "September")
    day = day.replace("Oct", "October")
    day = day.replace("Nov", "November")
    day = day.replace("Dec", "December")
    return day


# def pick_V_G_VGM(series):
#     i = False
#     if (series["Growth Score"] <= "C"):
#         if (series["Value Score"] <= "D"):
#             i = True
#         elif "VGM Score" in series:
#             if series["VGM Score"] == "A":
#                 i = True
#     elif "VGM Score" in series:
#         if series["VGM Score"] == "A":
#             i = True
#     return i


def get_output_filename(infile, **kwargs):
    """Generate output file name from infile name based keyward args"""

    file_name = infile
    if kwargs["sample"]:
        file_name = file_name + ".hist_" + kwargs["sample"]
    if kwargs["filterOnly"]:
        file_name = file_name + ".filtered"
    if kwargs["vgm"]:
        file_name = file_name + ".cvg"
    if kwargs["blind"] > 0:
        file_name = file_name + ".bld" + str(kwargs["blind"])
    if kwargs["filter_upward"]:
        file_name = file_name + ".fUpw" + kwargs["filter_upward"].replace(',', '-')
    if kwargs["cutBrokerbyRatio"] > 0:
        file_name = file_name + ".cbr" + str(int(kwargs["cutBrokerbyRatio"] * 100))
    if kwargs["cutBrokerbyCount"] > 0:
        file_name = file_name + ".cbc" + str(int(kwargs["cutBrokerbyCount"] * 100))
    if kwargs["sort_zacks"]:
        file_name = file_name + ".szk" + kwargs["sort_zacks"].replace(',', '')
    elif kwargs["sort_trange"]:
        file_name = file_name + ".str" + kwargs["sort_trange"].replace(',', '_')
    if kwargs["sort_ema_distance"] > 0:
        file_name = file_name + ".sEmaDist" + str(kwargs["sort_ema_distance"])
    if kwargs["sort_bbdistance"]:
        file_name = file_name + ".sbd" + kwargs["sort_bbdistance"].replace(',', '_')
    if kwargs["sort_brokerrecomm"]:
        file_name = file_name + ".sbr"
    if kwargs["sort_performance"] > 0:
        file_name = file_name + ".sPfm" + str(int(kwargs["sort_performance"]))
    if kwargs["sort_industry"]:
        file_name = file_name + ".sInd"
    if ',' in kwargs["sort_sink"]:
        file_name = file_name + ".ssk" + kwargs["sort_sink"].replace(',', '_')

    if ',' in kwargs["sort_change_to_ref"]:
        file_name = file_name + ".sChgRef" + kwargs["sort_change_to_ref"].replace(',', '_')

    if kwargs["sort_earningDate"]:
        file_name = file_name + ".sed"
    if kwargs["filter_macd_sgl"]:
        file_name = file_name + ".fMacd" + kwargs["filter_macd_sgl"].replace(',', '-')
    if kwargs["filter_stochastic_sgl"]:
        file_name = file_name + ".fStcs" + kwargs["filter_stochastic_sgl"].replace(',', '-')
    if kwargs["filter_ema_slice"]:
        file_name = file_name + ".fEmaSli" + kwargs["filter_ema_slice"].replace(',', '-')
    if kwargs["two_dragon"]:
        file_name = file_name + ".2drgn" + kwargs["two_dragon"].replace(',', '-')
    if kwargs["weekly"]:
        file_name = file_name + ".week"
    if kwargs["weekly_chart"]:
        file_name = file_name + ".wkch"

    return file_name


# def scale(list, max, min):
#     data_max=""
#     data_min=""
#         for array in list:
#             max = array.max()
#             min = array.min()
#             if max > data_max: data_max = max
#             if min < data_min: data_min = min

