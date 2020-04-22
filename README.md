# PyTAS
PyTAS (Python technical analysis strategies) includes python scripts for downloading equity historical data, and for sorting, scanning and charting equities using a variety of technical indicators.


## Dependency
Python 3 (https://www.python.org/)

alpha_vantage (https://github.com/RomelTorres/alpha_vantage)

Numpy (https://numpy.org/)

Pandas (https://pandas.pydata.org/)

Matplotlib (https://matplotlib.org/)


## Usage demonstration with example data

### 1. Download free historical daily data
An API key is required to download data from Alpha Vantage (https://www.alphavantage.co/). You can claim a [free key](https://www.alphavantage.co/support/#api-key) that allows 5 downloads per minute and 500 downloads per day. Save the key in a file, e.g., my_key.

#### 1.1 Basic download
To download a list of equities included in tab-delimited file (sample.txt), type the following command in terminal:
```
downloadList.py --key my_key --dir download sample.txt
```
A destination directory 'download' will be created (if not already exists) and all historical data will be saved in this direcotry. By default, the program assumes a free API key and pauses 11 seconds every time a download attempt is made (5 downloas/minute). 

#### 1.2 --pause
The download frequency can be increase or decreased by giving a pause argument. To request download everything 2 seconds:
```
downloadList.py --key my_key --dir download sample.txt --pause 2
```

#### 1.3 --keep
If downloaded data file for an equity alread exists in destination direcotry, the script will check the time when the file was downloaded. If the file was downloaded a day before or earlier, it will be moved to a hidden directory (.pytas_backup) created by the script by default. If it was downloaded on the same day, the file will be kept and the corresponding equity will be ignored form download list. To force keeping all existing data file regardless of when they were downloaded:
```
downloadList.py --key my_key --dir download sample.txt --keep
```

#### 1.4 --refresh
To ignore all existing data file regardless of when they were downloaded:
```
downloadList.py --key my_key --dir download sample.txt --refresh
```

#### 1.5 --backup
To override the default backup directory setting, you can specify your own backup directory:
```
downloadList.py --key my_key --dir download sample.txt --backup my_backup_folder
```

### 2. Chart equities 
#### 2.1 Basic charting
```
chartList.py --dir download sample.txt
```
By default, the last 200 days' historical data will be plotted together with key moving everages for each equity included in 'sample.txt'. The charts will be sorted in output PDF file(s).

#### 2.2 --day
To specify the length of recent period (e.g., 60 days) to be plotted:
```
chartList.py --dir download sample.txt --day 60
```

#### 2.3 --weekly_chart
To create weekly chart:
```
chartList.py --dir download sample.txt --day 60 --weekly_chart
```

### 3. Sort equities 

#### 3.1 --sort_industry
Sort equities by their associated industry
```
chartList.py --dir download sample.txt --sort_industry
```

#### 3.2 --sort_performance
Sort equities by their performance in specified recent period (e.g., 200 days):
```
chartList.py --dir download sample.txt --sort_performance 200
```

#### 3.3 --sort_ema_distance
Sort equities by the difference between the last closing price and specified EMA. The distance is calculated by dividing the difference by the last closing price. 
```
chartList.py --dir download sample.txt --sort_ema_distance 100
```

#### 3.4 --sort_change_to_ref
Sort equities by price difference between two specified dates. The difference is normalized dividing the price change by the closing price of the first date.
```
chartList.py --dir download sample.txt --sort_change_to_ref 2018-09-10,2018-09-18
```

### 4. Filtering equities 

#### 4.1 --filter_upward
Filter for equities in uptrend pattern. The uptrend is defined by length of period (160 days) and frequency (0.8) of days supporting an uptrend pattern (20EMA>50EMA>150EMA):
```
chartList.py --dir download sample.txt --filter_upward 160,0.8  
```

#### 4.2 --filter_ema_slice
Filter for equities with last trading range intersected by key SMA lines (e.g., 100SMA). The options include 20, 50, 100, 150, and 200.
```
chartList.py --dir download sample.txt --filter_ema_slice 100   
```

#### 4.3 --filter_macd_sgl
Filter for equities with macd line staying below signal line for at least 8 days and then crossing above at the last trading day. Macd line is calculated from two specified EMA(14 and 26)
```
chartList.py --dir download sample.txt --filter_macd_sgl 12,26
```
Filter for equities with macd line staying below signal line for at least 5 days and then crossing above within the last 3 trading days
```
chartList.py --dir download sample.txt --filter_macd_sgl 12,26,3
```

#### 4.4 --filter_stochastic_sgl
Filter for equities with K line crossing above D line and staying below D-value cutoff (30) at the last trading day. K and D lines are calculated with look-back period (14 days) and 3-day EMA smoothing, respectively. 
```
chartList.py --dir download sample.txt --filter_stochastic_sgl 14,3,30,crs
```
Filter for equities with K staying above D and below cutoff (not requiring crossing over).
```
chartList.py --dir download sample.txt --filter_stochastic_sgl 14,3,30,all
```

#### 4.5 --filter_bbdistance
Filter for equities with normalized distance (<0.05) between last close and Bollinger lower boundary. The normalization is done dividing the difference between the last closing price and Bollinger lower band by the width of Bollinger band in the same day. 
```
chartList.py --dir download sample.txt --filter_bbdistance 0.05 --day 60
```
Filter for equities with normalized distance (<0.05) between closing price and Bollinger lower boundary within the last 3 days. 
```
chartList.py --dir download sample.txt --filter_bbdistance 0.05,3 --days 60
```


