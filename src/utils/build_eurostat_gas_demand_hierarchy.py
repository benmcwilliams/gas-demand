from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT_LABEL = "Gas demand"


EXCLUDED_SUPPLY_CODES = {
    "EXP",
    "IMP",
    "IPRD",
    "IPRD_AG",
    "IPRD_CG",
    "IPRD_NAG",
    "STATDIFF",
    "STK_CHG",
    "STK_CHG_CG",
    "TOS",
    "TOS_COAL",
    "TOS_HYD",
    "TOS_OIL",
    "TOS_REN",
}


SHORT_LABELS = {
    "ID": "Inland demand",
    "IC_OBS": "Inland consumption observed",
    "IC_CAL": "Inland consumption calculated",
    "FC": "Final consumption",
    "FC_E": "Energy use",
    "FC_NE": "Non-energy use",
    "FC_IND_E": "Industry",
    "FC_IND_NE": "Industry non-energy",
    "FC_TRA_E": "Transport",
    "FC_TRA_NE": "Transport non-energy",
    "FC_OTH_E": "Other sectors",
    "FC_OTH_NE": "Other sectors non-energy",
    "FC_OTH_HH_E": "Households",
    "FC_OTH_CP_E": "Commercial and public services",
    "FC_OTH_AF_E": "Agriculture and forestry",
    "FC_OTH_A_E": "Agriculture",
    "FC_OTH_F_E": "Forestry",
    "FC_OTH_FISH_E": "Fishing",
    "FC_OTH_NSP_E": "Other sectors NSP",
    "FC_TRA_ROAD_E": "Road transport",
    "FC_TRA_PIPE_E": "Pipeline transport",
    "FC_TRA_NSP_E": "Transport NSP",
    "FC_IND_IS_E": "Iron and steel",
    "FC_IND_CPC_E": "Chemicals and petrochemicals",
    "FC_IND_NFM_E": "Non-ferrous metals",
    "FC_IND_NMM_E": "Non-metallic minerals",
    "FC_IND_TE_E": "Transport equipment",
    "FC_IND_MAC_E": "Machinery",
    "FC_IND_MQ_E": "Mining and quarrying",
    "FC_IND_FBT_E": "Food, beverages and tobacco",
    "FC_IND_PPP_E": "Paper, pulp and printing",
    "FC_IND_WP_E": "Wood and wood products",
    "FC_IND_CON_E": "Construction",
    "FC_IND_TL_E": "Textile and leather",
    "FC_IND_NSP_E": "Industry NSP",
    "FC_IND_CPC_NE": "Chemicals and petrochemicals non-energy",
    "TI_E": "Transformation input",
    "TI_EHG_MAPE_E": "Main activity electricity-only",
    "TI_EHG_MAPCHP_E": "Main activity CHP",
    "TI_EHG_MAPH_E": "Main activity heat-only",
    "TI_EHG_APE_E": "Autoproducer electricity-only",
    "TI_EHG_APCHP_E": "Autoproducer CHP",
    "TI_EHG_APH_E": "Autoproducer heat-only",
    "TI_HYDP_E": "Hydrogen production",
    "TI_BF_E": "Blast furnaces",
    "TI_CO_E": "Coke ovens",
    "TI_GW_E": "Gas works",
    "TI_GTL_E": "Gas-to-liquids",
    "TI_GTL_GTL_E": "GTL technology",
    "TI_NSP_E": "Transformation NSP",
    "NRG_E": "Energy sector own use",
    "NRG_PR_E": "Refineries",
    "NRG_OIL_NG_E": "Oil and gas extraction",
    "NRG_PLG_E": "Production/liquefaction/gasification",
    "NRG_LNG_E": "LNG terminals",
    "NRG_EHG_E": "Power and heat generation own use",
    "NRG_BF_E": "Blast furnaces own use",
    "NRG_CM_E": "Coal mines own use",
    "NRG_CO_E": "Coke ovens own use",
    "NRG_GW_E": "Gas works own use",
    "NRG_GTL_E": "Gas-to-liquids own use",
    "NRG_GTL_GTL_E": "GTL technology own use",
    "NRG_NSP_E": "Energy sector NSP",
    "TRANSL_DL": "Transmission and distribution losses",
    "TRANSL": "Transmission losses",
    "DL": "Distribution losses",
    "DL_NT": "Distribution non-technical losses",
    "VENT": "Vented",
    "FLARE": "Flared",
    "INTMARB": "International maritime bunkers",
}


def infer_parent(code: str) -> str | None:
    if code == "ID":
        return None
    if code in {"IC_OBS", "IC_CAL", "FC", "TI_E", "NRG_E", "TRANSL_DL", "VENT", "FLARE", "INTMARB"}:
        return "ID"
    if code in {"FC_E", "FC_NE"}:
        return "FC"
    if code in {"FC_IND_E", "FC_TRA_E", "FC_OTH_E"}:
        return "FC_E"
    if code in {"FC_IND_NE", "FC_TRA_NE", "FC_OTH_NE"}:
        return "FC_NE"
    if code.startswith("FC_IND_") and code not in {"FC_IND_E", "FC_IND_NE"}:
        return "FC_IND_NE" if code.endswith("_NE") else "FC_IND_E"
    if code.startswith("FC_TRA_") and code not in {"FC_TRA_E", "FC_TRA_NE"}:
        return "FC_TRA_NE" if code.endswith("_NE") else "FC_TRA_E"
    if code in {"FC_OTH_AF_E", "FC_OTH_AF_NE"}:
        return "FC_OTH_NE" if code.endswith("_NE") else "FC_OTH_E"
    if code.startswith("FC_OTH_A_") or code.startswith("FC_OTH_F_"):
        return "FC_OTH_AF_NE" if code.endswith("_NE") else "FC_OTH_AF_E"
    if code.startswith("FC_OTH_") and code not in {"FC_OTH_E", "FC_OTH_NE", "FC_OTH_AF_E", "FC_OTH_AF_NE"}:
        return "FC_OTH_NE" if code.endswith("_NE") else "FC_OTH_E"
    if code in {"TRANSL", "DL"}:
        return "TRANSL_DL"
    if code == "DL_NT":
        return "DL"
    if code.startswith("TI_") and code != "TI_E":
        return "TI_E"
    if code.startswith("NRG_") and code != "NRG_E":
        return "NRG_E"
    return None


def demand_group(code: str) -> str:
    if code in {"ID", "IC_OBS", "IC_CAL"}:
        return "reference_totals"
    if code.startswith("FC"):
        return "final_consumption"
    if code.startswith("TI_"):
        return "transformation_input"
    if code.startswith("NRG_"):
        return "energy_sector_own_use"
    if code in {"TRANSL_DL", "TRANSL", "DL", "DL_NT"}:
        return "network_losses"
    if code in {"VENT", "FLARE"}:
        return "venting_and_flaring"
    if code == "INTMARB":
        return "bunkers"
    return "exclude_supply_or_balance"


def plot_family(code: str) -> str:
    if code in {"ID", "IC_OBS", "IC_CAL"}:
        return "totals"
    if code in {"FC", "FC_E", "FC_NE"}:
        return "final_consumption"
    if code.startswith("FC_IND"):
        return "industry"
    if code.startswith("FC_OTH_HH"):
        return "households"
    if code.startswith("FC_OTH_CP"):
        return "commercial_public"
    if code.startswith("FC_OTH_AF") or code.startswith("FC_OTH_A_") or code.startswith("FC_OTH_F_") or code.startswith("FC_OTH_FISH"):
        return "agriculture_forestry_fishing"
    if code.startswith("FC_OTH"):
        return "other_sectors"
    if code.startswith("FC_TRA"):
        return "transport"
    if code.startswith("TI_EHG"):
        return "power_and_heat_generation"
    if code.startswith("TI_"):
        return "other_transformation"
    if code.startswith("NRG_"):
        return "energy_sector_own_use"
    if code in {"TRANSL_DL", "TRANSL", "DL", "DL_NT"}:
        return "losses"
    if code in {"VENT", "FLARE"}:
        return "venting_and_flaring"
    if code == "INTMARB":
        return "bunkers"
    return "excluded"


def is_included(code: str) -> bool:
    return code not in EXCLUDED_SUPPLY_CODES


def short_label(code: str, long_label: str) -> str:
    if code in SHORT_LABELS:
        return SHORT_LABELS[code]
    if long_label.startswith("Final consumption - industry sector - "):
        return long_label.replace("Final consumption - industry sector - ", "")
    if long_label.startswith("Final consumption - other sectors - "):
        return long_label.replace("Final consumption - other sectors - ", "")
    if long_label.startswith("Final consumption - transport sector - "):
        return long_label.replace("Final consumption - transport sector - ", "")
    if long_label.startswith("Transformation input - "):
        return long_label.replace("Transformation input - ", "")
    if long_label.startswith("Energy sector - "):
        return long_label.replace("Energy sector - ", "")
    return long_label


def build_hierarchy(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["include_in_demand_view"] = work["energy_balance"].map(is_included)
    work["parent_code_guess"] = work["energy_balance"].map(infer_parent)

    label_map = dict(
        zip(work["energy_balance"], work["energy_balance_label"], strict=False)
    )
    work["parent_label_guess"] = work["parent_code_guess"].map(label_map)
    work["demand_group"] = work["energy_balance"].map(demand_group)
    work["plot_family"] = work["energy_balance"].map(plot_family)
    work["plot_label_short"] = [
        short_label(code, label)
        for code, label in zip(
            work["energy_balance"],
            work["energy_balance_label"],
            strict=False,
        )
    ]

    level_cache: dict[str, int] = {}

    def compute_level(code: str) -> int:
        if code in level_cache:
            return level_cache[code]
        parent = infer_parent(code)
        if parent is None:
            level_cache[code] = 0
        else:
            level_cache[code] = compute_level(parent) + 1
        return level_cache[code]

    work["level"] = work["energy_balance"].map(compute_level)

    work["notes"] = ""
    work.loc[work["energy_balance"].isin({"IC_OBS", "IC_CAL"}), "notes"] = (
        "Reference total close to inland demand; likely avoid plotting alongside ID to prevent duplication."
    )
    work.loc[work["energy_balance"].isin(EXCLUDED_SUPPLY_CODES), "notes"] = (
        "Supply-side or balancing item; excluded from demand-focused tree."
    )
    work.loc[work["energy_balance"] == "INTMARB", "notes"] = (
        "Useful as a separate memorandum item; often excluded from inland final demand charts."
    )
    work.loc[work["energy_balance"].isin({"VENT", "FLARE"}), "notes"] = (
        "Leakage/disposal item rather than end-use demand; keep only if showing non-consumed gas uses."
    )

    cols = [
        "country",
        "year",
        "energy_balance",
        "energy_balance_label",
        "plot_label_short",
        "value",
        "include_in_demand_view",
        "demand_group",
        "plot_family",
        "level",
        "parent_code_guess",
        "parent_label_guess",
        "notes",
    ]
    work = work[cols]

    group_order = {
        "reference_totals": 0,
        "final_consumption": 1,
        "transformation_input": 2,
        "energy_sector_own_use": 3,
        "network_losses": 4,
        "venting_and_flaring": 5,
        "bunkers": 6,
        "exclude_supply_or_balance": 7,
    }
    work["_group_order"] = work["demand_group"].map(group_order).fillna(99)
    work = work.sort_values(
        ["include_in_demand_view", "_group_order", "level", "energy_balance"],
        ascending=[False, True, True, True],
    ).drop(columns="_group_order")
    return work.reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a demand-focused hierarchy for Eurostat annual gas balances."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("src/data/raw/eurostat/nrg_cb_gas_annual_eu_2024_balances.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "src/data/raw/eurostat/nrg_cb_gas_annual_eu_2024_demand_hierarchy.csv"
        ),
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    hierarchy = build_hierarchy(df)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    hierarchy.to_csv(args.output, index=False)
    print(f"Wrote {len(hierarchy)} rows to {args.output}")
    print(hierarchy.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
