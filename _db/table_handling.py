def db_table_exists(con, table_name: str) -> bool:
    result = con.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?
    """, [table_name]).fetchone()
    from qbrain._db.log_facade import duck_print_result
    duck_print_result("table_exists", table=table_name, count=result[0] if result else 0)
    return result[0] > 0