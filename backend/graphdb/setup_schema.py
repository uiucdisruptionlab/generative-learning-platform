"""
One-time script to create uniqueness constraints on Neo4j AuraDB.
Run from backend/:
    python -m graphdb.setup_schema
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

URI      = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chunk)   REQUIRE c.id   IS UNIQUE",
]


def main():
    print(f"Connecting to {URI} ...")
    with GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD)) as driver:
        driver.verify_connectivity()
        print("Connected.\n")

        for cypher in CONSTRAINTS:
            driver.execute_query(cypher, database_=DATABASE)
            print(f"Applied: {cypher}")

    print("\nSchema setup complete.")


if __name__ == "__main__":
    main()
