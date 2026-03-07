import psycopg
try:
    conn = psycopg.connect('postgresql://admin:An0th3rStr4wngH3ld3nV4nH3Vt3@localhost:5432/shopify_platform')
    conn.autocommit = True
    cur = conn.cursor()
    
    # Drop table first
    cur.execute('DROP TABLE IF EXISTS pending_approvals CASCADE;')
    
    # Use helper for idempotent type creation
    def create_enum_type(name, values):
        cur.execute(f"SELECT 1 FROM pg_type WHERE typname = '{name}'")
        if not cur.fetchone():
            vals_str = ", ".join([f"'{v}'" for v in values])
            cur.execute(f"CREATE TYPE {name} AS ENUM ({vals_str})")
            print(f"Created type {name}")
        else:
            print(f"Type {name} already exists")

    create_enum_type('approvalstatus', ['PENDING', 'APPROVED', 'REJECTED', 'EXPIRED'])
    create_enum_type('approvalpriority', ['LOW', 'NORMAL', 'HIGH', 'CRITICAL'])
    create_enum_type('sandboxverdict', ['green', 'yellow', 'red'])

    conn.close()
    print('DB Setup complete')
except Exception as e:
    print(f"Error: {e}")
