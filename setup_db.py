import sqlite3

# 1. Create a new local database file (or connect to it if it exists)
conn = sqlite3.connect('hwsd_local.db')
cursor = conn.cursor()

# 2. Build the architecture (Table)
cursor.execute('''
CREATE TABLE IF NOT EXISTS regional_soil (
    region TEXT PRIMARY KEY,
    ph REAL,
    nitrogen REAL,
    phosphorus REAL,
    potassium REAL
)
''')

# 3. Inject the HWSD baseline data for Sfax
cursor.execute('''
INSERT OR REPLACE INTO regional_soil (region, ph, nitrogen, phosphorus, potassium)
VALUES ('Sfax,TN', 7.4, 38.0, 22.0, 32.0)
''')

# Save and close
conn.commit()
conn.close()

print("✅ Offline HWSD database built successfully! Look for 'hwsd_local.db' in your folder.")