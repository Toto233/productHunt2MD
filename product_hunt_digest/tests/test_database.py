import unittest
from unittest.mock import patch
import os
import sys
import sqlite3
import datetime
import tempfile
import shutil

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from product_hunt_digest.src import database
from product_hunt_digest.src import utils # For log_error, if we want to check logs

class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_db_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.temp_db_dir, "test_products.db")
        self.original_database_file = database.DATABASE_FILE
        self.original_data_dir = database.DATA_DIR
        database.DATABASE_FILE = self.test_db_file
        database.DATA_DIR = self.temp_db_dir
        database.init_db()
        self.added_product_ids = []

    def tearDown(self):
        shutil.rmtree(self.temp_db_dir)
        database.DATABASE_FILE = self.original_database_file
        database.DATA_DIR = self.original_data_dir

    def test_init_db_creates_table_and_indexes(self):
        self.assertTrue(os.path.exists(self.test_db_file))
        conn = sqlite3.connect(self.test_db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products';")
        self.assertIsNotNone(cursor.fetchone(), "Table 'products' was not created.")
        cursor.execute("PRAGMA table_info(products);")
        columns_info = {info[1]: (info[2], info[3]) for info in cursor.fetchall()}
        expected_schema = {
            'id': ('INTEGER', 0),
            'name_en': ('TEXT', 0), 'description_en': ('TEXT', 0), 'website_url': ('TEXT', 0),
            'all_comment_texts_en': ('TEXT', 0), 'name_cn': ('TEXT', 0),
            'description_cn': ('TEXT', 0), 'comment_summary_cn': ('TEXT', 0),
            'scraped_date': ('DATE', 1), 'weekly_leaderboard_source': ('TEXT', 1)
        }
        id_col_info = next(col for col in cursor.execute("PRAGMA table_info(products);").fetchall() if col[1] == 'id')
        self.assertEqual(id_col_info[5], 1, "id column should be primary key")
        for col_name, (col_type, col_notnull) in expected_schema.items():
            self.assertIn(col_name, columns_info)
            self.assertEqual(columns_info[col_name][0], col_type, f"Column {col_name} type mismatch")
            if col_name != 'id':
                 self.assertEqual(columns_info[col_name][1], col_notnull, f"Column {col_name} notnull mismatch")
        cursor.execute("PRAGMA index_list('products');")
        indexes = [idx[1] for idx in cursor.fetchall()]
        self.assertIn("idx_weekly_leaderboard_source", indexes)
        conn.close()

    def test_add_product_successfully(self):
        today = datetime.date.today()
        product_data = {
            "name_en": "Test Product", "description_en": "Test Desc",
            "website_url": "http://test.com", "all_comment_texts_en": "Comment1",
            "scraped_date": today, "weekly_leaderboard_source": "2023/01"
        }
        product_id = database.add_product(product_data)
        self.assertIsNotNone(product_id)
        self.added_product_ids.append(product_id)
        retrieved = database.get_product_by_id(product_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['name_en'], product_data['name_en'])
        self.assertEqual(retrieved['scraped_date'], today.strftime('%Y-%m-%d'))
        self.assertEqual(retrieved['weekly_leaderboard_source'], "2023/01")
        self.assertIsNone(retrieved['name_cn'])

    def test_add_product_missing_required_fields(self):
        product_data_missing_date = {"name_en": "Test Product Fail", "weekly_leaderboard_source": "2023/02"}
        self.assertIsNone(database.add_product(product_data_missing_date))
        product_data_missing_source = {"name_en": "Test Product Fail 2", "scraped_date": datetime.date.today()}
        self.assertIsNone(database.add_product(product_data_missing_source))

    def test_update_product_translation(self):
        product_id = database.add_product({
            "name_en": "Translate Me", "scraped_date": datetime.date.today(),
            "weekly_leaderboard_source": "2023/03_Translate"
        })
        self.assertIsNotNone(product_id); self.added_product_ids.append(product_id)
        self.assertTrue(database.update_product_translation(product_id, "name_cn", "已翻译名称"))
        self.assertTrue(database.update_product_translation(product_id, "description_cn", "已翻译描述"))
        self.assertTrue(database.update_product_translation(product_id, "comment_summary_cn", "已翻译评论"))
        retrieved = database.get_product_by_id(product_id)
        self.assertEqual(retrieved['name_cn'], "已翻译名称")
        self.assertEqual(retrieved['description_cn'], "已翻译描述")
        self.assertEqual(retrieved['comment_summary_cn'], "已翻译评论")
        self.assertFalse(database.update_product_translation(product_id, "invalid_field", "test"))
        self.assertFalse(database.update_product_translation(99999, "name_cn", "test"))

    def test_get_products_for_ranking(self):
        source_target = "2023/04"; source_other = "2023/05"; today = datetime.date.today()
        p1_id = database.add_product({"name_en": "P1", "scraped_date": today, "weekly_leaderboard_source": source_target})
        p2_id = database.add_product({"name_en": "P2", "scraped_date": today, "weekly_leaderboard_source": source_other})
        p3_id = database.add_product({"name_en": "P3", "scraped_date": today, "weekly_leaderboard_source": source_target})
        self.added_product_ids.extend([p for p in [p1_id, p2_id, p3_id] if p is not None])
        self.assertIsNotNone(p1_id); self.assertIsNotNone(p3_id)

        database.update_product_translation(p1_id, "name_cn", "P1_CN_Updated")
        database.update_product_translation(p3_id, "description_cn", "P3_DescCN_Updated")
        database.update_product_translation(p3_id, "comment_summary_cn", "P3_SummCN_Updated")

        ranked_products = database.get_products_for_ranking(source_target)
        self.assertEqual(len(ranked_products), 2)
        product_ids_retrieved = {p['id'] for p in ranked_products}
        self.assertIn(p1_id, product_ids_retrieved); self.assertIn(p3_id, product_ids_retrieved)
        if p2_id: self.assertNotIn(p2_id, product_ids_retrieved)
        for p_dict in ranked_products:
            self.assertIn('id', p_dict); self.assertIn('name_cn', p_dict)
            self.assertIn('description_cn', p_dict); self.assertIn('comment_summary_cn', p_dict)
            if p_dict['id'] == p1_id: self.assertEqual(p_dict['name_cn'], "P1_CN_Updated")
            if p_dict['id'] == p3_id:
                self.assertEqual(p_dict['description_cn'], "P3_DescCN_Updated")
                self.assertEqual(p_dict['comment_summary_cn'], "P3_SummCN_Updated")

    def test_get_all_products_for_markdown(self):
        source_md = "2023/06"
        today = datetime.date.today()
        ids = []
        # Define expected Chinese content
        expected_cn_content = {
            "name_cn": [f"MD_P{i+1}_CN" for i in range(3)],
            "description_cn": [f"MD_P{i+1}_DescCN" for i in range(3)],
            "comment_summary_cn": [f"MD_P{i+1}_SummCN" for i in range(3)],
        }

        for i in range(3):
            # Add product with only English fields initially
            pid = database.add_product({
                "name_en": f"MD_P{i+1}", "website_url": f"md_p{i+1}.com",
                "scraped_date": today, "weekly_leaderboard_source": source_md
            })
            self.assertIsNotNone(pid)
            ids.append(pid)
            # Update with Chinese content
            self.assertTrue(database.update_product_translation(pid, "name_cn", expected_cn_content["name_cn"][i]))
            self.assertTrue(database.update_product_translation(pid, "description_cn", expected_cn_content["description_cn"][i]))
            self.assertTrue(database.update_product_translation(pid, "comment_summary_cn", expected_cn_content["comment_summary_cn"][i]))
        self.added_product_ids.extend(ids)

        ordered_ids = [ids[1], ids[2], ids[0]]
        markdown_products = database.get_all_products_for_markdown(source_md, ordered_ids)

        self.assertEqual(len(markdown_products), 3)
        self.assertEqual([p['id'] for p in markdown_products], ordered_ids)

        for idx, p_dict in enumerate(markdown_products):
            original_product_index = ids.index(p_dict['id']) # Find which original product this is (0, 1, or 2)
            self.assertEqual(p_dict['name_en'], f"MD_P{original_product_index+1}")
            self.assertEqual(p_dict['website_url'], f"md_p{original_product_index+1}.com")
            self.assertEqual(p_dict['name_cn'], expected_cn_content["name_cn"][original_product_index])
            self.assertEqual(p_dict['description_cn'], expected_cn_content["description_cn"][original_product_index])
            self.assertEqual(p_dict['comment_summary_cn'], expected_cn_content["comment_summary_cn"][original_product_index])

if __name__ == '__main__':
    unittest.main()
