import pandas as pd
from typing import Dict
from src.utils.config import Config
import logging

class GermanyDemandExtractor:
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.source_the = 'the'  # Trading Hub Europe
        self.source_legacy = 'gaspool-ncg'  # Historical combined data
        
    def _clean_gaspool_data(self, gpl: pd.DataFrame) -> pd.DataFrame:
        """Process GASPOOL data and calculate demand types."""
        # Calculate demand types (converting MWh to kWh)
        gpl['small'] = (gpl['SLPsyn_H [MWh]'] + gpl['SLPsyn_L [MWh]'] + 
                       gpl['SLPana_H [MWh]'] + gpl['SLPana_L [MWh]']) * 1000
        gpl['large'] = (gpl['RLMmT_H [MWh]'] + gpl['RLMmT_L [MWh]'] + 
                       gpl['RLMoT_H [MWh]'] + gpl['RLMoT_L [MWh]']) * 1000
        gpl['total'] = gpl['small'] + gpl['large']
        
        return gpl[['Datum', 'small', 'large', 'total']]

    def _clean_ncg_data(self, ncg: pd.DataFrame) -> pd.DataFrame:
        """Process NCG data and calculate demand types."""
        # Calculate demand types (already in kWh)
        ncg['small'] = (ncg['HGasSLPsyn'] + ncg['HGasSLPana'] + 
                       ncg['LGasSLPsyn'] + ncg['LGasSLPana'])
        ncg['large'] = (ncg['HGasRLMmT'] + ncg['LGasRLMmT'] + 
                       ncg['HGasRLMoT'] + ncg['LGasRLMoT'])
        ncg['total'] = ncg['small'] + ncg['large']
        
        return ncg[['DayOfUse', 'small', 'large', 'total']]

    def _clean_the_data(self, the: pd.DataFrame) -> pd.DataFrame:
        """Process THE (Trading Hub Europe) data and calculate demand types."""
        # Calculate demand types
        the['distribution'] = (the['slPsyn_H_Gas'] + the['slPana_H_Gas'] + 
                             the['slPsyn_L_Gas'] + the['slPana_L_Gas'])
        the['industry-power'] = (the['rlMmT_H_Gas'] + the['rlMmT_L_Gas'] + 
                          the['rlMoT_H_Gas'] + the['rlMoT_L_Gas'])
        the['total'] = the['distribution'] + the['industry-power']
        
        # Convert date
        the['date'] = pd.to_datetime(the['gastag'])
        
        return the[['date', 'distribution', 'industry-power', 'total']]

    def get_demand_data(self) -> pd.DataFrame:
        """
        Retrieves German gas demand data from GASPOOL, NCG, and THE files,
        combines them and processes into the standard format.
        
        Returns:
            pd.DataFrame: DataFrame containing columns:
                - country (str): Always 'DE'
                - date (datetime): Date of the demand reading
                - demand (float): Demand value
                - type (str): One of ['distribution', 'industry', 'total']
                - source (str): Either 'the', 'gaspool-ncg', or 'gaspool'
        """
        result_dfs = []  # Initialize an empty list to hold DataFrames

        # Process THE data
        try:
            the = pd.read_csv('src/data/raw/THE_demand.csv')
            the_clean = self._clean_the_data(the)
            
            for demand_type in ['distribution', 'industry-power', 'total']:
                type_df = pd.DataFrame({
                    'country': 'DE',
                    'date': the_clean['date'],
                    'demand': the_clean[demand_type],
                    'type': demand_type,
                    'source': self.source_the
                })
                result_dfs.append(type_df)
            
            self.logger.info("Successfully processed THE data")
            
        except Exception as e:
            self.logger.warning(f"Could not process THE data: {str(e)}")

        # Process GASPOOL and NCG data
        try:
            gpl = pd.read_csv('src/data/raw/GASPOOL_historic.csv', sep=';')
            ncg = pd.read_csv('src/data/raw/NCG_historic.csv', sep=';')
            
            gpl_clean = self._clean_gaspool_data(gpl)
            ncg_clean = self._clean_ncg_data(ncg)
            
            # Merge the datasets
            merged = pd.merge(
                gpl_clean,
                ncg_clean,
                left_on='Datum',
                right_on='DayOfUse',
                suffixes=('_gpl', '_ncg')
            )
            
            # Convert date and calculate total German demand
            merged['date'] = pd.to_datetime(merged['Datum'], format='%d.%m.%Y')
            merged['distribution'] = merged['small_gpl'] + merged['small_ncg']
            merged['industry-power'] = merged['large_gpl'] + merged['large_ncg']
            merged['total'] = merged['distribution'] + merged['industry-power']
            
            for demand_type in ['distribution', 'industry-power', 'total']:
                type_df = pd.DataFrame({
                    'country': 'DE',
                    'date': merged['date'],
                    'demand': merged[demand_type],
                    'type': demand_type,
                    'source': self.source_legacy  # or 'gaspool' if you want to specify
                })
                result_dfs.append(type_df)
            
            self.logger.info("Successfully processed GASPOOL/NCG data")
            
        except Exception as e:
            self.logger.error(f"Could not process GASPOOL/NCG data: {str(e)}")

        # Combine all types
        result_df = pd.concat(result_dfs, ignore_index=True)
        
        return result_df[['country', 'date', 'demand', 'type', 'source']] 