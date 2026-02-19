"""
Utility functions for applying country-specific cutoff dates to monthly demand data.
"""
import pandas as pd
from src.utils.config import Config


def apply_country_cutoffs(df: pd.DataFrame, config: Config = None) -> pd.DataFrame:
    """
    Apply country-specific cutoff dates to a DataFrame with monthly demand data.
    
    The DataFrame should have columns: 'country', 'year', 'month'
    
    Args:
        df: DataFrame with monthly demand data
        config: Config instance (creates new one if not provided)
        
    Returns:
        Filtered DataFrame with country-specific cutoffs applied
    """
    if config is None:
        config = Config()
    
    # Create a mask to track which rows to keep
    mask = pd.Series([False] * len(df), index=df.index)
    
    # Apply cutoff for each country
    for country in df['country'].unique():
        cutoff_year, cutoff_month = config.get_cutoff_for_country(country)
        country_mask = (
            (df['country'] == country) &
            (
                (df['year'] < cutoff_year) |
                (
                    (df['year'] == cutoff_year) &
                    (df['month'] <= cutoff_month)
                )
            )
        )
        mask |= country_mask
    
    return df[mask].copy()


def get_cutoff_summary(config: Config = None) -> pd.DataFrame:
    """
    Get a summary of cutoff dates for all countries.
    
    Args:
        config: Config instance (creates new one if not provided)
        
    Returns:
        DataFrame with columns: country, cutoff_year, cutoff_month
    """
    if config is None:
        config = Config()
    
    cutoffs = config.country_cutoffs
    default = cutoffs.get('default', {'year': 2026, 'month': 1})
    
    # Get all countries from config (excluding 'default')
    countries = [k for k in cutoffs.keys() if k != 'default']
    
    # Build summary
    summary_data = []
    for country in countries:
        country_cutoff = cutoffs[country]
        summary_data.append({
            'country': country,
            'cutoff_year': country_cutoff.get('year', default['year']),
            'cutoff_month': country_cutoff.get('month', default['month'])
        })
    
    # Add default entry
    summary_data.append({
        'country': 'default (all others)',
        'cutoff_year': default['year'],
        'cutoff_month': default['month']
    })
    
    return pd.DataFrame(summary_data)
