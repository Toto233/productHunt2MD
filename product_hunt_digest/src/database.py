import sqlite3
import os
from .utils import log_error
import datetime

# Define the directory and database file path
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
DATABASE_FILE = os.path.join(DATA_DIR, 'products.db')

def _get_db_connection():
    """Establishes and returns a database connection."""
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        log_error(f"Database connection error: {e}")
        return None
    except OSError as e:
        log_error(f"OS error while ensuring data directory {DATA_DIR}: {e}")
        return None

def init_db_corrected():
    """
    Initializes the database and creates the 'products' table if it doesn't exist.
    weekly_leaderboard_source is NOT UNIQUE.
    Ensures scraped_date and weekly_leaderboard_source are NOT NULL.
    """
    conn = _get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_en TEXT,
                description_en TEXT,
                website_url TEXT,
                all_comment_texts_en TEXT,
                name_cn TEXT,
                description_cn TEXT,
                comment_summary_cn TEXT,
                scraped_date DATE NOT NULL,
                weekly_leaderboard_source TEXT NOT NULL
            )
        """)
        # Index on weekly_leaderboard_source is still useful for queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_weekly_leaderboard_source ON products (weekly_leaderboard_source)")
        conn.commit()
    except sqlite3.Error as e:
        log_error(f"Error initializing database table 'products' (corrected): {e}")
    finally:
        if conn:
            conn.close()

init_db = init_db_corrected

def add_product_refined(product_data: dict) -> int | None:
    """
    Adds a new product to the database.
    product_data MUST contain: scraped_date, weekly_leaderboard_source (e.g., "YYYY/WW").
    Optional: name_en, description_en, website_url, all_comment_texts_en.
    Returns the ID of the newly inserted row, or None if insertion fails.
    """
    required_fields = ['scraped_date', 'weekly_leaderboard_source']
    for field in required_fields:
        if field not in product_data or product_data[field] is None:
            log_error(f"Error adding product: Missing required field '{field}'.")
            return None

    conn = _get_db_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        scraped_date_val = product_data['scraped_date']
        if isinstance(scraped_date_val, (datetime.date, datetime.datetime)):
            scraped_date_str = scraped_date_val.strftime('%Y-%m-%d')
        else:
            scraped_date_str = str(scraped_date_val)

        cursor.execute("""
            INSERT INTO products (
                name_en, description_en, website_url, all_comment_texts_en,
                name_cn, description_cn, comment_summary_cn,
                scraped_date, weekly_leaderboard_source
            ) VALUES (?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
        """, (
            product_data.get('name_en', ''),
            product_data.get('description_en', ''),
            product_data.get('website_url', ''),
            product_data.get('all_comment_texts_en', ''),
            scraped_date_str,
            str(product_data['weekly_leaderboard_source']) # Should be "YYYY/WW"
        ))
        conn.commit()
        return cursor.lastrowid
    # No longer expect sqlite3.IntegrityError for weekly_leaderboard_source uniqueness
    except sqlite3.Error as e:
        log_error(f"Error adding product: {e}")
        return None
    finally:
        if conn:
            conn.close()

add_product = add_product_refined

def update_product_translation(product_id: int, field_name: str, translated_text: str) -> bool:
    if field_name not in ['name_cn', 'description_cn', 'comment_summary_cn']:
        log_error(f"Invalid field name for translation update: {field_name}")
        return False
    conn = _get_db_connection()
    if conn is None: return False
    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE products SET {field_name} = ? WHERE id = ?", (translated_text, product_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        log_error(f"Error updating product {product_id} with {field_name}: {e}")
        return False
    finally:
        if conn: conn.close()

def get_product_by_id(product_id: int) -> dict | None:
    conn = _get_db_connection()
    if conn is None: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        log_error(f"Error getting product by ID {product_id}: {e}")
        return None
    finally:
        if conn: conn.close()

def get_products_for_ranking(weekly_leaderboard_source: str) -> list[dict]:
    """
    Retrieves products matching an exact weekly_leaderboard_source (e.g., "YYYY/WW").
    Returns a list of dicts with id, name_cn, description_cn, comment_summary_cn.
    """
    conn = _get_db_connection()
    if conn is None: return []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name_cn, description_cn, comment_summary_cn
            FROM products
            WHERE weekly_leaderboard_source = ?
            ORDER BY id
        """, (weekly_leaderboard_source,)) # Exact match
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        log_error(f"Error getting products for ranking by source '{weekly_leaderboard_source}': {e}")
        return []
    finally:
        if conn: conn.close()

def get_all_products_for_markdown(weekly_leaderboard_source: str, ordered_ids: list[int]) -> list[dict]:
    """
    Retrieves product details for a given exact weekly_leaderboard_source, ordered by ordered_ids.
    Returns list of dicts with name_en, name_cn, description_cn, website_url, comment_summary_cn.
    """
    if not ordered_ids: return []
    conn = _get_db_connection()
    if conn is None: return []
    try:
        cursor = conn.cursor()
        placeholders = ','.join('?' for _ in ordered_ids)
        query = f"""
            SELECT id, name_en, name_cn, description_cn, website_url, comment_summary_cn
            FROM products
            WHERE weekly_leaderboard_source = ? AND id IN ({placeholders})
        """
        params = [weekly_leaderboard_source] + ordered_ids # Exact match
        cursor.execute(query, params)
        rows = cursor.fetchall()

        ordered_rows_map = {dict(row)['id']: dict(row) for row in rows}
        result_list = [ordered_rows_map[id_] for id_ in ordered_ids if id_ in ordered_rows_map]

        return result_list
    except sqlite3.Error as e:
        log_error(f"Error getting all products for markdown by source '{weekly_leaderboard_source}': {e}")
        return []
    finally:
        if conn: conn.close()
