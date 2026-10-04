"""
Synthetic activation data generator for the SalesMesh fraud detection system.

Matches fraud behaviours described in:
- Concept Note: fake users, duplicate entries, agent collusion
- Proposal Section 2.6: submission frequency, time-of-day clustering, customer similarity
- Proposal Section 2.4.1 (Chang et al., 2024): coordinated multi-agent fraud via shared
  customer identifiers across different agent accounts

Three fraud sub-patterns are modelled, matching the literature basis:
1. Sequential identifier fraud (Tabassum et al., 2021)
2. Literal duplicate resubmission (Concept Note: "submit duplicate entries")
3. Collusion: two or more agents share overlapping customer_id values
   (Concept Note: "collude with others"; Chang et al., 2024)

Version 2 (harder, less separable data). The v1 generator made every fraud
agent trivially separable: fraud submitted only at 01:00-03:00, used 5-digit
customer ids (legit used 6-digit), submitted ~8x the legit volume, and all
three rings were the same template. v2 changes:
- The three collusion rings are structurally different (RING_CONFIGS): ring
  size (4/3/2 agents), shared pool size (300/120/40 customers), submission
  timing (late night / evening / business hours) and daily volume all vary.
- Fraud agents mix in normal-looking activity (FRAUD_NORMAL_ACTIVITY_SHARE of
  their submissions use a fresh customer id at a normal daytime hour) and skip
  some days, so no fraud agent is a pure pattern.
- Fraud daily volume overlaps the legit range instead of sitting far above it.
- A handful of legitimate agents overlap fraud behaviour: some submit
  occasionally at night, some have regular repeat customers, some are simply
  high-volume.
- Every customer id is a 6-digit CUSTnnnnnn for every agent, so id length no
  longer encodes the label.
- Registration dates are relative to ANALYSIS_START rather than "now", so the
  output is identical whenever it is regenerated with the same seed.

agents.csv also carries `profile` (e.g. legit, legit_night, ring_1,
sequential) and `ring_id`. These are ground-truth labels for evaluation and
analysis only: no feature or model may read them.

Each activation record also carries client_id and category: which client
account and product line the agent was activating a customer for. These
reflect the shared platform entities described in the SRS (Section 6.1) and
are attached independently of fraud status, so they provide operational
context on an agent's profile without acting as fraud signals themselves.

Usage: python data_generation.py [--seed N] [--out-dir DIR]
Output: <out-dir>/agents.csv and <out-dir>/activation_records.csv
        (default out-dir: data/synthetic next to this file)
"""

import argparse
import random
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

DEFAULT_SEED = 42
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "data" / "synthetic"

fake = Faker()


def seed_everything(seed):
    """Seeds every random source the generator uses, so a seed fully determines the output."""
    Faker.seed(seed)
    random.seed(seed)
    np.random.seed(seed)


seed_everything(DEFAULT_SEED)

REGIONS = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"]

# client_id and category are pass-through context from other SalesMesh modules
# (client management, catalogue) -- this service doesn't own them. An agent
# works across multiple clients and categories (SRS), so they're assigned per
# activation record, independent of fraud status: realistic context, not a
# fraud signal.
CLIENTS = [
    "PesaLink Kenya", "FashionHub EA", "TechCorp Nairobi", "FinServe Africa",
    "MobiPay Solutions", "UrbanStyle Retail", "AgriTech Ventures", "HealthLink Kenya",
]

CATEGORIES = ["fintech", "fashion", "technology", "healthcare", "agriculture", "logistics", "e-commerce"]

NUM_LEGIT_AGENTS = 100
NUM_FRAUD_AGENTS = 15

ANALYSIS_START = pd.Timestamp(2026, 8, 1)
ANALYSIS_END = pd.Timestamp(2026, 8, 30)

# Every customer id, legit or fraud, is CUST + 6 digits.
CUSTOMER_ID_MIN = 100000
CUSTOMER_ID_MAX = 999999

# --- Legitimate agents ---
LEGIT_DAILY_RANGE = (1, 8)
LEGIT_ACTIVE_DAY_PROB = 0.85

# A handful of legit agents overlap fraud behaviour (disjoint groups):
LEGIT_NIGHT_AGENTS = 6         # occasionally submit late at night
LEGIT_NIGHT_SHARE = 0.15       # share of their submissions at 00:00-04:59
LEGIT_REPEAT_AGENTS = 6        # have regular repeat customers
LEGIT_REPEAT_POOL_SIZE = 8     # size of each such agent's regular-customer list
# Share of their submissions to a regular customer, drawn per agent: some legit
# agents (renewals, top-ups) reuse customers heavily.
LEGIT_REPEAT_SHARE_RANGE = (0.15, 0.50)
LEGIT_BUSY_AGENTS = 4          # high-volume but otherwise normal
LEGIT_BUSY_DAILY_RANGE = (6, 14)

# --- Fraudulent agents ---
FRAUD_ACTIVE_DAY_PROB = 0.90
# Share of each fraud agent's submissions that look normal (fresh customer id,
# normal daytime hour), so fraud agents are not pure patterns.
FRAUD_NORMAL_ACTIVITY_SHARE = 0.30

# Three structurally different rings (9 agents in total).
RING_CONFIGS = [
    {"size": 4, "pool_size": 300, "hours": "late_night", "daily_range": (8, 20)},
    {"size": 3, "pool_size": 120, "hours": "evening", "daily_range": (5, 14)},
    {"size": 2, "pool_size": 40, "hours": "business", "daily_range": (3, 10)},
]
NUM_COLLUSION_RINGS = len(RING_CONFIGS)

# The remaining 6 fraud agents are split evenly between the two solo patterns.
SEQUENTIAL_CONFIG = {"hours": "late_night", "daily_range": (6, 18)}
DUPLICATE_CONFIG = {"hours": "early_morning", "daily_range": (5, 15), "pool_size": 25}


def sample_hour(profile):
    """Submission hour for a timing profile."""
    if profile == "normal":
        return int(np.clip(np.random.normal(loc=13, scale=3), 7, 19))
    if profile == "business":
        return int(np.clip(np.random.normal(loc=14, scale=2), 8, 18))
    if profile == "late_night":
        return random.randint(0, 4)
    if profile == "early_morning":
        return random.randint(4, 7)
    if profile == "evening":
        return random.randint(18, 23)
    raise ValueError(f"unknown timing profile {profile!r}")


def make_timestamp(day, hour):
    return day.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))


def random_customer_id():
    return f"CUST{random.randint(CUSTOMER_ID_MIN, CUSTOMER_ID_MAX)}"


def generate_agents(num_legit, num_fraud):
    agents = []
    agent_id = 1000

    for _ in range(num_legit):
        agents.append({
            "agent_id": f"A{agent_id}",
            "registration_timestamp": fake.date_time_between(
                start_date=ANALYSIS_START - timedelta(days=365), end_date=ANALYSIS_START - timedelta(days=30)
            ),
            "region": random.choice(REGIONS),
            "is_fraud": False,
        })
        agent_id += 1

    for _ in range(num_fraud):
        agents.append({
            "agent_id": f"A{agent_id}",
            "registration_timestamp": fake.date_time_between(
                start_date=ANALYSIS_START - timedelta(days=180), end_date=ANALYSIS_START - timedelta(days=14)
            ),
            "region": random.choice(REGIONS),
            "is_fraud": True,
        })
        agent_id += 1

    return pd.DataFrame(agents)


def assign_profiles(agents_df):
    """
    Returns {agent_id: (profile, ring_index or None)} for every agent.

    Legit agents: LEGIT_NIGHT/REPEAT/BUSY_AGENTS of them get an overlapping
    profile, the rest are plain "legit". Fraud agents: rings filled in
    RING_CONFIGS order, the remainder split between sequential and duplicate.
    """
    legit_ids = agents_df[~agents_df["is_fraud"]]["agent_id"].tolist()
    fraud_ids = agents_df[agents_df["is_fraud"]]["agent_id"].tolist()
    random.shuffle(legit_ids)
    random.shuffle(fraud_ids)

    profiles = {}
    special = (
        ["legit_night"] * LEGIT_NIGHT_AGENTS
        + ["legit_repeat"] * LEGIT_REPEAT_AGENTS
        + ["legit_busy"] * LEGIT_BUSY_AGENTS
    )
    for i, agent_id in enumerate(legit_ids):
        profiles[agent_id] = (special[i] if i < len(special) else "legit", None)

    position = 0
    for ring_index, config in enumerate(RING_CONFIGS):
        for agent_id in fraud_ids[position:position + config["size"]]:
            profiles[agent_id] = (f"ring_{ring_index + 1}", ring_index)
        position += config["size"]

    remaining = fraud_ids[position:]
    half = len(remaining) // 2
    for agent_id in remaining[:half]:
        profiles[agent_id] = ("sequential", None)
    for agent_id in remaining[half:]:
        profiles[agent_id] = ("duplicate", None)

    return profiles


def generate_activation_records(agents_df, profiles=None):
    """
    Generates activation records for every agent. `profiles` (from
    assign_profiles) is drawn here when not supplied.
    """
    if profiles is None:
        profiles = assign_profiles(agents_df)

    days = pd.date_range(ANALYSIS_START, ANALYSIS_END, freq="D")

    ring_pools = []
    for config in RING_CONFIGS:
        base = random.randint(CUSTOMER_ID_MIN, CUSTOMER_ID_MAX - config["pool_size"])
        ring_pools.append([f"CUST{base + j}" for j in range(config["pool_size"])])

    records = []
    record_id = 5000

    for _, agent in agents_df.iterrows():
        agent_id = agent["agent_id"]
        profile, ring_index = profiles[agent_id]

        # Per-agent state for the pattern-specific customer-id generators.
        seq_next = random.randint(CUSTOMER_ID_MIN, CUSTOMER_ID_MAX - 2000)
        duplicate_pool = [random_customer_id() for _ in range(DUPLICATE_CONFIG["pool_size"])]
        regulars = [random_customer_id() for _ in range(LEGIT_REPEAT_POOL_SIZE)]
        repeat_share = random.uniform(*LEGIT_REPEAT_SHARE_RANGE)

        if agent["is_fraud"]:
            if ring_index is not None:
                config = RING_CONFIGS[ring_index]
            elif profile == "sequential":
                config = SEQUENTIAL_CONFIG
            else:
                config = DUPLICATE_CONFIG
            daily_range = config["daily_range"]
            active_prob = FRAUD_ACTIVE_DAY_PROB
        else:
            daily_range = LEGIT_BUSY_DAILY_RANGE if profile == "legit_busy" else LEGIT_DAILY_RANGE
            active_prob = LEGIT_ACTIVE_DAY_PROB

        for day in days:
            if random.random() > active_prob:
                continue

            for _ in range(random.randint(*daily_range)):
                if agent["is_fraud"]:
                    if random.random() < FRAUD_NORMAL_ACTIVITY_SHARE:
                        customer_id, hour = random_customer_id(), sample_hour("normal")
                    else:
                        hour = sample_hour(config["hours"])
                        if ring_index is not None:
                            customer_id = random.choice(ring_pools[ring_index])
                        elif profile == "sequential":
                            customer_id = f"CUST{seq_next}"
                            seq_next += 1
                        else:
                            customer_id = random.choice(duplicate_pool)
                else:
                    hour = sample_hour("normal")
                    if profile == "legit_night" and random.random() < LEGIT_NIGHT_SHARE:
                        hour = sample_hour("late_night")
                    if profile == "legit_repeat" and random.random() < repeat_share:
                        customer_id = random.choice(regulars)
                    else:
                        customer_id = random_customer_id()

                records.append({
                    "record_id": f"R{record_id}",
                    "agent_id": agent_id,
                    "timestamp": make_timestamp(day, hour),
                    "customer_id": customer_id,
                    "activation_status": random.choices(
                        ["completed", "pending", "failed"], weights=[0.85, 0.1, 0.05]
                    )[0],
                    # Independent of fraud status/pattern -- context, not a fraud signal.
                    "client_id": random.choice(CLIENTS),
                    "category": random.choice(CATEGORIES),
                })
                record_id += 1

    return pd.DataFrame(records)


def generate_dataset(seed=DEFAULT_SEED):
    """Returns (agents_df, activations_df) for a seed; agents_df includes the profile labels."""
    seed_everything(seed)
    agents_df = generate_agents(NUM_LEGIT_AGENTS, NUM_FRAUD_AGENTS)
    profiles = assign_profiles(agents_df)
    activations_df = generate_activation_records(agents_df, profiles)
    agents_df["profile"] = agents_df["agent_id"].map(lambda a: profiles[a][0])
    agents_df["ring_id"] = agents_df["agent_id"].map(
        lambda a: f"ring_{profiles[a][1] + 1}" if profiles[a][1] is not None else ""
    )
    return agents_df, activations_df


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    print(f"Generating synthetic agents and activation records (seed {args.seed})...")
    agents_df, activations_df = generate_dataset(args.seed)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    agents_df.to_csv(args.out_dir / "agents.csv", index=False)
    activations_df.to_csv(args.out_dir / "activation_records.csv", index=False)

    print(f"Done. {len(agents_df)} agents, {len(activations_df)} activation records.")
    print(agents_df["profile"].value_counts().to_string())
    print(f"Saved to {args.out_dir / 'agents.csv'} and {args.out_dir / 'activation_records.csv'}")


if __name__ == "__main__":
    main()
