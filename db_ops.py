def createTable(pool):
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks
                (
                    ID TEXT PRIMARY KEY NOT NULL,
                    FILENAME TEXT NOT NULL
                )
                """
            )
            conn.commit()


def insert(pool, id, filename):
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tasks(id, filename) VALUES(%s, %s);",
                (id, filename),
            )
            conn.commit()


def delete(pool, id):
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM tasks WHERE id=%s;",
                (id,),
            )
            conn.commit()


async def getTasks(pool):
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM tasks;")
            results = await cursor.fetchall()
            return results
