import pytest
import psycopg
from testcontainers.postgres import PostgresContainer
from os import getenv
from init_db import create_customers_table, create_products_table, create_baskets_table, create_products_baskets_table

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def connection():
    conn = psycopg.connect(postgres_container.get_connection_url())

    with conn.cursor() as cur:
        create_customers_table(conn)
        create_products_table(conn)
        create_baskets_table(conn)
        create_products_baskets_table(conn)
    conn.commit()
  
    yield conn
    conn.close()

@pytest.fixture
def db(connection):

    connection.autocommit = False

    with connection.cursor() as cursor:
        yield cursor

    connection.rollback()

@pytest.fixture
def sample_customer(db):

    db.execute("""
        INSERT INTO customers
        (customer_id, forename, surname, billing_address)
        VALUES
        (1, 'John', 'Smith', '123 Main Street')
    """)

    return 1


@pytest.fixture
def sample_product(db):

    db.execute("""
        INSERT INTO products
        (sku, name, unit_price, in_stock)
        VALUES
        ('SKU001', 'Laptop', 999.99, 10)
    """)

    return "SKU001"


@pytest.fixture
def sample_basket(db, sample_customer):

    db.execute("""
        INSERT INTO baskets
        (basket_id, customer_no)
        VALUES
        (100, 1)
    """)

    return 100

def test_create_product(db):

    db.execute("""
        INSERT INTO products
        (sku, name, unit_price, in_stock)
        VALUES
        ('SKU100', 'Monitor', 249.99, 5)
    """)

    db.execute("""
        SELECT sku, name
        FROM products
        WHERE sku = 'SKU100'
    """)

    result = db.fetchone()

    assert result == ("SKU100", "Monitor")

def test_read_product(db, sample_product):

    db.execute("""
        SELECT name, unit_price
        FROM products
        WHERE sku = %s
    """, (sample_product,))

    product = db.fetchone()

    assert product[0] == "Laptop"
    assert float(product[1]) == 999.99

def test_update_product_stock(db, sample_product):

    db.execute("""
        UPDATE products
        SET in_stock = 25
        WHERE sku = %s
    """, (sample_product,))

    db.execute("""
        SELECT in_stock
        FROM products
        WHERE sku = %s
    """, (sample_product,))

    assert db.fetchone()[0] == 25

def test_delete_product(db, sample_product):

    db.execute("""
        DELETE FROM products
        WHERE sku = %s
    """, (sample_product,))

    db.execute("""
        SELECT *
        FROM products
        WHERE sku = %s
    """, (sample_product,))

    assert db.fetchone() is None

def test_cannot_create_basket_for_missing_customer(db):

    with pytest.raises(psycopg.errors.ForeignKeyViolation):

        db.execute("""
            INSERT INTO baskets
            (customer_no)
            VALUES (999)
        """)

def test_add_product_to_basket(
    db,
    sample_product,
    sample_basket
):

    db.execute("""
        INSERT INTO products_baskets
        (product_id, basket_id)
        VALUES
        (%s, %s)
    """, (sample_product, sample_basket))

    db.execute("""
        SELECT product_id, basket_id
        FROM products_baskets
    """)

    relation = db.fetchone()

    assert relation == ("SKU001", 100)
