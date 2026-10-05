"""Plot stored and proposed monthly EU/Europe aggregates from an audit CSV."""
import argparse
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

SECTORS = [('total', 'Total'), ('industry', 'Industry'), ('power', 'Power'),
           ('household', 'Households'), ('industry-household', 'Industry–household')]


def plot_comparison(input_path: Path, output_dir: Path):
    data = pd.read_csv(input_path)
    data['date'] = pd.to_datetime(dict(year=data.year, month=data.month, day=1))
    data = data.sort_values('date')
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(5, 2, figsize=(15, 15), sharex=True, sharey='row')
    blue, grey = '#0066A6', '#B35732'
    for row, (sector, label) in enumerate(SECTORS):
        for col, area in enumerate(['EU', 'EU+UK']):
            ax = axes[row, col]
            selected = data[(data.country == area) & (data.type == sector)].set_index('date')
            # Explicit monthly grid preserves gaps rather than joining across them.
            dates = pd.date_range(data.date.min(), data.date.max(), freq='MS')
            selected = selected.reindex(dates)
            ax.plot(dates, selected.demand, color=blue, linewidth=1.8, zorder=2)
            ax.plot(dates, selected.legacy_demand, color=grey, linewidth=1.3,
                    linestyle=(0, (4, 3)), alpha=.9, zorder=3)
            ax.grid(axis='y', color='#E1E5EA', linewidth=.6)
            ax.set_axisbelow(True)
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax.tick_params(axis='x', labelbottom=True, length=0, pad=6)
            ax.tick_params(axis='y', length=0)
            ax.spines['left'].set_visible(False)
            ax.spines['bottom'].set_color('#D1D6DC')
            ax.set_title(label, loc='left', fontsize=12, fontweight='bold', pad=8)
            if col == 0:
                ax.set_ylabel('TWh / month', color='#4B5563')
            if selected.demand.iloc[-1] != selected.demand.iloc[-1]:
                ax.text(.99, .94, 'Sep 2026 withheld', transform=ax.transAxes,
                        ha='right', va='top', fontsize=9, color='#596574',
                        bbox=dict(facecolor='white', edgecolor='none', alpha=.85, pad=2))
        row_values = data[data.type == sector][['demand', 'legacy_demand']]
        axes[row, 0].set_ylim(0, row_values.max().max() * 1.12)
    axes[0, 0].text(.5, 1.12, 'EU', transform=axes[0, 0].transAxes,
                    ha='center', fontsize=15, fontweight='bold')
    axes[0, 1].text(.5, 1.12, 'Europe (EU + UK)', transform=axes[0, 1].transAxes,
                    ha='center', fontsize=15, fontweight='bold')
    axes[-1, 0].set_xlim(data.date.min() - pd.Timedelta(days=20),
                        data.date.max() + pd.Timedelta(days=35))
    fig.suptitle('Monthly gas demand: existing vs proposed aggregates',
                 x=.065, y=.986, ha='left', fontsize=20, fontweight='bold')
    fig.text(.065, .957, 'January 2019–September 2026 · Proposed series uses country data after the Energy Charts backfill',
             fontsize=10.5, color='#4B5563')
    fig.legend(handles=[Line2D([0], [0], color=blue, linewidth=2, label='Proposed aggregate'),
                        Line2D([0], [0], color=grey, linewidth=1.5, linestyle='--', label='Existing MongoDB aggregate')],
               loc='upper left', bbox_to_anchor=(.06, .947), frameon=False, ncol=2)
    fig.subplots_adjust(left=.065, right=.985, top=.89, bottom=.065, hspace=.40, wspace=.12)
    fig.text(.065, .025,
             'Existing aggregates end in July 2026. Proposed September household, industry and industry–household values are withheld.\n'
             'Proposed series includes flagged imputations. EU coverage follows the tracker’s reporting countries; UK has no combined industry–household series.',
             fontsize=9, color='#4B5563', linespacing=1.6)
    stem = output_dir / 'eu_europe_monthly_aggregate_comparison'
    fig.savefig(stem.with_suffix('.png'), dpi=160, facecolor='white')
    fig.savefig(stem.with_suffix('.svg'), facecolor='white')
    plt.close(fig)
    print(stem.with_suffix('.png').resolve())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path,
                        default=Path('src/data/analyzed/aggregate_fallback_check/legacy_comparison.csv'))
    parser.add_argument('--output-dir', type=Path,
                        default=Path('src/data/analyzed/aggregate_fallback_check/figures'))
    args = parser.parse_args()
    plot_comparison(args.input, args.output_dir)
