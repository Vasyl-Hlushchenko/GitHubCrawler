import json

from crawler import github_crawler


if __name__ == "__main__":
    input_data = {
        "keywords": ["python", "django-rest-framework", "jwt"],
        "proxies": [],
        "type": "Repositories",
    }

    results = github_crawler(
        input_data["keywords"], input_data["proxies"], input_data["type"]
    )
    print(json.dumps(results, indent=2, ensure_ascii=False))
