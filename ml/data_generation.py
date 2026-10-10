"""
Synthetic activation data generator for the SalesMesh fraud detection system.

Fraud patterns (Concept Note; Proposal Sections 2.4.1 and 2.6):
- ring: collusion rings of varied size, hour window and shared customer pool
  (Chang et al., 2024)
- sequential: fabricated customers with incrementing ids (Tabassum et al., 2021)
- duplicate: the same few customers resubmitted
- weak: mostly normal agents with a small share of duplicate resubmissions

Hard legitimate groups: legit_night (some night work), legit_repeat (regular
repeat customers), legit_busy (high volume).

Agent ids are random and carry no label. agents.csv holds only what the
platform knows; ground truth goes to labels.csv and rings.csv, which are for
evaluation only. Rules, parameters and counts are in ml/DATA_CARD.md.

Usage: python data_generation.py [--n-agents N] [--fraud-rate R] [--seed N] [--out-dir DIR]
Output: <out-dir>/agents.csv, activation_records.csv, labels.csv, rings.csv,
        and a run folder ml/runs/<run_id>/ with run_info.json and generation_summary.csv
"""

import argparse
import random
from datetime import timedelta
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd
from faker import Faker

DEFAULT_SEED = 42
DEFAULT_N_AGENTS = 600
DEFAULT_FRAUD_RATE = 0.13
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "data" / "synthetic"

ANALYSIS_START = pd.Timestamp(2026, 8, 1)
ANALYSIS_END = pd.Timestamp(2026, 8, 30)
REGISTRATION_DAYS_BEFORE = (14, 365)

AGENT_ID_RANGE = (10000, 99999)
# 8 digits: with 6 digits, ~80k records collide by chance often enough to fake sharing.
CUSTOMER_ID_DIGITS = 8
CUSTOMER_ID_MIN = 10 ** (CUSTOMER_ID_DIGITS - 1)
CUSTOMER_ID_MAX = 10 ** CUSTOMER_ID_DIGITS - 1
RECORD_ID_START = 5000

REGIONS = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"]
# Context from other SalesMesh modules, drawn independently of fraud status.
CLIENTS = [
    "PesaLink Kenya", "FashionHub EA", "TechCorp Nairobi", "FinServe Africa",
    "MobiPay Solutions", "UrbanStyle Retail", "AgriTech Ventures", "HealthLink Kenya",
]
CATEGORIES = ["fintech", "fashion", "technology", "healthcare", "agriculture", "logistics", "e-commerce"]
STATUS_WEIGHTS = {"completed": 0.85, "pending": 0.10, "failed": 0.05}

# Shares of fraud agents; ring:sequential:duplicate keeps the v2 ratio 3:1:1.
FRAUD_PATTERN_SHARES = {"ring": 0.48, "sequential": 0.16, "duplicate": 0.16, "weak": 0.20}
# Shares of legit agents; the rest are plain "legit".
LEGIT_PATTERN_SHARES = {"legit_night": 0.08, "legit_repeat": 0.08, "legit_busy": 0.06}

LEGIT_ACTIVE_DAY_PROB = 0.85
LEGIT_DAILY_RANGE = (1, 8)
LEGIT_NIGHT_SHARE_RANGE = (0.10, 0.25)
LEGIT_REPEAT_POOL_SIZE = 8
LEGIT_REPEAT_SHARE_RANGE = (0.15, 0.50)
LEGIT_BUSY_DAILY_RANGE = (6, 14)

FRAUD_ACTIVE_DAY_PROB = 0.90
FRAUD_NORMAL_ACTIVITY_SHARE = 0.30

RING_SIZE_RANGE = (2, 6)
RING_POOL_PER_MEMBER_RANGE = (20, 75)
RING_HOUR_WIDTH_RANGE = (2, 5)
RING_DAILY_LOW_RANGE = (3, 8)
RING_DAILY_SPAN_RANGE = (5, 12)

SOLO_FRAUD_CONFIGS = {
    "sequential": {"hours": "late_night", "daily_range": (6, 18), "pool_size": 0},
    "duplicate": {"hours": "early_morning", "daily_range": (5, 15), "pool_size": 25},
    "weak": {"hours": "early_morning", "daily_range": (2, 9), "pool_size": 10},
}
WEAK_FRAUD_SHARE_RANGE = (0.10, 0.25)

fake = Faker()


class SyntheticDataset(NamedTuple):
    agents: pd.DataFrame
    activations: pd.DataFrame
    labels: pd.DataFrame
    rings: pd.DataFrame


def seed_everything(seed):
    Faker.seed(seed)
    random.seed(seed)
    np.random.seed(seed)


seed_everything(DEFAULT_SEED)


def allocate(total, shares):
    """Largest-remainder rounding of total * share for each key."""
    exact = {k: total * s for k, s in shares.items()}
    counts = {k: int(np.floor(v)) for k, v in exact.items()}
    missing = int(round(total * sum(shares.values()))) - sum(counts.values())
    for k in sorted(exact, key=lambda k: exact[k] - counts[k], reverse=True)[:missing]:
        counts[k] += 1
    return counts


def sample_hour(profile):
    if isinstance(profile, tuple):
        start, width = profile
        return (start + random.randint(0, width - 1)) % 24
    if profile == "normal":
        return int(np.clip(np.random.normal(loc=13, scale=3), 7, 19))
    if profile == "late_night":
        return random.randint(0, 4)
    if profile == "early_morning":
        return random.randint(4, 7)
    raise ValueError(f"unknown timing profile {profile!r}")


def make_timestamp(day, hour):
    return day.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))


def random_customer_id():
    return f"CUST{random.randint(CUSTOMER_ID_MIN, CUSTOMER_ID_MAX)}"


def non_consecutive_customer_ids(n):
    while True:
        numbers = sorted(random.sample(range(CUSTOMER_ID_MIN, CUSTOMER_ID_MAX + 1), n))
        if all(b - a > 1 for a, b in zip(numbers, numbers[1:])):
            random.shuffle(numbers)
            return [f"CUST{x}" for x in numbers]


def generate_agents(num_legit, num_fraud):
    """Agents with random ids and one registration-date distribution for both classes."""
    numbers = random.sample(range(AGENT_ID_RANGE[0], AGENT_ID_RANGE[1] + 1), num_legit + num_fraud)
    is_fraud = [False] * num_legit + [True] * num_fraud
    random.shuffle(is_fraud)
    agents = [{
        "agent_id": f"A{n}",
        "registration_timestamp": fake.date_time_between(
            start_date=ANALYSIS_START - timedelta(days=REGISTRATION_DAYS_BEFORE[1]),
            end_date=ANALYSIS_START - timedelta(days=REGISTRATION_DAYS_BEFORE[0]),
        ),
        "region": random.choice(REGIONS),
        "is_fraud": fraud,
    } for n, fraud in zip(numbers, is_fraud)]
    return pd.DataFrame(agents).sort_values("agent_id").reset_index(drop=True)


def make_rings(num_ring_agents):
    sizes = []
    while sum(sizes) < num_ring_agents:
        sizes.append(random.randint(*RING_SIZE_RANGE))
    if sizes:
        sizes[-1] -= sum(sizes) - num_ring_agents
        if sizes[-1] < 2:
            leftover = sizes.pop()
            if sizes:
                sizes[-1] += leftover
    rings = []
    for size in sizes:
        low = random.randint(*RING_DAILY_LOW_RANGE)
        rings.append({
            "size": size,
            "pool_size": size * random.randint(*RING_POOL_PER_MEMBER_RANGE),
            "hours": (random.randint(0, 23), random.randint(*RING_HOUR_WIDTH_RANGE)),
            "daily_range": (low, low + random.randint(*RING_DAILY_SPAN_RANGE)),
        })
    return rings


def assign_profiles(agents_df):
    """Returns ({agent_id: (profile, ring_index or None)}, rings)."""
    legit_ids = agents_df.loc[~agents_df["is_fraud"], "agent_id"].tolist()
    fraud_ids = agents_df.loc[agents_df["is_fraud"], "agent_id"].tolist()
    random.shuffle(legit_ids)
    random.shuffle(fraud_ids)

    profiles = {}
    position = 0
    for profile, count in allocate(len(legit_ids), LEGIT_PATTERN_SHARES).items():
        for agent_id in legit_ids[position:position + count]:
            profiles[agent_id] = (profile, None)
        position += count
    for agent_id in legit_ids[position:]:
        profiles[agent_id] = ("legit", None)

    fraud_counts = allocate(len(fraud_ids), FRAUD_PATTERN_SHARES)
    rings = make_rings(fraud_counts["ring"])
    fraud_counts["sequential"] += fraud_counts["ring"] - sum(r["size"] for r in rings)
    position = 0
    for ring_index, ring in enumerate(rings):
        for agent_id in fraud_ids[position:position + ring["size"]]:
            profiles[agent_id] = ("ring", ring_index)
        position += ring["size"]
    for profile in SOLO_FRAUD_CONFIGS:
        for agent_id in fraud_ids[position:position + fraud_counts[profile]]:
            profiles[agent_id] = (profile, None)
        position += fraud_counts[profile]

    return profiles, rings


def generate_activation_records(agents_df, profiles=None, rings=None):
    if profiles is None:
        profiles, rings = assign_profiles(agents_df)

    days = pd.date_range(ANALYSIS_START, ANALYSIS_END, freq="D")
    ring_pools = [non_consecutive_customer_ids(ring["pool_size"]) for ring in rings]

    records = []
    for agent in agents_df.itertuples():
        profile, ring_index = profiles[agent.agent_id]
        if agent.is_fraud:
            config = rings[ring_index] if profile == "ring" else SOLO_FRAUD_CONFIGS[profile]
            daily_range, active_prob = config["daily_range"], FRAUD_ACTIVE_DAY_PROB
            fraud_share = random.uniform(*WEAK_FRAUD_SHARE_RANGE) if profile == "weak" else 1 - FRAUD_NORMAL_ACTIVITY_SHARE
            own_pool = [random_customer_id() for _ in range(config.get("pool_size", 0))]
            seq_next = random.randint(CUSTOMER_ID_MIN, CUSTOMER_ID_MAX - 2000)
        else:
            daily_range = LEGIT_BUSY_DAILY_RANGE if profile == "legit_busy" else LEGIT_DAILY_RANGE
            active_prob, fraud_share = LEGIT_ACTIVE_DAY_PROB, 0.0
            night_share = random.uniform(*LEGIT_NIGHT_SHARE_RANGE)
            repeat_share = random.uniform(*LEGIT_REPEAT_SHARE_RANGE)
            regulars = [random_customer_id() for _ in range(LEGIT_REPEAT_POOL_SIZE)]

        for day in days:
            if random.random() > active_prob:
                continue
            for _ in range(random.randint(*daily_range)):
                if agent.is_fraud and random.random() < fraud_share:
                    hour = sample_hour(config["hours"])
                    if profile == "ring":
                        customer_id = random.choice(ring_pools[ring_index])
                    elif profile == "sequential":
                        customer_id = f"CUST{seq_next}"
                        seq_next += 1
                    else:
                        customer_id = random.choice(own_pool)
                else:
                    hour = sample_hour("normal")
                    customer_id = random_customer_id()
                    if profile == "legit_night" and random.random() < night_share:
                        hour = sample_hour("late_night")
                    if profile == "legit_repeat" and random.random() < repeat_share:
                        customer_id = random.choice(regulars)
                records.append({
                    "agent_id": agent.agent_id,
                    "timestamp": make_timestamp(day, hour),
                    "customer_id": customer_id,
                    "activation_status": random.choices(list(STATUS_WEIGHTS), weights=list(STATUS_WEIGHTS.values()))[0],
                    "client_id": random.choice(CLIENTS),
                    "category": random.choice(CATEGORIES),
                })

    activations = pd.DataFrame(records).sort_values(["timestamp", "agent_id", "customer_id"], kind="mergesort")
    activations.insert(0, "record_id", [f"R{RECORD_ID_START + i}" for i in range(len(activations))])
    return activations.reset_index(drop=True)


def ring_label(ring_index):
    return f"ring_{ring_index + 1:02d}"


def generate_dataset(seed=DEFAULT_SEED, n_agents=DEFAULT_N_AGENTS, fraud_rate=DEFAULT_FRAUD_RATE):
    if n_agents < 1 or not 0 < fraud_rate < 1:
        raise ValueError("n_agents must be positive and fraud_rate strictly between 0 and 1")
    seed_everything(seed)
    num_fraud = int(round(n_agents * fraud_rate))
    agents_df = generate_agents(n_agents - num_fraud, num_fraud)
    profiles, rings = assign_profiles(agents_df)
    activations_df = generate_activation_records(agents_df, profiles, rings)

    labels_df = pd.DataFrame({
        "agent_id": agents_df["agent_id"],
        "is_fraud": agents_df["is_fraud"],
        "profile": agents_df["agent_id"].map(lambda a: profiles[a][0]),
        "ring_id": agents_df["agent_id"].map(lambda a: "" if profiles[a][1] is None else ring_label(profiles[a][1])),
    })
    rings_df = pd.DataFrame([{
        "ring_id": ring_label(i), "size": r["size"], "pool_size": r["pool_size"],
        "hour_start": r["hours"][0], "hour_width": r["hours"][1],
        "daily_low": r["daily_range"][0], "daily_high": r["daily_range"][1],
    } for i, r in enumerate(rings)], columns=["ring_id", "size", "pool_size", "hour_start", "hour_width", "daily_low", "daily_high"])
    public_agents = agents_df[["agent_id", "registration_timestamp", "region"]]
    return SyntheticDataset(public_agents, activations_df, labels_df, rings_df)


def generator_parameters(n_agents, fraud_rate):
    return {
        "n_agents": n_agents, "fraud_rate": fraud_rate,
        "analysis_window": [str(ANALYSIS_START.date()), str(ANALYSIS_END.date())],
        "customer_id_digits": CUSTOMER_ID_DIGITS,
        "fraud_pattern_shares": FRAUD_PATTERN_SHARES, "legit_pattern_shares": LEGIT_PATTERN_SHARES,
        "legit_daily_range": LEGIT_DAILY_RANGE, "legit_active_day_prob": LEGIT_ACTIVE_DAY_PROB,
        "legit_night_share_range": LEGIT_NIGHT_SHARE_RANGE, "legit_repeat_pool_size": LEGIT_REPEAT_POOL_SIZE,
        "legit_repeat_share_range": LEGIT_REPEAT_SHARE_RANGE, "legit_busy_daily_range": LEGIT_BUSY_DAILY_RANGE,
        "fraud_active_day_prob": FRAUD_ACTIVE_DAY_PROB, "fraud_normal_activity_share": FRAUD_NORMAL_ACTIVITY_SHARE,
        "ring_size_range": RING_SIZE_RANGE, "ring_pool_per_member_range": RING_POOL_PER_MEMBER_RANGE,
        "ring_hour_width_range": RING_HOUR_WIDTH_RANGE, "ring_daily_low_range": RING_DAILY_LOW_RANGE,
        "ring_daily_span_range": RING_DAILY_SPAN_RANGE, "solo_fraud_configs": SOLO_FRAUD_CONFIGS,
        "weak_fraud_share_range": WEAK_FRAUD_SHARE_RANGE,
    }


def generation_summary(dataset):
    records = dataset.activations.groupby("agent_id").size().rename("records")
    per_agent = dataset.labels.set_index("agent_id").join(records).fillna({"records": 0})
    per_agent["class"] = np.where(per_agent["is_fraud"], "fraud", "legit")
    summary = per_agent.groupby(["class", "profile"]).agg(
        agents=("records", "size"), records=("records", "sum"),
        records_per_agent_mean=("records", "mean"),
        records_per_agent_min=("records", "min"), records_per_agent_max=("records", "max"),
    ).reset_index()
    summary["records"] = summary["records"].astype(int)
    return summary


def save_dataset(dataset, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {name: out_dir / f"{name}.csv" for name in ["agents", "activation_records", "labels", "rings"]}
    dataset.agents.to_csv(paths["agents"], index=False)
    dataset.activations.to_csv(paths["activation_records"], index=False)
    dataset.labels.to_csv(paths["labels"], index=False)
    dataset.rings.to_csv(paths["rings"], index=False)
    return paths


def main(argv=None):
    from run_utils import start_run

    parser = argparse.ArgumentParser(description="Generate synthetic SalesMesh agents and activation records.")
    parser.add_argument("--n-agents", type=int, default=DEFAULT_N_AGENTS)
    parser.add_argument("--fraud-rate", type=float, default=DEFAULT_FRAUD_RATE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    dataset = generate_dataset(args.seed, args.n_agents, args.fraud_rate)
    paths = save_dataset(dataset, args.out_dir)
    run_dir = start_run("datagen", args.seed, generator_parameters(args.n_agents, args.fraud_rate), paths.values())
    summary = generation_summary(dataset)
    summary.to_csv(run_dir / "generation_summary.csv", index=False)
    dataset.rings.to_csv(run_dir / "rings.csv", index=False)

    n_fraud = int(dataset.labels["is_fraud"].sum())
    print(f"Seed {args.seed}: {len(dataset.agents)} agents ({n_fraud} fraud, {n_fraud / len(dataset.agents):.3f}), "
          f"{len(dataset.activations)} activation records, {len(dataset.rings)} rings.")
    print(summary.round(1).to_string(index=False))
    print(dataset.rings.to_string(index=False))
    print(f"Data saved to {args.out_dir}; run folder {run_dir}")


if __name__ == "__main__":
    main()
