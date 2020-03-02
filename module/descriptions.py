import os
import numpy as np
import pandas as pd
from module.stimeseries import stimeseries

class descriptions:
    def __init__(self, descriptions, data_dir, file_name, kwargs):
        self.descriptions = descriptions.copy(deep=True)
        self.data_dir = data_dir
        self.file_name = file_name
        self.kwargs_backup = kwargs
        self.kwargs = kwargs
        self.new_file_name = ""
    
    def get_new_descriptions(self):
        return self.descriptions
        
    def get_new_file_name(self):
        return self.new_file_name
        
    def work(self):
        if self.kwargs["sort_brokerrecomm"]  and "# Rating Strong Buy or Buy" in self.descriptions:
            self.descriptions = self.descriptions.sort_values(["# Rating Strong Buy or Buy"], 
                                ascending=False)
            del self.kwargs['sort_brokerrecomm']
            
        if self.kwargs["sort_industry"] and "Industry" in self.descriptions:
            self.descriptions = self.descriptions.sort_values(["Industry"])
            del self.kwargs["sort_industry"]

        if self.kwargs["sort_zacks"]:
            sort_zacks = self.kwargs["sort_zacks"]
            type=''
            cut =''
            if ',' in sort_zacks:
                list = sort_zacks.split(',')
                type, cut = list
                cut = cut.upper()
            else:
                type=sort_zacks
                            
            if   type=='V' and "Value Score" in self.descriptions:
                if cut:
                    self.descriptions = self.descriptions[ self.descriptions["Value Score"]<= cut ]
                    print (f"# {self.descriptions.shape[0]:>5} symbols meeting Value cutoff {cut}")
                self.descriptions = self.descriptions.sort_values(["Value Score"])
            elif type=='G' and "Growth Score" in self.descriptions:
                if cut:
                    self.descriptions = self.descriptions[ self.descriptions["Growth Score"]<= cut ]
                    print (f"# {self.descriptions.shape[0]:>5} symbols meeting Growth cutoff {cut}")
                self.descriptions = self.descriptions.sort_values(["Growth Score"])
            else:
                print (f"invalide input for -szk: {sort_zacks}")
                exit(1)
            del self.kwargs["sort_zacks"]
            
        if len(self.kwargs)>0:
            # load all price data to dict for iterate through later on
            dict_sts = {}        
            for symbol, row in self.descriptions.iterrows():
                price = self.data_dir+"/"+symbol+".txt"
                if os.path.exists(price):
                    price=pd.read_csv(price,sep="\t",index_col=0)
                    sts = stimeseries(price.tail(500))
                    dict_sts[symbol]=sts
                else:
                    self.descriptions = self.descriptions.drop(symbol)

            # method sort_trange
            if self.kwargs["sort_trange"]:
                argument = self.kwargs["sort_trange"]
                days, cutoff = argument.split(',')
                trange_days   = int(days)
                trange_cutoff = float(cutoff)
                self.descriptions["Sort"] = 0
                if trange_days>0:
                    #for symbol, sts in dict_sts.items:
                    for symbol, row in self.descriptions.iterrows():
                        self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].get_trading_uprange(trange_days)
                if trange_cutoff >=0:
                    self.descriptions = self.descriptions.loc[ self.descriptions["Sort"]>=trange_cutoff ]
                self.descriptions = self.descriptions.sort_values(["Sort"], ascending=False)
            print (len(self.descriptions), " symbols meet user criterion")

            # method sort_sink
            if self.kwargs["sort_sink"]:
                """ sort symbols by price change relative to a reference date
                    example: input information [5, 4]
                    set the fifth last day as reference, compare the average price of the 
                    following 4 day and report the price change
                """
                sort_sink = self.kwargs["sort_sink"]
                aa = sort_sink.split(',')
                reference_date = aa[0]
                days  = int(aa[1])
            
                self.descriptions["Sort"] = 0
                for symbol, row in self.descriptions.iterrows():
                    self.descriptions.loc[symbol, "Sort"] = dict_sts[symbol].get_referenced_change(reference_date, days)
                    
                self.descriptions = self.descriptions.sort_values(["Sort"], ascending=True)
                self.descriptions["Date Added"] = reference_date
                print ( self.descriptions["Sort"] )
            
            


        

