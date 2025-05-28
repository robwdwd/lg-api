# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass Tool and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
#
import re
import sqlite3


def init_community_map_db():
    """Initialise the community mappings database."""

    db_con = sqlite3.connect("mapsdb/maps.db")

    db_cursor = db_con.cursor()
    db_cursor.execute("DROP TABLE IF EXISTS communities")
    db_cursor.execute("CREATE TABLE communities(community, name)")

    records = []

    with open("mapsdb/communities.txt", "r") as communities_file:
        for line in communities_file:
            line = line.strip()
            if line.startswith("#") or not line:
                continue

            data = re.split(r"\s+", line, maxsplit=1)
            if len(data) == 2:
                records.append(data)

    db_cursor.executemany("INSERT INTO communities VALUES(?,?);", records)
    db_con.commit()
    db_con.close()