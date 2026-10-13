"""
Synthetic activation data generator for the SalesMesh fraud detection system
(U-CS 56, AI Fraud Detection). Change #5 (integrity rules R1-R6 and context
fields) is the final change: see ml/DATA_CARD.md.

Fraud patterns (Concept Note; Proposal Sections 2.4.1 and 2.6):
- ring: collusion rings of varied size, hour window and shared customer pool
  (Chang et al., 2024)
- weak_ring: rings with legit-like volume that share only a few customers
- sequential: fabricated customers with incrementing ids (Tabassum et al., 2021)
- duplicate: the same customer resubmitted for the same client
- weak: mostly normal agents with a small share of duplicate resubmissions

Hard legitimate groups: legit_night, legit_repeat (cross sell plus retries),
legit_busy. Any agent may serve its county's popular customers, so honest agents
share customers across different clients.

Integrity rules (enforced while generating, not by filtering):
R1 an honest (customer, client) pair is used by no other agent;
R2 an honest agent repeats a pair only as a retry after a failed or pending
   attempt, with at most one completed activation per pair;
R3 popular pool customers are skipped when the pair is already taken;
R4 only the planted fraud patterns break R1 and R2;
R5 activations only in certified categories, after registration and certification;
R6 pending only in the last PENDING_WINDOW_HOURS of the window.
The normal (non-pattern) submissions of every agent, honest or fraud, follow
R1-R3 through one code path.

Context fields (account_status, identity, certifications, quality_score,
commission) come from separate RNG streams spawned from the seed, with the same
distributions for every agent, so they cannot change behaviour draws.

region is one of Kenya's 47 counties (population weighted, at least
COUNTY_MIN_AGENTS each). Each agent works with 1-3 clients from a fixed
reference list; a record's category is its client's category. County, clients
and categories are drawn independently of the label.

Timestamps are naive local time in TIMEZONE. agents.csv holds only what the
platform knows; ground truth goes to labels.csv and rings.csv (evaluation only).

Usage: python data_generation.py [--n-agents N] [--fraud-rate R] [--seed N] [--out-dir DIR]
Output: <out-dir>/agents.csv, agent_identity.csv, agent_categories.csv, activation_records.csv,
        clients.csv, labels.csv, rings.csv, and ml/runs/<run_id>/ with run_info.json,
        generation_summary.csv and data_checks.json
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
DEFAULT_N_AGENTS = 1000
DEFAULT_FRAUD_RATE = 0.13
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "data" / "synthetic"

TIMEZONE = "Africa/Nairobi"
ANALYSIS_START = pd.Timestamp(2026, 8, 1)
ANALYSIS_END = pd.Timestamp(2026, 8, 30)
REGISTRATION_DAYS_BEFORE = (14, 365)

AGENT_ID_RANGE = (10000, 99999)
# 8 digits: with 6 digits, ~80k records collide by chance often enough to fake sharing.
CUSTOMER_ID_DIGITS = 8
CUSTOMER_ID_MIN = 10 ** (CUSTOMER_ID_DIGITS - 1)
CUSTOMER_ID_MAX = 10 ** CUSTOMER_ID_DIGITS - 1
RECORD_ID_START = 5000

# Rough 2019 census population (thousands), used as agent weights per county.
COUNTY_POPULATION_THOUSANDS = {
    "Mombasa": 1209, "Kwale": 867, "Kilifi": 1453, "Tana River": 316, "Lamu": 143, "Taita-Taveta": 341,
    "Garissa": 841, "Wajir": 781, "Mandera": 867,
    "Marsabit": 459, "Isiolo": 268, "Meru": 1545, "Tharaka-Nithi": 393, "Embu": 608, "Kitui": 1136,
    "Machakos": 1422, "Makueni": 987,
    "Nyandarua": 638, "Nyeri": 759, "Kirinyaga": 610, "Murang'a": 1056, "Kiambu": 2417,
    "Turkana": 926, "West Pokot": 621, "Samburu": 310, "Trans Nzoia": 991, "Uasin Gishu": 1163,
    "Elgeyo-Marakwet": 454, "Nandi": 886, "Baringo": 667, "Laikipia": 518, "Nakuru": 2162, "Narok": 1158,
    "Kajiado": 1118, "Kericho": 902, "Bomet": 876,
    "Kakamega": 1868, "Vihiga": 591, "Bungoma": 1671, "Busia": 894,
    "Siaya": 993, "Kisumu": 1156, "Homa Bay": 1132, "Migori": 1116, "Kisii": 1266, "Nyamira": 605,
    "Nairobi": 4397,
}
COUNTY_MIN_AGENTS = 2
FORMER_PROVINCE_COUNTIES = {
    "Coast": ["Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita-Taveta"],
    "North Eastern": ["Garissa", "Wajir", "Mandera"],
    "Eastern": ["Marsabit", "Isiolo", "Meru", "Tharaka-Nithi", "Embu", "Kitui", "Machakos", "Makueni"],
    "Central": ["Nyandarua", "Nyeri", "Kirinyaga", "Murang'a", "Kiambu"],
    "Rift Valley": ["Turkana", "West Pokot", "Samburu", "Trans Nzoia", "Uasin Gishu", "Elgeyo-Marakwet", "Nandi",
                    "Baringo", "Laikipia", "Nakuru", "Narok", "Kajiado", "Kericho", "Bomet"],
    "Western": ["Kakamega", "Vihiga", "Bungoma", "Busia"],
    "Nyanza": ["Siaya", "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira"],
    "Nairobi": ["Nairobi"],
}
COUNTY_TO_FORMER_PROVINCE = {c: p for p, counties in FORMER_PROVINCE_COUNTIES.items() for c in counties}
COUNTIES = list(COUNTY_POPULATION_THOUSANDS)
COUNTY_WEIGHTS = list(COUNTY_POPULATION_THOUSANDS.values())

# Reference list only: which business a customer is being onboarded to.
CATEGORIES = [
    "banking", "mobile money", "insurance", "SACCO", "e-commerce", "fashion",
    "telecom", "healthcare", "education", "logistics", "agritech", "real estate",
]
# client_id -> (name, category, weight)
CLIENTS = {
    "CL01": ("Client 01", "banking", 8), "CL02": ("Client 02", "banking", 6),
    "CL03": ("Client 03", "mobile money", 10), "CL04": ("Client 04", "mobile money", 8),
    "CL05": ("Client 05", "insurance", 5), "CL06": ("Client 06", "insurance", 3),
    "CL07": ("Client 07", "SACCO", 5), "CL08": ("Client 08", "SACCO", 3),
    "CL09": ("Client 09", "e-commerce", 6), "CL10": ("Client 10", "e-commerce", 4),
    "CL11": ("Client 11", "fashion", 3),
    "CL12": ("Client 12", "telecom", 9), "CL13": ("Client 13", "telecom", 6),
    "CL14": ("Client 14", "healthcare", 4),
    "CL15": ("Client 15", "education", 3), "CL16": ("Client 16", "education", 2),
    "CL17": ("Client 17", "logistics", 3),
    "CL18": ("Client 18", "agritech", 4), "CL19": ("Client 19", "agritech", 2),
    "CL20": ("Client 20", "real estate", 2),
}
CLIENT_CATEGORY = {cid: c[1] for cid, c in CLIENTS.items()}
AGENT_CLIENT_COUNT_WEIGHTS = {1: 0.45, 2: 0.40, 3: 0.15}
EXTRA_CLIENT_SAME_CATEGORY_PROB = 0.6
CLIENT_MIX_DIRICHLET_ALPHA = 2.0
# Cross sell: the same customer for a different client of the same agent; allowed, but rare.
CROSS_CLIENT_REPEAT_PROB = 0.02

# R6: pending only in the last PENDING_WINDOW_HOURS; older records are completed or failed (17:1).
RESOLVED_STATUS_WEIGHTS = {"completed": 0.85, "failed": 0.05}
PENDING_WINDOW_HOURS = 72
PENDING_PROB_IN_WINDOW = 0.30
# R2: share of failed or pending normal attempts that the agent retries on a later active day.
RETRY_PROB = 0.6
POPULAR_PICK_TRIES = 30
CROSS_SELL_TRIES = 20

# Popular customers per county (e.g. shops, families served by several agents).
POPULAR_POOL_PER_AGENT = 10
POPULAR_POOL_MIN = 20
POPULAR_POOL_USER_PROB = 0.35
POPULAR_POOL_SHARE_RANGE = (0.03, 0.15)

# Shares of fraud agents; all rings : sequential : duplicate keeps the v2 ratio 3:1:1.
FRAUD_PATTERN_SHARES = {"ring": 0.32, "weak_ring": 0.16, "sequential": 0.16, "duplicate": 0.16, "weak": 0.20}
# Shares of legit agents; the rest are plain "legit".
LEGIT_PATTERN_SHARES = {"legit_night": 0.08, "legit_repeat": 0.08, "legit_busy": 0.06}

# Applied to every agent, legit or fraud (label-aware change #4: no class-specific caps or clips).
ACTIVE_DAY_PROB_RANGE = (0.75, 0.95)
# Daily count ~ negative binomial(mean = agent rate, dispersion); heavy right tail, no cap.
DAILY_COUNT_DISPERSION = 3.0
# Agent rate = group median x lognormal(0, sigma).
AGENT_RATE_SIGMA = 0.25
# Normal hours: Normal(mean, sd) kept inside 0-23 by resampling (no clip), plus a
# per-agent share of submissions at a uniformly random hour.
NORMAL_HOUR_MEAN = 13
NORMAL_HOUR_SD = 3
OFF_HOURS_SHARE_RANGE = (0.01, 0.06)

LEGIT_DAILY_MEDIAN = 4.5
LEGIT_BUSY_DAILY_MEDIAN = 10.0
LEGIT_NIGHT_SHARE_RANGE = (0.10, 0.25)
# legit_repeat: this share of normal submissions cross sells an earlier customer to another
# client (a single-client agent gets one extra cross-sell client); due retries come first.
LEGIT_REPEAT_SHARE_RANGE = (0.15, 0.50)

# Per agent share of pattern submissions for ring, sequential and duplicate (mean 0.70).
FRAUD_PATTERN_SHARE_RANGE = (0.55, 0.85)

RING_SIZE_RANGE = (2, 6)
RING_POOL_PER_MEMBER_RANGE = (20, 75)
RING_HOUR_WIDTH_RANGE = (2, 5)
RING_DAILY_MEDIAN_RANGE = (5.0, 12.0)
WEAK_RING_POOL_PER_MEMBER_RANGE = (5, 15)
WEAK_RING_SHARE_RANGE = (0.08, 0.20)
WEAK_RING_DAILY_MEDIAN_RANGE = (2.5, 5.0)

SOLO_FRAUD_CONFIGS = {
    "sequential": {"hours": "late_night", "daily_median": 12.0, "pool_size_range": (0, 0)},
    "duplicate": {"hours": "early_morning", "daily_median": 10.0, "pool_size_range": (15, 35)},
    "weak": {"hours": "early_morning", "daily_median": None, "pool_size_range": (5, 15)},
}
WEAK_FRAUD_SHARE_RANGE = (0.10, 0.25)
# Weak fraud: a random elevated rate, LEGIT_DAILY_MEDIAN x this multiplier.
WEAK_FRAUD_RATE_MULTIPLIER_RANGE = (1.15, 1.6)

# Context fields (illustrative values; same distributions for every agent).
COMMISSION_PER_ACTIVATION_KES = {
    "banking": 250, "mobile money": 60, "insurance": 300, "SACCO": 200, "e-commerce": 80, "fashion": 50,
    "telecom": 40, "healthcare": 150, "education": 120, "logistics": 70, "agritech": 100, "real estate": 400,
}
ACCOUNT_STATUS_WEIGHTS = {"active": 0.94, "suspended": 0.06}
EXPIRED_CATEGORY_PROB = 0.08
QUALITY_AGENT_MEAN = 80.0
QUALITY_AGENT_SD = 5.0
QUALITY_RECORD_SD = 8.0
QUALITY_FAILED_PENALTY = 15.0
PHONE_PREFIX = "+2547"
PHONE_DIGITS = 8
NATIONAL_ID_DIGITS = 8
CONTEXT_STREAMS = ["identity", "account_status", "certifications", "quality"]
# Fictional identities: random combinations of common Kenyan names.
FIRST_NAMES = [
    "John", "Mary", "Peter", "Grace", "James", "Jane", "Joseph", "Faith", "David", "Mercy",
    "Samuel", "Esther", "Daniel", "Ann", "Paul", "Lucy", "Stephen", "Joyce", "Michael", "Caroline",
    "Brian", "Sharon", "Kevin", "Purity", "Dennis", "Winnie", "Collins", "Cynthia", "Victor", "Brenda",
    "Kennedy", "Agnes", "Francis", "Eunice", "George", "Margaret", "Patrick", "Catherine", "Joshua", "Naomi",
    "Moses", "Rose", "Wanjiru", "Wambui", "Njeri", "Muthoni", "Akinyi", "Atieno", "Achieng", "Chebet",
    "Cherono", "Kibet", "Kiprotich", "Nafula", "Nekesa", "Halima", "Amina", "Fatuma", "Abdi", "Hassan",
    "Zawadi", "Baraka", "Imani", "Neema", "Juma", "Rehema", "Mwende", "Kanini", "Wairimu", "Nyokabi",
]
LAST_NAMES = [
    "Mwangi", "Kamau", "Otieno", "Odhiambo", "Ochieng", "Omondi", "Wanjiku", "Njoroge", "Kariuki", "Kiprop",
    "Kipkemboi", "Cheruiyot", "Kimani", "Mutua", "Musyoka", "Wafula", "Wekesa", "Barasa", "Simiyu", "Nyongesa",
    "Onyango", "Owino", "Okoth", "Ouma", "Odera", "Koech", "Rotich", "Langat", "Kiplagat", "Mutai",
    "Chepkoech", "Maina", "Ndungu", "Githinji", "Gitau", "Macharia", "Waweru", "Kinyua", "Muriuki", "Mugo",
    "Nyaga", "Njiru", "Kioko", "Mbugua", "Wambugu", "Ndirangu", "Ombati", "Nyamweya", "Moraa", "Momanyi",
    "Abdullahi", "Mohamed", "Omar", "Mutiso", "Kilonzo", "Nzioka", "Muli", "Kahindi", "Charo", "Katana",
    "Ekai", "Lokuruka", "Lemayian", "Sankale", "Kerubo", "Nyakundi", "Kibe", "Muthee", "Ngugi", "Chege",
]

fake = Faker()


class SyntheticDataset(NamedTuple):
    agents: pd.DataFrame
    activations: pd.DataFrame
    labels: pd.DataFrame
    rings: pd.DataFrame
    clients: pd.DataFrame
    identity: pd.DataFrame
    agent_categories: pd.DataFrame


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


def sample_hour(profile, off_hours_share=0.0):
    if isinstance(profile, tuple):
        start, width = profile
        return (start + random.randint(0, width - 1)) % 24
    if profile == "normal":
        if random.random() < off_hours_share:
            return random.randint(0, 23)
        while True:
            hour = int(np.floor(np.random.normal(NORMAL_HOUR_MEAN, NORMAL_HOUR_SD)))
            if 0 <= hour <= 23:
                return hour
    if profile == "late_night":
        return random.randint(0, 4)
    if profile == "early_morning":
        return random.randint(4, 7)
    raise ValueError(f"unknown timing profile {profile!r}")


def daily_count(rate):
    return int(np.random.negative_binomial(DAILY_COUNT_DISPERSION, DAILY_COUNT_DISPERSION / (DAILY_COUNT_DISPERSION + rate)))


def agent_rate(median):
    return median * float(np.random.lognormal(0.0, AGENT_RATE_SIGMA))


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


def draw_counties(n):
    """COUNTY_MIN_AGENTS per county (fewer if n is too small), the rest by population."""
    floor = min(COUNTY_MIN_AGENTS, n // len(COUNTIES))
    counties = [c for c in COUNTIES for _ in range(floor)]
    counties += random.choices(COUNTIES, weights=COUNTY_WEIGHTS, k=n - len(counties))
    random.shuffle(counties)
    return counties


def draw_agent_clients():
    """1-3 clients, extra clients mostly from the primary client's category."""
    ids, weights = list(CLIENTS), [c[2] for c in CLIENTS.values()]
    n = random.choices(list(AGENT_CLIENT_COUNT_WEIGHTS), weights=list(AGENT_CLIENT_COUNT_WEIGHTS.values()))[0]
    chosen = [random.choices(ids, weights=weights)[0]]
    while len(chosen) < n:
        same = [c for c in ids if CLIENT_CATEGORY[c] == CLIENT_CATEGORY[chosen[0]] and c not in chosen]
        if same and random.random() < EXTRA_CLIENT_SAME_CATEGORY_PROB:
            candidates = same
        else:
            candidates = [c for c in ids if c not in chosen]
        chosen.append(random.choices(candidates, weights=[CLIENTS[c][2] for c in candidates])[0])
    return chosen


def generate_agents(num_legit, num_fraud):
    """Agents with random ids; county, clients and registration date drawn independently of the label."""
    n = num_legit + num_fraud
    numbers = random.sample(range(AGENT_ID_RANGE[0], AGENT_ID_RANGE[1] + 1), n)
    is_fraud = [False] * num_legit + [True] * num_fraud
    random.shuffle(is_fraud)
    counties = draw_counties(n)
    agents = [{
        "agent_id": f"A{number}",
        "registration_timestamp": fake.date_time_between(
            start_date=ANALYSIS_START - timedelta(days=REGISTRATION_DAYS_BEFORE[1]),
            end_date=ANALYSIS_START - timedelta(days=REGISTRATION_DAYS_BEFORE[0]),
        ),
        "region": county,
        "is_fraud": fraud,
    } for number, fraud, county in zip(numbers, is_fraud, counties)]
    agents_df = pd.DataFrame(agents).sort_values("agent_id").reset_index(drop=True)
    agents_df["clients"] = [draw_agent_clients() for _ in range(n)]
    return agents_df


def make_rings(num_ring_agents, strength="strong"):
    weak = strength == "weak"
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
        median = random.uniform(*(WEAK_RING_DAILY_MEDIAN_RANGE if weak else RING_DAILY_MEDIAN_RANGE))
        per_member = random.randint(*(WEAK_RING_POOL_PER_MEMBER_RANGE if weak else RING_POOL_PER_MEMBER_RANGE))
        rings.append({
            "strength": strength,
            "size": size,
            "pool_size": size * per_member,
            "hours": (random.randint(0, 23), random.randint(*RING_HOUR_WIDTH_RANGE)),
            "daily_median": median,
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
    rings = make_rings(fraud_counts["ring"], "strong") + make_rings(fraud_counts["weak_ring"], "weak")
    fraud_counts["sequential"] += fraud_counts["ring"] + fraud_counts["weak_ring"] - sum(r["size"] for r in rings)
    position = 0
    for ring_index, ring in enumerate(rings):
        for agent_id in fraud_ids[position:position + ring["size"]]:
            profiles[agent_id] = ("ring" if ring["strength"] == "strong" else "weak_ring", ring_index)
        position += ring["size"]
    for profile in SOLO_FRAUD_CONFIGS:
        for agent_id in fraud_ids[position:position + fraud_counts[profile]]:
            profiles[agent_id] = (profile, None)
        position += fraud_counts[profile]

    return profiles, rings


def pending_window_start():
    return ANALYSIS_END + pd.Timedelta(days=1) - pd.Timedelta(hours=PENDING_WINDOW_HOURS)


def draw_status(timestamp):
    if timestamp >= pending_window_start() and random.random() < PENDING_PROB_IN_WINDOW:
        return "pending"
    return random.choices(list(RESOLVED_STATUS_WEIGHTS), weights=list(RESOLVED_STATUS_WEIGHTS.values()))[0]


def cross_sell_client(clients):
    """One extra client for a single-client legit_repeat agent, from the same category if possible."""
    others = [c for c in CLIENTS if c not in clients]
    same = [c for c in others if CLIENT_CATEGORY[c] == CLIENT_CATEGORY[clients[0]]]
    candidates = same or others
    return random.choices(candidates, weights=[CLIENTS[c][2] for c in candidates])[0]


def generate_activation_records(agents_df, profiles=None, rings=None):
    if "clients" not in agents_df:
        agents_df = agents_df.assign(clients=[draw_agent_clients() for _ in range(len(agents_df))])
    if profiles is None:
        profiles, rings = assign_profiles(agents_df)

    taken_pairs = set()
    used_customers = set()

    def fresh_customer():
        while True:
            customer_id = random_customer_id()
            if customer_id not in used_customers:
                used_customers.add(customer_id)
                return customer_id

    days = pd.date_range(ANALYSIS_START, ANALYSIS_END, freq="D")
    ring_pools = [non_consecutive_customer_ids(ring["pool_size"]) for ring in rings]
    for pool in ring_pools:
        used_customers.update(pool)
    county_counts = agents_df["region"].value_counts()
    popular_pools = {county: [fresh_customer() for _ in range(max(POPULAR_POOL_MIN, POPULAR_POOL_PER_AGENT * n))]
                     for county, n in sorted(county_counts.items())}

    records = []
    for agent in agents_df.itertuples():
        profile, ring_index = profiles[agent.agent_id]
        clients = agent.clients
        client_mix = np.random.dirichlet([CLIENT_MIX_DIRICHLET_ALPHA] * len(clients))

        def pick_client():
            return random.choices(clients, weights=client_mix)[0]

        popular_share = random.uniform(*POPULAR_POOL_SHARE_RANGE) if random.random() < POPULAR_POOL_USER_PROB else 0.0
        active_prob = random.uniform(*ACTIVE_DAY_PROB_RANGE)
        off_hours_share = random.uniform(*OFF_HOURS_SHARE_RANGE)
        repeat_share = 0.0
        sell_clients = list(clients)
        if agent.is_fraud:
            config = rings[ring_index] if ring_index is not None else SOLO_FRAUD_CONFIGS[profile]
            if profile == "weak":
                rate = LEGIT_DAILY_MEDIAN * random.uniform(*WEAK_FRAUD_RATE_MULTIPLIER_RANGE)
            else:
                rate = agent_rate(config["daily_median"])
            if profile == "weak":
                fraud_share = random.uniform(*WEAK_FRAUD_SHARE_RANGE)
            elif profile == "weak_ring":
                fraud_share = random.uniform(*WEAK_RING_SHARE_RANGE)
            else:
                fraud_share = random.uniform(*FRAUD_PATTERN_SHARE_RANGE)
            pool_size = random.randint(*config["pool_size_range"]) if ring_index is None else 0
            own_pool = [(fresh_customer(), pick_client()) for _ in range(pool_size)]
            taken_pairs.update(own_pool)
            seq_next = random.randint(CUSTOMER_ID_MIN, CUSTOMER_ID_MAX - 2000)
        else:
            rate = agent_rate(LEGIT_BUSY_DAILY_MEDIAN if profile == "legit_busy" else LEGIT_DAILY_MEDIAN)
            fraud_share = 0.0
            night_share = random.uniform(*LEGIT_NIGHT_SHARE_RANGE)
            if profile == "legit_repeat":
                repeat_share = random.uniform(*LEGIT_REPEAT_SHARE_RANGE)
                if len(clients) == 1:
                    sell_clients.append(cross_sell_client(clients))

        my_customers, my_customer_set, retry_queue = [], set(), []

        def cross_sell(candidate_clients):
            for _ in range(CROSS_SELL_TRIES if my_customers else 0):
                customer_id = random.choice(my_customers)
                free = [c for c in candidate_clients if (customer_id, c) not in taken_pairs]
                if free:
                    return customer_id, random.choice(free)
            return None

        def normal_pair(day, client_id):
            if retry_queue and retry_queue[0][0] < day:
                return retry_queue.pop(0)[1:]
            if repeat_share and random.random() < repeat_share:
                pair = cross_sell(sell_clients)
                if pair:
                    return pair
            if len(clients) > 1 and random.random() < CROSS_CLIENT_REPEAT_PROB:
                pair = cross_sell(clients)
                if pair:
                    return pair
            if random.random() < popular_share:
                pool = popular_pools[agent.region]
                for _ in range(POPULAR_PICK_TRIES):
                    customer_id = random.choice(pool)
                    if (customer_id, client_id) not in taken_pairs:
                        return customer_id, client_id
            return fresh_customer(), client_id

        for day in days:
            if random.random() > active_prob:
                continue
            for _ in range(daily_count(rate)):
                client_id = pick_client()
                pattern = agent.is_fraud and random.random() < fraud_share
                if pattern:
                    hour = sample_hour(config["hours"])
                    if ring_index is not None:
                        customer_id = random.choice(ring_pools[ring_index])
                    elif profile == "sequential":
                        while f"CUST{seq_next}" in used_customers:
                            seq_next += 1
                        customer_id = f"CUST{seq_next}"
                        seq_next += 1
                    else:
                        customer_id, client_id = random.choice(own_pool)
                else:
                    hour = sample_hour("normal", off_hours_share)
                    if profile == "legit_night" and random.random() < night_share:
                        hour = sample_hour("late_night")
                    customer_id, client_id = normal_pair(day, client_id)
                timestamp = make_timestamp(day, hour)
                status = draw_status(timestamp)
                used_customers.add(customer_id)
                taken_pairs.add((customer_id, client_id))
                if customer_id not in my_customer_set:
                    my_customer_set.add(customer_id)
                    my_customers.append(customer_id)
                if not pattern and status != "completed" and random.random() < RETRY_PROB:
                    retry_queue.append((day, customer_id, client_id))
                records.append({
                    "agent_id": agent.agent_id,
                    "timestamp": timestamp,
                    "customer_id": customer_id,
                    "activation_status": status,
                    "client_id": client_id,
                    "category": CLIENT_CATEGORY[client_id],
                })

    activations = pd.DataFrame(records).sort_values(["timestamp", "agent_id", "customer_id"], kind="mergesort")
    activations.insert(0, "record_id", [f"R{RECORD_ID_START + i}" for i in range(len(activations))])
    return activations.reset_index(drop=True)


def context_rngs(seed):
    """Independent generators for the context fields, spawned from the seed."""
    children = np.random.SeedSequence(seed).spawn(len(CONTEXT_STREAMS))
    return {name: np.random.default_rng(child) for name, child in zip(CONTEXT_STREAMS, children)}


def generate_identity(agent_ids, rng):
    n, n_last = len(agent_ids), len(LAST_NAMES)
    if n > len(FIRST_NAMES) * n_last:
        raise ValueError("not enough name combinations for unique full names")
    names = rng.choice(len(FIRST_NAMES) * n_last, n, replace=False)
    phones = rng.choice(10 ** PHONE_DIGITS, n, replace=False)
    low = 10 ** (NATIONAL_ID_DIGITS - 1)
    national_ids = rng.choice(10 ** NATIONAL_ID_DIGITS - low, n, replace=False) + low
    return pd.DataFrame({
        "agent_id": list(agent_ids),
        "full_name": [f"{FIRST_NAMES[i // n_last]} {LAST_NAMES[i % n_last]}" for i in names],
        "phone_number": [f"{PHONE_PREFIX}{p:0{PHONE_DIGITS}d}" for p in phones],
        "national_id_number": [f"{x:0{NATIONAL_ID_DIGITS}d}" for x in national_ids],
    })


def draw_account_status(n, rng):
    """Snapshot after the window, for administrative reasons; exact shares, random agents."""
    statuses = [status for status, k in allocate(n, ACCOUNT_STATUS_WEIGHTS).items() for _ in range(k)]
    return rng.permutation(statuses)


def generate_agent_categories(agents, activations, rng):
    """A certified row per category worked in, certified between registration and the first
    activity there; EXPIRED_CATEGORY_PROB of agents (random) also hold one expired category."""
    registration = pd.to_datetime(agents.set_index("agent_id")["registration_timestamp"])
    first = activations.assign(timestamp=pd.to_datetime(activations["timestamp"])).groupby(
        ["agent_id", "category"])["timestamp"].min()
    worked_by_agent = {a: s.droplevel(0) for a, s in first.groupby(level=0)}
    n_expired = int(round(len(agents) * EXPIRED_CATEGORY_PROB))
    with_expired = set(rng.choice(agents["agent_id"].to_numpy(), n_expired, replace=False))
    rows = []
    for agent_id in agents["agent_id"]:
        registered = registration[agent_id]
        worked = worked_by_agent.get(agent_id, pd.Series(dtype="datetime64[ns]"))
        for category, first_activity in worked.items():
            certified_at = registered + (first_activity - registered) * float(rng.random())
            rows.append((agent_id, category, "certified", certified_at.floor("s")))
        if agent_id in with_expired:
            others = [c for c in CATEGORIES if c not in worked.index]
            category = others[int(rng.integers(len(others)))]
            certified_at = registered + (ANALYSIS_START - registered) * float(rng.random())
            rows.append((agent_id, category, "expired", certified_at.floor("s")))
    return pd.DataFrame(rows, columns=["agent_id", "category", "certification_status", "certified_at"])


def add_activation_context(activations, agent_ids, rng):
    """quality_score (0-100) and commission_kes (the client rate if completed, else 0)."""
    agent_mean = dict(zip(agent_ids, rng.normal(QUALITY_AGENT_MEAN, QUALITY_AGENT_SD, len(agent_ids))))
    noise = rng.normal(0.0, QUALITY_RECORD_SD, len(activations))
    failed = activations["activation_status"].eq("failed")
    quality = activations["agent_id"].map(agent_mean) + noise - QUALITY_FAILED_PENALTY * failed
    rate = activations["category"].map(COMMISSION_PER_ACTIVATION_KES)
    return activations.assign(
        quality_score=np.clip(np.round(quality), 0, 100).astype(int),
        commission_kes=np.where(activations["activation_status"].eq("completed"), rate, 0).astype(int),
    )


def ring_label(ring_index):
    return f"ring_{ring_index + 1:02d}"


def clients_frame():
    return pd.DataFrame([{"client_id": cid, "name": name, "category": category,
                          "commission_per_activation_kes": COMMISSION_PER_ACTIVATION_KES[category]}
                         for cid, (name, category, _) in CLIENTS.items()])


def generate_dataset(seed=DEFAULT_SEED, n_agents=DEFAULT_N_AGENTS, fraud_rate=DEFAULT_FRAUD_RATE):
    if n_agents < 1 or not 0 < fraud_rate < 1:
        raise ValueError("n_agents must be positive and fraud_rate strictly between 0 and 1")
    seed_everything(seed)
    num_fraud = int(round(n_agents * fraud_rate))
    agents_df = generate_agents(n_agents - num_fraud, num_fraud)
    profiles, rings = assign_profiles(agents_df)
    activations_df = generate_activation_records(agents_df, profiles, rings)
    rngs = context_rngs(seed)
    agent_ids = agents_df["agent_id"].tolist()
    identity_df = generate_identity(agent_ids, rngs["identity"])
    agents_df["account_status"] = draw_account_status(len(agents_df), rngs["account_status"])
    activations_df = add_activation_context(activations_df, agent_ids, rngs["quality"])

    labels_df = pd.DataFrame({
        "agent_id": agents_df["agent_id"],
        "is_fraud": agents_df["is_fraud"],
        "profile": agents_df["agent_id"].map(lambda a: profiles[a][0]),
        "ring_id": agents_df["agent_id"].map(lambda a: "" if profiles[a][1] is None else ring_label(profiles[a][1])),
    })
    rings_df = pd.DataFrame([{
        "ring_id": ring_label(i), "strength": r["strength"], "size": r["size"], "pool_size": r["pool_size"],
        "hour_start": r["hours"][0], "hour_width": r["hours"][1],
        "daily_median": round(r["daily_median"], 2),
    } for i, r in enumerate(rings)], columns=["ring_id", "strength", "size", "pool_size", "hour_start", "hour_width", "daily_median"])
    public_agents = agents_df[["agent_id", "registration_timestamp", "region", "account_status"]]
    categories_df = generate_agent_categories(public_agents, activations_df, rngs["certifications"])
    return SyntheticDataset(public_agents, activations_df, labels_df, rings_df, clients_frame(),
                            identity_df, categories_df)


def generator_parameters(n_agents, fraud_rate):
    return {
        "n_agents": n_agents, "fraud_rate": fraud_rate, "timezone": TIMEZONE,
        "analysis_window": [str(ANALYSIS_START.date()), str(ANALYSIS_END.date())],
        "customer_id_digits": CUSTOMER_ID_DIGITS,
        "county_population_thousands": COUNTY_POPULATION_THOUSANDS, "county_min_agents": COUNTY_MIN_AGENTS,
        "categories": CATEGORIES, "clients": CLIENTS,
        "agent_client_count_weights": AGENT_CLIENT_COUNT_WEIGHTS,
        "extra_client_same_category_prob": EXTRA_CLIENT_SAME_CATEGORY_PROB,
        "client_mix_dirichlet_alpha": CLIENT_MIX_DIRICHLET_ALPHA, "cross_client_repeat_prob": CROSS_CLIENT_REPEAT_PROB,
        "resolved_status_weights": RESOLVED_STATUS_WEIGHTS, "pending_window_hours": PENDING_WINDOW_HOURS,
        "pending_prob_in_window": PENDING_PROB_IN_WINDOW, "retry_prob": RETRY_PROB,
        "popular_pick_tries": POPULAR_PICK_TRIES, "cross_sell_tries": CROSS_SELL_TRIES,
        "popular_pool_per_agent": POPULAR_POOL_PER_AGENT, "popular_pool_min": POPULAR_POOL_MIN,
        "popular_pool_user_prob": POPULAR_POOL_USER_PROB, "popular_pool_share_range": POPULAR_POOL_SHARE_RANGE,
        "fraud_pattern_shares": FRAUD_PATTERN_SHARES, "legit_pattern_shares": LEGIT_PATTERN_SHARES,
        "active_day_prob_range": ACTIVE_DAY_PROB_RANGE, "daily_count_dispersion": DAILY_COUNT_DISPERSION,
        "agent_rate_sigma": AGENT_RATE_SIGMA, "normal_hour_mean": NORMAL_HOUR_MEAN, "normal_hour_sd": NORMAL_HOUR_SD,
        "off_hours_share_range": OFF_HOURS_SHARE_RANGE,
        "legit_daily_median": LEGIT_DAILY_MEDIAN, "legit_busy_daily_median": LEGIT_BUSY_DAILY_MEDIAN,
        "legit_night_share_range": LEGIT_NIGHT_SHARE_RANGE, "legit_repeat_share_range": LEGIT_REPEAT_SHARE_RANGE,
        "fraud_pattern_share_range": FRAUD_PATTERN_SHARE_RANGE,
        "ring_size_range": RING_SIZE_RANGE, "ring_pool_per_member_range": RING_POOL_PER_MEMBER_RANGE,
        "ring_hour_width_range": RING_HOUR_WIDTH_RANGE, "ring_daily_median_range": RING_DAILY_MEDIAN_RANGE,
        "weak_ring_pool_per_member_range": WEAK_RING_POOL_PER_MEMBER_RANGE,
        "weak_ring_share_range": WEAK_RING_SHARE_RANGE,
        "weak_ring_daily_median_range": WEAK_RING_DAILY_MEDIAN_RANGE,
        "solo_fraud_configs": SOLO_FRAUD_CONFIGS, "weak_fraud_share_range": WEAK_FRAUD_SHARE_RANGE,
        "weak_fraud_rate_multiplier_range": WEAK_FRAUD_RATE_MULTIPLIER_RANGE,
        "context_streams": CONTEXT_STREAMS, "commission_per_activation_kes": COMMISSION_PER_ACTIVATION_KES,
        "account_status_weights": ACCOUNT_STATUS_WEIGHTS, "expired_category_prob": EXPIRED_CATEGORY_PROB,
        "quality_agent_mean": QUALITY_AGENT_MEAN, "quality_agent_sd": QUALITY_AGENT_SD,
        "quality_record_sd": QUALITY_RECORD_SD, "quality_failed_penalty": QUALITY_FAILED_PENALTY,
        "phone_prefix": PHONE_PREFIX, "phone_digits": PHONE_DIGITS, "national_id_digits": NATIONAL_ID_DIGITS,
        "first_names": len(FIRST_NAMES), "last_names": len(LAST_NAMES),
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
    frames = {"agents": dataset.agents, "agent_identity": dataset.identity,
              "agent_categories": dataset.agent_categories, "activation_records": dataset.activations,
              "clients": dataset.clients, "labels": dataset.labels, "rings": dataset.rings}
    paths = {name: out_dir / f"{name}.csv" for name in frames}
    for name, frame in frames.items():
        frame.to_csv(paths[name], index=False)
    return paths


def main(argv=None):
    import json

    from data_checks import overlap_audit, run_checks
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
    checks = run_checks(dataset)
    (run_dir / "data_checks.json").write_text(json.dumps(checks, indent=2))
    audit, descriptors = overlap_audit(dataset)
    audit.to_csv(run_dir / "overlap_audit.csv", index=False)
    descriptors.reset_index().to_csv(run_dir / "raw_descriptors_by_agent.csv", index=False)

    n_fraud = int(dataset.labels["is_fraud"].sum())
    print(f"Seed {args.seed}: {len(dataset.agents)} agents ({n_fraud} fraud, {n_fraud / len(dataset.agents):.3f}), "
          f"{len(dataset.activations)} activation records, {len(dataset.rings)} rings, {len(dataset.clients)} clients.")
    print(summary.round(1).to_string(index=False))
    print(dataset.rings.to_string(index=False))
    print(json.dumps(checks, indent=1))
    print("Overlap audit, zero-overlap rows:")
    print(audit[audit["zero_overlap"]].to_string(index=False))
    print(f"Data saved to {args.out_dir}; run folder {run_dir}")


if __name__ == "__main__":
    main()
