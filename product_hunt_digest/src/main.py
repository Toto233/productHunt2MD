import datetime
from . import utils, scraper, database, llm # Using . for relative imports within the package

def run_digest_generation():
    """
    Main workflow to generate the Product Hunt digest.
    """
    utils.log_error("--- Starting Digest Generation Process ---")

    # 1. Initialize Database
    utils.log_error("Initializing database...")
    try:
        database.init_db()
        utils.log_error("Database initialized successfully.")
    except Exception as e:
        utils.log_error(f"CRITICAL: Database initialization failed: {e}. Exiting.")
        return # Exit if DB init fails

    # 2. Determine Target Week
    utils.log_error("Determining target week...")
    target_week_str = utils.get_previous_week_yyy_ww()
    if not target_week_str:
        utils.log_error("CRITICAL: Could not determine target week. Exiting.")
        return
    utils.log_error(f"Target week determined: {target_week_str}")

    try:
        year_str, week_str = target_week_str.split('/')
        year = int(year_str)
        week = int(week_str)
    except ValueError as e:
        utils.log_error(f"CRITICAL: Could not parse year and week from '{target_week_str}': {e}. Exiting.")
        return

    # 3. Scrape Data
    utils.log_error(f"Starting scraping for week: {target_week_str} (Year: {year}, Week: {week})")
    # Scraper will use mock HTML files set up in previous subtasks
    scraped_products = scraper.scrape_product_hunt_weekly(year, week)

    if not scraped_products:
        utils.log_error(f"No products found or scraping failed for week {target_week_str}. Exiting.")
        return
    utils.log_error(f"Scraping complete. Found {len(scraped_products)} products initially.")

    top_10_scraped_products = scraped_products[:10]
    utils.log_error(f"Processing top {len(top_10_scraped_products)} products.")

    # 4. Process and Store Each Product
    today_date_iso = datetime.date.today().isoformat()
    processed_product_count = 0

    for i, product_scraped_data in enumerate(top_10_scraped_products):
        utils.log_error(f"--- Processing product {i+1}/{len(top_10_scraped_products)}: {product_scraped_data.get('name_en', 'Unknown Name')} ---")

        product_data_to_store = {
            "name_en": product_scraped_data.get("name_en", ""),
            "description_en": product_scraped_data.get("description_en", ""),
            "website_url": product_scraped_data.get("website_url", ""),
            "all_comment_texts_en": product_scraped_data.get("all_comment_texts_en", ""),
            "scraped_date": today_date_iso,
            "weekly_leaderboard_source": target_week_str # Common for all products of this week
        }

        product_id = database.add_product(product_data_to_store)

        if product_id is None:
            utils.log_error(f"Failed to add product {product_data_to_store.get('name_en', 'Unknown Name')} to database. Skipping LLM processing for this product.")
            continue

        utils.log_error(f"Added product '{product_data_to_store.get('name_en')}' to DB with ID: {product_id}. Starting LLM processing.")

        # LLM Processing
        name_en = product_data_to_store.get("name_en")
        if name_en: # Only translate if there's a name
            name_cn = llm.translate_name(name_en)
            database.update_product_translation(product_id, "name_cn", name_cn)
            utils.log_error(f"  Translated name for product ID {product_id}: '{name_cn[:30]}...'")
        else:
            utils.log_error(f"  Skipped name translation for product ID {product_id} as English name is missing.")
            database.update_product_translation(product_id, "name_cn", llm.CONTENT_UNAVAILABLE_CN)


        description_en = product_data_to_store.get("description_en")
        if description_en: # Only translate if there's a description
            description_cn = llm.translate_description(description_en)
            database.update_product_translation(product_id, "description_cn", description_cn)
            utils.log_error(f"  Translated description for product ID {product_id}: '{description_cn[:30]}...'")
        else:
            utils.log_error(f"  Skipped description translation for product ID {product_id} as English description is missing.")
            database.update_product_translation(product_id, "description_cn", llm.DESCRIPTION_UNAVAILABLE_CN)


        comments_en = product_data_to_store.get("all_comment_texts_en")
        if comments_en: # Only summarize if there are comments
            comment_summary_cn = llm.summarize_comments(comments_en)
            database.update_product_translation(product_id, "comment_summary_cn", comment_summary_cn)
            utils.log_error(f"  Summarized comments for product ID {product_id}: '{comment_summary_cn[:30]}...'")
        else:
            utils.log_error(f"  Skipped comment summarization for product ID {product_id} as English comments are missing.")
            database.update_product_translation(product_id, "comment_summary_cn", llm.COMMENTS_UNAVAILABLE_CN)

        utils.log_error(f"Finished LLM tasks for product ID: {product_id}")
        processed_product_count +=1

    utils.log_error(f"--- Finished processing all {processed_product_count} products that were successfully added to DB. ---")
    utils.log_error("--- Digest Generation Process Completed ---")


if __name__ == "__main__":
    try:
        run_digest_generation()
    except Exception as e:
        # This is a last resort catch. Specific errors should be handled within functions.
        utils.log_error(f"CRITICAL_UNHANDLED_EXCEPTION in main: {e}", exc_info=True)
        # In a real script, you might also want to:
        # import traceback
        # utils.log_error(traceback.format_exc())
    finally:
        utils.log_error("--- Main script execution finished ---")
