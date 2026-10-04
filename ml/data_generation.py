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

Each activation record also carries client_id and category: which client
account and product line the agent was activating a customer for. These
reflect the shared platform entities described in the SRS (Section 6.1) and
are attached independently of fraud status, so they provide operational
context on an agent's profile without acting as fraud signals themselves.

Output: data/synthetic/agents.csv and data/synthetic/activation_records.csv
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

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
NUM_COLLUSION_RINGS = 3
AGENTS_PER_RING = 3

ANALYSIS_START = datetime(2026, 8, 1)
ANALYSIS_END = datetime(2026, 8, 30)


def generate_agents(num_legit, num_fraud):
    agents = []
    agent_id = 1000

    for _ in range(num_legit):
        agents.append({
            "agent_id": f"A{agent_id}",
            "registration_timestamp": fake.date_time_between(start_date="-1y", end_date="-1m"),
            "region": random.choice(REGIONS),
            "is_fraud": False
        })
        agent_id += 1

    for _ in range(num_fraud):
        agents.append({
            "agent_id": f"A{agent_id}",
            "registration_timestamp": fake.date_time_between(start_date="-6m", end_date="-2w"),
            "region": random.choice(REGIONS),
            "is_fraud": True
        })
        agent_id += 1

    return pd.DataFrame(agents)


def random_timestamp_legit(day):
    hour = int(np.clip(np.random.normal(loc=13, scale=3), 7, 19))
    minute = random.randint(0, 59)
    return day.replace(hour=hour, minute=minute, second=random.randint(0, 59))


def random_timestamp_fraud(day):
    hour = random.choice([1, 2, 3])
    minute = random.randint(0, 59)
    return day.replace(hour=hour, minute=minute, second=random.randint(0, 59))


def generate_legit_customer_id():
    return f"CUST{random.randint(100000, 999999)}"


def assign_fraud_agent_pools(fraud_agent_ids, num_rings, agents_per_ring):
    fraud_agent_ids = list(fraud_agent_ids)
    random.shuffle(fraud_agent_ids)

    ring_agents = fraud_agent_ids[: num_rings * agents_per_ring]
    remaining = fraud_agent_ids[num_rings * agents_per_ring:]

    rings = [ring_agents[i:i + agents_per_ring] for i in range(0, len(ring_agents), agents_per_ring)]

    half = len(remaining) // 2
    solo_sequential = remaining[:half]
    solo_duplicate = remaining[half:]

    return rings, solo_sequential, solo_duplicate


def generate_activation_records(agents_df):
    records = []
    record_id = 5000
    days = pd.date_range(ANALYSIS_START, ANALYSIS_END, freq="D")

    fraud_agent_ids = agents_df[agents_df["is_fraud"]]["agent_id"].tolist()
    rings, solo_sequential, solo_duplicate = assign_fraud_agent_pools(
        fraud_agent_ids, NUM_COLLUSION_RINGS, AGENTS_PER_RING
    )

    ring_pools = {}
    for i, ring in enumerate(rings):
        shared_base = random.randint(20000, 79000)
        ring_pools[i] = [f"CUST{shared_base + j}" for j in range(200)]

    ring_lookup = {}
    for i, ring in enumerate(rings):
        for agent_id in ring:
            ring_lookup[agent_id] = i

    for _, agent in agents_df.iterrows():
        agent_id_val = agent["agent_id"]

        if agent["is_fraud"]:
            daily_count_range = (15, 45)
            timestamp_fn = random_timestamp_fraud
        else:
            daily_count_range = (1, 8)
            timestamp_fn = random_timestamp_legit

        pattern = None
        if agent["is_fraud"]:
            if agent_id_val in ring_lookup:
                pattern = "collusion"
            elif agent_id_val in solo_sequential:
                pattern = "sequential"
                seq_base = random.randint(10000, 19000)
            elif agent_id_val in solo_duplicate:
                pattern = "duplicate"
                duplicate_pool = [f"CUST{random.randint(10000, 99999)}" for _ in range(20)]

        for day in days:
            if random.random() > 0.85 and not agent["is_fraud"]:
                continue

            n_submissions = random.randint(*daily_count_range)
            for _ in range(n_submissions):
                if agent["is_fraud"]:
                    if pattern == "collusion":
                        customer_id = random.choice(ring_pools[ring_lookup[agent_id_val]])
                    elif pattern == "sequential":
                        customer_id = f"CUST{seq_base}"
                        seq_base += 1
                    else:
                        customer_id = random.choice(duplicate_pool)
                else:
                    customer_id = generate_legit_customer_id()

                records.append({
                    "record_id": f"R{record_id}",
                    "agent_id": agent_id_val,
                    "timestamp": timestamp_fn(day),
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


def main():
    print("Generating synthetic agents...")
    agents_df = generate_agents(NUM_LEGIT_AGENTS, NUM_FRAUD_AGENTS)

    print("Generating synthetic activation records...")
    activations_df = generate_activation_records(agents_df)

    import os
    os.makedirs("data/synthetic", exist_ok=True)

    agents_df.to_csv("data/synthetic/agents.csv", index=False)
    activations_df.to_csv("data/synthetic/activation_records.csv", index=False)

    print(f"Done. {len(agents_df)} agents, {len(activations_df)} activation records.")
    print(f"  - Legitimate agents: {NUM_LEGIT_AGENTS}")
    print(f"  - Fraud-pattern agents: {NUM_FRAUD_AGENTS}")
    print(f"    - Collusion rings: {NUM_COLLUSION_RINGS} rings of {AGENTS_PER_RING} agents each")
    print("Saved to data/synthetic/agents.csv and data/synthetic/activation_records.csv")


if __name__ == "__main__":
    main()