from fake_useragent import UserAgent


ua = UserAgent()

GITHUB_BASE_URL = "https://github.com"
GITHUB_SEARCH_URL = f"{GITHUB_BASE_URL}/search"
PROXY_SEARCH_URL = "https://free-proxy-list.net/"

SEARCH_TYPES = [
    "Repositories",
    "Issues",
    "Wikis",
]

HEADERS = {"User-Agent": ua.random}
