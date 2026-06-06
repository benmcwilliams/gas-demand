"""
Utility functions for applying country-specific cutoff dates to monthly demand data.
"""
import pandas as pd
from src.utils.config import Config


def _latest_source_cutoff(df: pd.DataFrame, country: str, source: str) -> tuple | None:
    required_columns = {'country', 'source', 'year', 'month', 'demand'}
    if not required_columns.issubset(set(df.columns)):
        return None

    source_df = df[
        (df['country'] == country) &
        (df['source'] == source) &
        (df['demand'].notna())
    ].copy()
    if source_df.empty:
        return None

    source_df['year'] = pd.to_numeric(source_df['year'], errors='coerce')
    source_df['month'] = pd.to_numeric(source_df['month'], errors='coerce')
    source_df = source_df.dropna(subset=['year', 'month'])
    if source_df.empty:
        return None

    source_df['year_month'] = source_df['year'].astype(int) * 100 + source_df['month'].astype(int)
    latest_row = source_df.loc[source_df['year_month'].idxmax()]
    return int(latest_row['year']), int(latest_row['month'])


def _get_cutoff_for_country(df: pd.DataFrame, config: Config, country: str) -> tuple:
    country_config = config.country_cutoffs.get(country, {})
    cutoff_source = country_config.get('cutoff_source')
    if cutoff_source:
        source_cutoff = _latest_source_cutoff(df, country, cutoff_source)
        if source_cutoff:
            return source_cutoff

    return config.get_cutoff_for_country(country)


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
        cutoff_year, cutoff_month = _get_cutoff_for_country(df, config, country)
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
    default_year, default_month = config.get_cutoff_for_country('__default__')
    
    # Get all countries from config (excluding 'default')
    countries = [k for k in cutoffs.keys() if k != 'default']
    
    # Build summary
    summary_data = []
    for country in countries:
        country_config = cutoffs[country]
        cutoff_source = country_config.get('cutoff_source')
        if cutoff_source and 'year' not in country_config and 'month' not in country_config:
            cutoff_year, cutoff_month = None, None
        else:
            cutoff_year, cutoff_month = config.get_cutoff_for_country(country)

        summary_data.append({
            'country': country,
            'cutoff_year': cutoff_year,
            'cutoff_month': cutoff_month,
            'cutoff_source': cutoff_source
        })
    
    # Add default entry
    summary_data.append({
        'country': 'default (all others)',
        'cutoff_year': default_year,
        'cutoff_month': default_month,
        'cutoff_source': None
    })
    
    return pd.DataFrame(summary_data)
