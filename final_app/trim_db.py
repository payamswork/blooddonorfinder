"""
trim_db.py — run once to trim donors.db to ~350 records.
Keeps a realistic blood-group distribution, favours the earliest
inserted rows (most "original" data). Safe to delete afterward.

Usage:
    python trim_db.py
"""
import sqlite3, os, shutil

DB = "donors.db"
BACKUP = "donors_full_backup.db"
TARGET = 350

if not os.path.exists(DB):
    print("donors.db not found. Nothing to trim.")
    exit()

shutil.copy2(DB, BACKUP)
print(f"Backup saved → {BACKUP}")

conn = sqlite3.connect(DB)
total_before = conn.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
print(f"Before: {total_before} donors")

blood_groups = ["A+","A-","B+","B-","AB+","AB-","O+","O-"]
weights      = [28,   6,  30,   7,   5,   1,  20,   3]

keep_ids = set()
for bg, w in zip(blood_groups, weights):
    n = max(1, round(TARGET * w / sum(weights)))
    rows = conn.execute(
        "SELECT id FROM donors WHERE Blood_group=? ORDER BY id ASC LIMIT ?",
        (bg, n)
    ).fetchall()
    keep_ids.update(r[0] for r in rows)

# Keep last 5 manually-added rows regardless
last = conn.execute("SELECT id FROM donors ORDER BY id DESC LIMIT 10").fetchall()
keep_ids.update(r[0] for r in last[:5])

# Delete everything not in keep set
placeholders = ",".join("?" * len(keep_ids))
conn.execute(f"DELETE FROM donors WHERE id NOT IN ({placeholders})", list(keep_ids))
conn.execute("VACUUM")
conn.commit()

total_after = conn.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
print(f"After:  {total_after} donors")

dist = conn.execute(
    "SELECT Blood_group, COUNT(*) FROM donors GROUP BY Blood_group ORDER BY 2 DESC"
).fetchall()
for row in dist:
    print(f"  {row[0]}: {row[1]}")

conn.close()
print("Done. Full backup kept at donors_full_backup.db")
