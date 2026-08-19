# Legacy dashboards

Kept verbatim, still runnable, still reading the **same** database at
`~/Documents/LatencyTester/latency_tester.db`.

| File | Notes |
|---|---|
| `LatencyTester_Dashboard_v2.py` | The known-good single-file dashboard this project was refactored from. Reference implementation of the measurement pipeline |
| `LatencyTester_Dashboard_v2_GUIDA.md` | Its Italian user guide |
| `latency_dashboard_v1_1.py` | Earlier single-file dashboard |

The schema v1 migration only *adds* columns, so v2 keeps working after the new
dashboard has upgraded the archive — it simply ignores the new fields.

The command-line companion is still at `../companion/latency_companion.py`.

Run one with:

```powershell
python legacy/LatencyTester_Dashboard_v2.py
```
