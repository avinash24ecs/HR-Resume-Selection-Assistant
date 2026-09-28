"""Central configuration. Reads environment variables (used when hosted); defaults are for local use."""
import os
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "hr_resume_db")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")   # Aura uses neo4j+s://xxxx.databases.neo4j.io
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

WAREHOUSE_DB = "data/hr_warehouse.db"   # SQLite file (star schema)
