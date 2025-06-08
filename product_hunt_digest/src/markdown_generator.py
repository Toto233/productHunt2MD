from datetime import datetime, timedelta, timezone
import os
from .utils import log_error

# Define specific placeholders for markdown if different from LLM's raw output
MD_NAME_UNAVAILABLE = "中文名称不可用"
MD_DESCRIPTION_UNAVAILABLE = "中文描述不可用"
MD_COMMENTS_UNAVAILABLE = "评论总结不可用"

def _get_week_date_range(year: int, week: int) -> tuple[str, str] | None:
    """
    Calculates the start (Monday) and end (Sunday) dates for the given ISO year and week.
    Returns a tuple (YYYYMMDD_start, YYYYMMDD_end) or None if calculation fails.
    """
    try:
        # Get the first day (Monday) of the given ISO year and week
        start_date = datetime.fromisocalendar(year, week, 1)
        # Sunday is 6 days after Monday
        end_date = start_date + timedelta(days=6)

        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")
        return start_date_str, end_date_str
    except ValueError as e:
        log_error(f"Error calculating date range for year {year}, week {week}: {e}")
        return None
    except Exception as e: # Catch any other unexpected errors
        log_error(f"Unexpected error in _get_week_date_range for year {year}, week {week}: {e}")
        return None


def generate_markdown_report(products: list[dict], target_week_str: str, output_dir: str = "output") -> str | None:
    """
    Generates a markdown report from a list of products.

    Args:
        products: List of product dictionaries, ordered for the report.
        target_week_str: The target week in "YYYY/WW" format.
        output_dir: The directory where the markdown file will be saved.

    Returns:
        The filepath of the generated markdown file, or None on failure.
    """
    if not products:
        log_error("generate_markdown_report: No products provided to generate report. Skipping.")
        return None

    try:
        year_str, week_str = target_week_str.split('/')
        year = int(year_str)
        week = int(week_str)
    except ValueError as e:
        log_error(f"generate_markdown_report: Invalid target_week_str format '{target_week_str}'. Error: {e}. Cannot generate report.")
        return None

    date_objects = {} # To store actual date objects for title formatting
    try:
        date_objects['start_date'] = datetime.fromisocalendar(year, week, 1)
        date_objects['end_date'] = date_objects['start_date'] + timedelta(days=6)
        start_date_str = date_objects['start_date'].strftime("%Y%m%d")
        end_date_str = date_objects['end_date'].strftime("%Y%m%d")
    except ValueError as e: # Handles invalid year/week for fromisocalendar
        log_error(f"Error creating date objects from year {year}, week {week}: {e}")
        return None


    filename = f"Product_Hunt_Digest_{start_date_str}_{end_date_str}.md"
    filepath = os.path.join(output_dir, filename)

    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            log_error(f"Created output directory: {output_dir}")
    except OSError as e:
        log_error(f"Error creating output directory {output_dir}: {e}. Cannot write report.")
        return None

    md_content = []
    # Use formatted dates for the title if available
    report_title_date_part = f"{date_objects['start_date'].strftime('%Y年%m月%d日')} - {date_objects['end_date'].strftime('%Y年%m月%d日')}"
    md_content.append(f"# 每周 Product Hunt 精选 - 潜在影响力 Top 10 ({report_title_date_part})\n")

    for rank, p in enumerate(products, 1):
        name_en = p.get('name_en', 'Unknown English Name')
        name_cn = p.get('name_cn', '') or MD_NAME_UNAVAILABLE
        description_cn = p.get('description_cn', '') or MD_DESCRIPTION_UNAVAILABLE
        website_url = p.get('website_url', '') or "#"
        comment_summary_cn = p.get('comment_summary_cn', '') or MD_COMMENTS_UNAVAILABLE

        md_content.append(f"## {rank}. {name_cn} ({name_en})\n")
        md_content.append(f"- **描述：** {description_cn}\n")
        md_content.append(f"- **网址：** {website_url}\n") # Ensure URL is clickable if it's a real URL
        md_content.append(f"- **评论摘要：** {comment_summary_cn}\n")

    try:
        full_md_text = "\n".join(md_content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_md_text)
        log_error(f"Markdown report generated successfully: {filepath}")
        return filepath
    except IOError as e:
        log_error(f"Error writing markdown file to {filepath}: {e}")
        return None
    except Exception as e:
        log_error(f"Unexpected error writing markdown file to {filepath}: {e}")
        return None
