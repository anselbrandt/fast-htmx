async def createTable(pool):
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks
                (
                    ID TEXT PRIMARY KEY NOT NULL,
                    FILENAME TEXT NOT NULL,
                    STATUS TEXT NOT NULL
                )
                """
            )
            await conn.commit()


async def insert(pool, id, filename, status):
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO tasks(id, filename, status) VALUES(%s, %s, %s);",
                (id, filename, status),
            )
            await conn.commit()


async def getTasks(pool):
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM tasks WHERE status LIKE 'in-progress';")
            results = await cursor.fetchall()
            return results


async def update(pool, id, status):
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE tasks SET status=%s WHERE id=%s;",
                (status, id),
            )
            await conn.commit()
