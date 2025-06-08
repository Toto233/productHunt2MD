import time # For potential (though not used in mock) delays
from .utils import get_api_key, log_error # log_error is imported directly

# --- Placeholders for unsuccessful operations ---
PROCESSING_FAILED_CN = "处理失败"
CONTENT_UNAVAILABLE_CN = "内容不可用" # For product name
DESCRIPTION_UNAVAILABLE_CN = "描述不可用" # For product description
COMMENTS_UNAVAILABLE_CN = "评论总结不可用" # For comment summary

# --- Internal Helper for Mock LLM API Call ---
def _call_llm_api(api_key_name: str, prompt: str, purpose: str) -> str | None:
    """
    Simulates an LLM API call.
    - api_key_name: "gemini" or "grok"
    - prompt: The full prompt string.
    - purpose: A string for logging (e.g., "Product Name Translation").
    Returns a mock response string or None if the API call "fails".
    """
    log_message_prefix = f"LLM API Call ({api_key_name} for {purpose})"

    api_key_config_name = f"{api_key_name}_api_key" # e.g., "gemini_api_key"

    # This is a reference to utils.get_api_key, may be patched by tests
    # The get_api_key function is imported directly, so it's in the current module's namespace.
    active_get_api_key = get_api_key

    api_key_value = active_get_api_key(api_key_config_name)

    if api_key_value is None:
        log_error(f"{log_message_prefix}: API key '{api_key_config_name}' not found.")
        return None
    if api_key_value in ["YOUR_GEMINI_KEY_HERE", "YOUR_GROK_KEY_HERE"]:
        log_error(f"{log_message_prefix}: API key '{api_key_config_name}' is a placeholder. Please configure it.")
        return None

    log_error(f"{log_message_prefix}: Attempting with prompt (first 200 chars): '{prompt[:200]}...'")

    if "FAIL_PRIMARY_RERANK" in prompt and api_key_name == "gemini":
        log_error(f"{log_message_prefix}: Simulated primary LLM (Gemini) failure for reranking.")
        return None
    if "FAIL_SECONDARY_RERANK" in prompt and api_key_name == "grok":
        log_error(f"{log_message_prefix}: Simulated secondary LLM (Grok) failure for reranking.")
        return None
    if "FAIL_PRIMARY" in prompt and api_key_name == "gemini":
        log_error(f"{log_message_prefix}: Simulated primary LLM (Gemini) failure.")
        return None
    if "FAIL_SECONDARY" in prompt and api_key_name == "grok":
        log_error(f"{log_message_prefix}: Simulated secondary LLM (Grok) failure.")
        return None

    if purpose == "Product Re-ranking":
        mock_response = f"MockResponse_from_{api_key_name}_for_{purpose}: Processed (default - tests should mock specific name list)"
    else:
        mock_response = f"MockResponse_from_{api_key_name}_for_{purpose}: Processed '{prompt[:30]}...'"

    log_error(f"{log_message_prefix}: Success. Response: '{mock_response}'")
    return mock_response

def translate_text(text_en: str, prompt_core: str, llm_purpose: str) -> str:
    if not text_en or not text_en.strip():
        log_error(f"{llm_purpose}: Input text is empty or whitespace. Skipping translation.")
        if "Name" in llm_purpose: return CONTENT_UNAVAILABLE_CN
        if "Description" in llm_purpose: return DESCRIPTION_UNAVAILABLE_CN
        if "Comment" in llm_purpose: return COMMENTS_UNAVAILABLE_CN
        return PROCESSING_FAILED_CN

    full_prompt = f"{prompt_core} {text_en}"
    primary_result = _call_llm_api("gemini", full_prompt, llm_purpose)
    if primary_result is not None:
        return primary_result

    log_error(f"Primary LLM (Gemini) failed for {llm_purpose}. Trying fallback (Grok).")
    fallback_result = _call_llm_api("grok", full_prompt, llm_purpose)
    if fallback_result is not None:
        return fallback_result

    log_error(f"Both Gemini and Grok LLMs failed for {llm_purpose} on text: '{text_en[:50]}...'")
    return PROCESSING_FAILED_CN

def translate_name(name_en: str) -> str:
    if not name_en or not name_en.strip():
        log_error("translate_name: English name is empty or whitespace.")
        return CONTENT_UNAVAILABLE_CN
    prompt_core = "Translate the following English product name accurately into Chinese:"
    return translate_text(name_en, prompt_core, "Product Name Translation")

def translate_description(description_en: str) -> str:
    if not description_en or not description_en.strip():
        log_error("translate_description: English description is empty or whitespace.")
        return DESCRIPTION_UNAVAILABLE_CN
    prompt_core = "Translate the following English product description accurately into Chinese:"
    return translate_text(description_en, prompt_core, "Product Description Translation")

def summarize_comments(all_comment_texts_en: str) -> str:
    if not all_comment_texts_en or not all_comment_texts_en.strip():
        log_error("summarize_comments: English comment texts are empty or whitespace.")
        return COMMENTS_UNAVAILABLE_CN
    prompt_core = (
        "Summarize the following English product comments (delimited by '||NEW COMMENT||') "
        "into a concise Chinese summary of 100-200 words. The summary should focus on "
        "overall user sentiment, key themes, main pros and cons mentioned, and any "
        "significant questions raised by users. Comments:"
    )
    return translate_text(all_comment_texts_en, prompt_core, "Comment Summarization and Translation to Chinese")

def rerank_products(products_data: list[dict]) -> list[int]:
    original_ids = [p['id'] for p in products_data]

    if not products_data:
        log_error("rerank_products: No products provided for re-ranking. Returning empty list.")
        return []

    if len(products_data) != 10:
        # Use the imported log_error directly
        log_error(f"rerank_products: Expected 10 products for re-ranking, got {len(products_data)}. Proceeding, but this might affect ranking quality or prompt expectations.")

    prompt_core = (
        "Given the following products, each with its Chinese name, Chinese description, and "
        "Chinese comment summary, please re-rank them from 1 (most impactful) to 10 (least impactful), "
        "or fewer if fewer than 10 products are provided. "
        "The primary criterion for ranking is 'Potential Impact,' defined as 'how much this product "
        "could change things or help people.' Evaluate this based on the provided information. "
        "Output only the list of product Chinese names in the new order, each on a new line. "
        "Ensure all and only the provided product names are present in your output. Products:\n"
    )

    formatted_products_info = []
    for p in products_data:
        name = p.get('name_cn', CONTENT_UNAVAILABLE_CN)
        desc = p.get('description_cn', DESCRIPTION_UNAVAILABLE_CN)
        summ = p.get('comment_summary_cn', COMMENTS_UNAVAILABLE_CN)
        formatted_products_info.append(f"- Name: {name}\n  Description: {desc}\n  Summary: {summ}\n")

    full_prompt = prompt_core + "\n".join(formatted_products_info)
    llm_purpose = "Product Re-ranking"
    ranked_list_str = None

    gemini_response = _call_llm_api("gemini", full_prompt, llm_purpose)
    if gemini_response:
        ranked_list_str = gemini_response
    else:
        log_error(f"Primary LLM (Gemini) failed for {llm_purpose}. Trying fallback (Grok).")
        grok_response = _call_llm_api("grok", full_prompt, llm_purpose)
        if grok_response:
            ranked_list_str = grok_response
        else:
            log_error(f"Both Gemini and Grok LLMs failed for {llm_purpose}. Returning original order of IDs.")
            return original_ids

    if not ranked_list_str or not ranked_list_str.strip():
        log_error(f"{llm_purpose}: LLM returned an empty or whitespace response. Returning original order of IDs.")
        return original_ids

    ordered_names_cn_from_llm = [name.strip() for name in ranked_list_str.split('\n') if name.strip()]

    if len(ordered_names_cn_from_llm) != len(products_data):
        log_error(f"{llm_purpose}: LLM returned {len(ordered_names_cn_from_llm)} product names, but expected {len(products_data)}. Response: '{ranked_list_str}'. Returning original order.")
        return original_ids

    available_products = list(products_data)
    newly_ordered_ids = []

    for llm_name_cn in ordered_names_cn_from_llm:
        found_match = False
        for i, product_info in enumerate(available_products):
            original_name_cn = product_info.get('name_cn', CONTENT_UNAVAILABLE_CN)
            if original_name_cn == llm_name_cn:
                newly_ordered_ids.append(product_info['id'])
                available_products.pop(i)
                found_match = True
                break

        if not found_match:
            log_error(f"{llm_purpose}: LLM returned product name '{llm_name_cn}' which was not found in the input list or was already matched. Returning original order.")
            return original_ids

    if len(newly_ordered_ids) != len(products_data):
        log_error(f"{llm_purpose}: Failed to reconstruct a full ordered list. Matched {len(newly_ordered_ids)} out of {len(products_data)}. Returning original order.")
        return original_ids

    log_error(f"{llm_purpose}: Successfully re-ranked products. New order: {newly_ordered_ids}")
    return newly_ordered_ids
