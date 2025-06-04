# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
import os
import re
import sqlite3

from lgapi import logger


def insert_communities_from_dir(db_cursor, directory):
    for filename in os.listdir(directory):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(directory, filename)

        logger.debug("Building BGP community data from %s", filepath)

        with open(filepath, "r") as communities_file:
            records = []
            for line in communities_file:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue

                data = re.split(r"\s+", line, maxsplit=1)
                if len(data) == 2:
                    records.append(data)

            if records:
                db_cursor.executemany(
                    "INSERT INTO communities(community, name) VALUES (?, ?) "
                    "ON CONFLICT(community) DO UPDATE SET name=excluded.name;",
                    records,
                )


def init_community_map_db():
    """Initialise the community mappings database."""

    with sqlite3.connect("mapsdb/maps.db") as db_con:
        db_cursor = db_con.cursor()
        db_cursor.execute("DROP TABLE IF EXISTS communities")
        db_cursor.execute("CREATE TABLE communities(community TEXT PRIMARY KEY, name TEXT)")

        insert_communities_from_dir(db_cursor, "mapsdb/asns")
        insert_communities_from_dir(db_cursor, "mapsdb/override")

        db_con.commit()
