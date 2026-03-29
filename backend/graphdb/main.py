from neo4j import GraphDatabase
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

NEO_URI = os.getenv("NEO4J_URI")
NEO_USER = os.getenv("NEO4J_USERNAME")
NEO_PASS = os.getenv("NEO4J_PASSWORD")

AUTH = (NEO_USER, NEO_PASS)

with GraphDatabase.driver(NEO_URI, auth=AUTH) as driver:
    driver.verify_connectivity()

    # Writing into the Database
    summary = driver.execute_query("""
        CREATE (a:Person {name: $name})
        CREATE (b:Person {name: $friendName})
        CREATE (a)-[:KNOWS]->(b)
        """,
        name="Alice", friendName="David",
        database_="cfbd0191",
    ).summary

    print("Created {nodes_created} nodes in {time} ms.".format(
        nodes_created=summary.counters.nodes_created,
        time=summary.result_available_after
    ))

    # Reading from the database
    records, summary, keys = driver.execute_query("""
        MATCH (p:Person)-[:KNOWS]->(:Person)
        RETURN p.name AS name
        """,
        database_="cfbd0191",
    )

    # Loop through results and do something with them
    for record in records:
        print(record.data())

    # Summary information
    print("The query `{query}` returned {records_count} records in {time} ms.".format(
        query=summary.query, records_count=len(records),
        time=summary.result_available_after
    ))

