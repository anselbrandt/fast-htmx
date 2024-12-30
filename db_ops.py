def createTable(pool):
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks
                (
                    ID TEXT PRIMARY KEY NOT NULL,
                    FILENAME TEXT NOT NULL,
                    STATUS TEXT NOT NULL
                )
                """
            )
            conn.commit()


def insert(pool, id, filename, status):
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tasks(id, filename, status) VALUES(%s, %s, %s);",
                (id, filename, status),
            )
            conn.commit()


def getTasks(pool):
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE status LIKE 'in-progress';")
            results = cursor.fetchall()
            return results


def update(pool, id, status):
    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET status=%s WHERE id=%s;",
                (status, id),
            )
            conn.commit()
