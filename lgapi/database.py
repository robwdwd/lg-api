# Copyright (c) 2025, Rob Woodward. All rights reserved.
#
# This file is part of Looking Glass API and is released under the
# "BSD 2-Clause License". Please see the LICENSE file that should
# have been included as part of this distribution.
"""Database functions, mainly for Community mapping"""
import os
import re

import aiosqlite
import aiosqlite.cursor

from lgapi import logger


async def get_community_map(communities: set) -> dict:
    """Get community descriptions from the database."""
    if not communities:
        return {}

    async with aiosqlite.connect("mapsdb/maps.db") as db_con:
        async with db_con.cursor() as db_cursor:
            placeholders = ",".join("?" for _ in communities)
            sql = f"SELECT community, name FROM communities WHERE community IN ({placeholders})"
            res = await db_cursor.execute(sql, tuple(communities))
            return {row[0]: row[1] for row in await res.fetchall()}


async def insert_communities_from_dir(db_cursor: aiosqlite.cursor.Cursor, directory: str):
    """Inserts the community mapping into the database from each ASN file"""
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
                await db_cursor.executemany(
                    "INSERT INTO communities(community, name) VALUES (?, ?) "
                    "ON CONFLICT(community) DO UPDATE SET name=excluded.name;",
                    records,
                )


async def init_community_map_db():
    """Initialise the community mappings database."""

    async with aiosqlite.connect("mapsdb/maps.db") as db_con:
        async with db_con.cursor() as db_cursor:
            await db_cursor.execute("DROP TABLE IF EXISTS communities")
            await db_cursor.execute("CREATE TABLE communities(community TEXT PRIMARY KEY, name TEXT)")

            await insert_communities_from_dir(db_cursor, "mapsdb/asns")
            await insert_communities_from_dir(db_cursor, "mapsdb/override")

            await db_con.commit()
