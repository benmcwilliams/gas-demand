# -*- coding: utf-8 -*-
"""
@author: Noemi E. Cazzaniga - 2023
@email: noemi.cazzaniga@polimi.it
"""
import eurostat

def get_avail_sdmx(**kwargs):
    if not kwargs.get('noalert', False):
        print('Alert: get_avail_sdmx is deprecated!')
    toc = eurostat.get_toc()
    return [(el[1], el[0]) for el in toc]



def get_avail_sdmx_df(**kwargs):
    if not kwargs.get('noalert', False):
        print('Alert: get_avail_sdmx_df is deprecated!')
    toc_df = eurostat.get_toc_df()
    return toc_df[['code','title']]



def subset_avail_sdmx_df(toc_df, keyword, **kwargs):
    if not kwargs.get('noalert', False):
        print('Alert: subset_avail_sdmx_df is deprecated!')
    return eurostat.subset_toc_df(toc_df, keyword)
    


def get_sdmx_dims(code, **kwargs):
    if not kwargs.get('noalert', False):
        print('Alert: get_sdmx_dims is deprecated!')
    return eurostat.get_pars(code)



def get_sdmx_dic(code, dim, **kwargs):
    if not kwargs.get('noalert', False):
        print('Alert: get_sdmx_dic is deprecated!')
    return eurostat.get_dic(code, dim, frmt='dict', full=False)



def get_sdmx_data(code, StartPeriod, EndPeriod, filter_pars, flags=False, verbose=True, **kwargs):
    if not kwargs.get('noalert', False):
        print('Alert: get_sdmx_data is deprecated!')
    filter_pars['startPeriod'] = StartPeriod
    filter_pars['endPeriod'] = EndPeriod
    dataset = eurostat.get_data(code, flags, filter_pars=filter_pars, verbose=verbose)
    i = dataset[0].index('geo\TIME_PERIOD') + 1
    for row,data in enumerate(dataset[1:]):
        for col,d in enumerate(data[i:]):
            try:
                dataset[row][col] = '{0:g}'.format(d)
            except:
                pass
    return dataset



def get_sdmx_data_df(code, StartPeriod, EndPeriod, filter_pars, flags=False, verbose=True, **kwargs):
    if not kwargs.get('noalert', False):
        print('Alert: get_sdmx_data_df is deprecated!')
    filter_pars['startPeriod'] = StartPeriod
    filter_pars['endPeriod'] = EndPeriod
    dataset_df = eurostat.get_data_df(code, flags, filter_pars=filter_pars, verbose=verbose)
    col_names = dataset_df.columns
    for c in col_names:
        try:
            dataset_df[c]= dataset_df[c].apply(str)
        except:
            pass
    return dataset_df
