# Freeze record: data (change #5)

Written 2026-10-13 09:11:38 by `ml/freeze.py --data`. The sha256 hashes were computed in Python; no git command was used. `ml/tests/test_freeze.py` fails if any file below changes.

The data is final after change #5 (integrity rules R1 to R6 and context fields; see `CHANGES.md`). Generation run: `runs/20261013-091128_datagen_s42` (seed 42). The model freeze written before Step 11 on the earlier data is archived as `results/archive_v3a/FREEZE_v3a.md`. The split, features, models and selection have not been re-run on this data; a new model freeze follows those re-runs.

**No test label has been loaded.** `labels.csv` and `rings.csv` were not re-read for this record. Their hashes, recorded when the data was generated, are `102db7224eaecf0cad54aaf721e7e94a18ba580ea383ec0db1b52e33b491b34c` and `6a9845a9be7b700e34ac42c4f0c7329eb0fae2c3712b809e745d9662a9906929` (`runs/20261013-091128_datagen_s42/run_info.json`). `labels.csv` is byte-identical to the archived v3a `labels.csv` (hashes compared, content not read).

## Hashes

| What | File (relative to `ml/`) | sha256 |
|---|---|---|
| Data | `data/synthetic/activation_records.csv` | `efcc0131a21c75718f79802a721aca845f95aba04b1790f38225bf00713bf0aa` |
| Data | `data/synthetic/agents.csv` | `f10364e58a046a9df0cb878aae0a37c1a43e0fbfde05ca176de90d1704a94b0e` |
| Data | `data/synthetic/agent_identity.csv` | `1783bb27b493e768aee5db98ec47fa4c00b3759b4753525c6d1eceeb68b4adaa` |
| Data | `data/synthetic/agent_categories.csv` | `59e6f99976b32350efbb1fa45d5d23ad3eeee2388fd191b14b3128b71e876d5c` |
| Data | `data/synthetic/clients.csv` | `2530e16542870a7c5652bd44c1ba23b2cc93a0997bc2217283e85512980a418a` |
| Generator | `data_generation.py` | `7ad03d6e694ae5f0b54f58cfd3bba5111d1024bb46c87b40a31b2c85908f4521` |
| Generator checks | `data_checks.py` | `58e9fb3def88ba64b9d66ec390f1cffee99b1205c08e5acc9f7f114eb9229104` |
| Generation run | `runs/20261013-091128_datagen_s42/run_info.json` | `1ae8d64c77e8f97134365ed1071edcd97cde6e8ffe06c6293ea0eaa1496d2848` |
| Generation run | `runs/20261013-091128_datagen_s42/data_checks.json` | `bb4f3fe3fee7bf75810a246914b89ce88aec34385a306d9f9b5d0ba7e1bdd2d1` |
| Rules (unchanged) | `results/acceptance_criteria.md` | `c6b9c035bfcbd1df19547fec1f2cccc4e2a65e71cf55487e0001a9df75d47158` |
| Rules (unchanged) | `results/selection_rule.md` | `e3aa8afd1324388dc5a9a51644b945ddc7aeb3f5fea061bc7a8ba3aff38fe8af` |
