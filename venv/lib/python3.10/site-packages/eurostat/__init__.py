# -*- coding: utf-8 -*-
"""
@author: Noemi E. Cazzaniga - 2024
@email: noemi.cazzaniga@polimi.it
"""

from eurostat.eurostat import get_data, get_data_df,\
                              get_dic, get_pars, get_par_values,\
                              get_requests_args, get_toc, get_toc_df,\
                              set_requests_args, setproxy, subset_toc_df
from eurostat.__old_sdmx_interface__ import get_avail_sdmx, get_avail_sdmx_df,\
                                            get_sdmx_data, get_sdmx_data_df,\
                                            get_sdmx_dic, get_sdmx_dims,\
                                            subset_avail_sdmx_df

__all__ = ['get_avail_sdmx', 'get_avail_sdmx_df', 'get_data', 'get_data_df',\
           'get_dic', 'get_pars', 'get_par_values', 'get_requests_args',\
           'get_sdmx_data', 'get_sdmx_data_df', 'get_sdmx_dic',\
           'get_sdmx_dims', 'get_toc', 'get_toc_df', 'set_requests_args',\
           'setproxy', 'subset_avail_sdmx_df', 'subset_toc_df']
