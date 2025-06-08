import os
import requests # Will be mocked for this subtask
from bs4 import BeautifulSoup
from .utils import log_error # Assuming utils.py is in the same directory (src)

# Define the directory where mock HTML files are stored.
MOCK_HTML_DIR = os.path.dirname(__file__)

def _get_mock_html(page_filename: str) -> str | None:
    """
    Reads the content of a mock HTML file.
    Simulates fetching HTML content for testing purposes.
    """
    filepath = os.path.join(MOCK_HTML_DIR, page_filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        log_error(f"Mock HTML file not found: {filepath}")
        return None
    except Exception as e:
        log_error(f"Error reading mock HTML file {filepath}: {e}")
        return None

def scrape_product_hunt_weekly(year: int, week: int) -> list[dict]:
    """
    Scrapes Product Hunt's weekly leaderboard for a given year and week using mock HTML.
    Extracts product name, description, website URL, and top 10 comments.
    """
    # Construct the URL (for eventual real implementation)
    # url = f"https://www.producthunt.com/leaderboard/weekly/{year}/{week:02d}"
    # log_error(f"Attempting to scrape: {url}") # For real scenario

    # Simulate fetching main leaderboard page
    # In a real scenario, this would be:
    # try:
    #     response = requests.get(url, timeout=10)
    #     response.raise_for_status()
    #     leaderboard_html = response.text
    # except requests.RequestException as e:
    #     log_error(f"Failed to fetch Product Hunt leaderboard for {year}/{week:02d}: {e}")
    #     return []

    leaderboard_html = _get_mock_html("mock_leaderboard.html")
    if not leaderboard_html:
        log_error(f"Failed to get mock leaderboard HTML for {year}/{week:02d}.")
        return []

    soup = BeautifulSoup(leaderboard_html, 'html.parser')
    products_data = []

    product_items = soup.select('div.product-item')[:10] # Limit to top 10 products

    for item in product_items:
        name_en_tag = item.select_one('h3.product-name')
        name_en = name_en_tag.text.strip() if name_en_tag else None

        description_en_tag = item.select_one('p.product-description')
        description_en = description_en_tag.text.strip() if description_en_tag else None

        website_url_tag = item.select_one('a.product-website-link')
        website_url = website_url_tag['href'] if website_url_tag and website_url_tag.has_attr('href') else None

        discussion_link_tag = item.select_one('a.product-discussion-link')
        discussion_page_filename = discussion_link_tag['href'] if discussion_link_tag and discussion_link_tag.has_attr('href') else None

        all_comment_texts_en = ""

        if not name_en:
            log_error(f"Product found with missing name. Description: '{description_en_tag.text.strip() if description_en_tag else 'N/A'}'")
        if not description_en:
            log_error(f"Product '{name_en}' found with missing description.")
        if not website_url:
            log_error(f"Product '{name_en}' found with missing website URL.")


        if discussion_page_filename:
            # log_error(f"Fetching comments for {name_en} from {discussion_page_filename}") # Debug
            discussion_html = _get_mock_html(discussion_page_filename)
            if discussion_html:
                discussion_soup = BeautifulSoup(discussion_html, 'html.parser')
                comment_tags = discussion_soup.select('div.comment-item p')[:10] # Limit to 10 comments
                comments_list = [tag.text.strip() for tag in comment_tags]
                if comments_list:
                    all_comment_texts_en = "||NEW COMMENT||".join(comments_list)
            else:
                log_error(f"Failed to get mock discussion HTML for product: {name_en} (file: {discussion_page_filename})")
        else:
            log_error(f"No discussion link found for product: {name_en}")

        products_data.append({
            "name_en": name_en or "", # Ensure string type
            "description_en": description_en or "", # Ensure string type
            "website_url": website_url or "", # Ensure string type
            "all_comment_texts_en": all_comment_texts_en
        })

    if not product_items:
        log_error("No product items found on the leaderboard page.")

    return products_data
