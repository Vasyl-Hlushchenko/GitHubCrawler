import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    GITHUB_BASE_URL,
    GITHUB_SEARCH_URL,
    PROXY_SEARCH_URL,
    SEARCH_TYPES,
    HEADERS,
)


def fetch_free_proxies(limit: int = 10) -> list[str]:
    """
    Parses fresh HTTPS proxies from free-proxy-list.net.
    Returns a list of proxies in the format 'IP:Port'.
    """
    response = requests.get(PROXY_SEARCH_URL, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("div", class_="table-responsive").find("table")
    if not table or not table.tbody:
        return []

    proxies = []
    for row in table.tbody.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) < 7:
            continue

        ip = cols[0].text.strip()
        port = cols[1].text.strip()
        https = cols[6].text.strip()

        if https.lower() == "yes":
            proxies.append(f"{ip}:{port}")

        if len(proxies) >= limit:
            break

    return proxies


def get_random_proxy(proxies: list[str]) -> dict[str, str]:
    """
    Selects a random proxy from the list and returns it in the format suitable for requests.
    """
    proxy = random.choice(proxies)

    return {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}",
    }


def build_search_url(keywords: list[str], search_type: str) -> str:
    """
    Builds a GitHub search URL for the given keywords and search type.
    Raises a ValueError if the search type is invalid.
    """
    if search_type not in SEARCH_TYPES:
        raise ValueError(f"Invalid search type. Must be one of {SEARCH_TYPES}")

    query = "+".join(keywords)

    return f"{GITHUB_SEARCH_URL}?q={query}&type={search_type}"


def fetch_html(url: str, proxies: dict[str, str]) -> str:
    """
    Fetches the HTML content of a URL using the provided proxy settings.
    Uses a random User-Agent for the request and raises an exception on HTTP errors.
    """

    response = requests.get(
        url, headers=HEADERS, proxies=proxies, timeout=10, verify=True
    )

    return response.text


def parse_search_results(html: str) -> list[dict[str, str]]:
    """
    Parses GitHub search results from the first page of HTML.
    Supports processing of search types: Repositories, Issues, Wikis.
    Returns a set of repository URLs.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = set()

    for link_tag in soup.find_all("a"):
        classes = link_tag.get("class", [])
        if classes and classes[0].startswith("prc-Link-Link"):
            results.add(link_tag.get("href"))

    return results


def parse_repo_languages(repo_url: str, proxy: dict) -> dict[str, float]:
    """
    Parses the language statistics of a GitHub repository.
    Includes all languages, including 'Other'.
    Returns a dictionary with language names as keys and percentages as float values.
    """
    repo_html = fetch_html(repo_url, proxy)
    soup = BeautifulSoup(repo_html, "html.parser")

    language_stats = {}

    for lang_item in soup.select("li.d-inline a, span.d-inline-flex"):
        spans = lang_item.find_all("span")
        if len(spans) < 2:
            continue

        lang_name = spans[0].get_text(strip=True)
        if lang_name in language_stats:
            continue

        lang_percent = float(spans[1].get_text(strip=True).strip("%"))
        language_stats[lang_name] = lang_percent

    return language_stats


def process_repo(result: str, proxy: dict[str, str]) -> dict[str, dict[str, str]]:
    """
    Processes a single GitHub repository URL.
    Fetches its language statistics and extracts the owner.
    Returns a dictionary with 'url' and 'extra' containing 'owner' and 'language_stats'.
    """
    repo_url = f"{GITHUB_BASE_URL}{result}"
    owner = result.strip("/").split("/")[0]
    language_stats = parse_repo_languages(repo_url, proxy)

    return {
        "url": repo_url,
        "extra": {"owner": owner, "language_stats": language_stats},
    }


def github_crawler(
    keywords: list[str], proxies: list[str], search_type: str
) -> list[dict[str, str]]:
    """
    Crawls GitHub for the given keywords and search type.
    Uses proxies to fetch pages and supports parallel processing for repository details.
    Returns a list of dictionaries with repository URLs and extra information including owner and language statistics.
    """
    url = build_search_url(keywords, search_type)
    proxies = fetch_free_proxies() if not proxies else proxies
    proxy = get_random_proxy(proxies)
    html = fetch_html(url, proxy)
    results = parse_search_results(html)
    if search_type != "Repositories":
        return [{"url": f"{GITHUB_BASE_URL}{result}"} for result in results]

    extra_results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_repo, result, proxy) for result in results]
        for future in as_completed(futures):
            try:
                extra_results.append(future.result())
            except Exception as e:
                print(f"Error processing repo: {e}")

    return extra_results
