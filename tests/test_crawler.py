import unittest
from unittest.mock import Mock, patch

import crawler


class TestGitHubCrawler(unittest.TestCase):
    @patch("crawler.requests.get")
    def test_fetch_free_proxies(self, mock_get):
        html = """
        <div class="table-responsive">
            <table>
                <tbody>
                    <tr><td>1.1.1.1</td><td>8080</td><td></td><td></td><td></td><td></td><td>yes</td></tr>
                    <tr><td>2.2.2.2</td><td>3128</td><td></td><td></td><td></td><td></td><td>no</td></tr>
                    <tr><td>3.3.3.3</td><td>8000</td><td></td><td></td><td></td><td></td><td>yes</td></tr>
                </tbody>
            </table>
        </div>
        """
        mock_resp = Mock()
        mock_resp.text = html
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        proxies = crawler.fetch_free_proxies(limit=5)
        self.assertEqual(proxies, ["1.1.1.1:8080", "3.3.3.3:8000"])
        self.assertEqual(len(proxies), 2)

    def test_get_random_proxy(self):
        proxies = ["1.1.1.1:8080", "3.3.3.3:8000"]
        proxy_dict = crawler.get_random_proxy(proxies)
        self.assertIn(proxy_dict["http"][7:], proxies)
        self.assertIn(proxy_dict["https"][7:], proxies)

    def test_build_search_url_valid(self):
        crawler.SEARCH_TYPES = ["Repositories", "Issues"]
        url = crawler.build_search_url(["python", "fastapi"], "Repositories")
        self.assertIn("python+fastapi", url)
        self.assertIn("type=Repositories", url)

    def test_build_search_url_invalid(self):
        crawler.SEARCH_TYPES = ["Repositories", "Issues"]
        with self.assertRaises(ValueError):
            crawler.build_search_url(["python"], "InvalidType")

    @patch("crawler.requests.get")
    def test_fetch_html(self, mock_get):
        mock_resp = Mock()
        mock_resp.text = "<html>ok</html>"
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        html = crawler.fetch_html("http://example.com", {"http": "proxy"})
        self.assertEqual(html, "<html>ok</html>")

    def test_parse_search_results(self):
        html = """
        <a class="prc-Link-Link-123" href="/user/repo1"></a>
        <a class="prc-Link-Link-456" href="/user/repo2"></a>
        <a class="other-class" href="/user/repo3"></a>
        """
        results = crawler.parse_search_results(html, "Repositories")
        self.assertEqual(results, {"/user/repo1", "/user/repo2"})

    @patch("crawler.fetch_html")
    def test_parse_repo_languages(self, mock_fetch):
        html = """
        <li class="d-inline">
            <a>
                <span class="color-fg-default text-bold mr-1">Python</span>
                <span>80.0%</span>
            </a>
        </li>
        <span class="d-inline-flex">
            <span>Other</span>
            <span>20.0%</span>
        </span>
        """
        mock_fetch.return_value = html
        languages = crawler.parse_repo_languages("http://repo", {"http": "proxy"})
        self.assertEqual(languages, {"Python": 80.0, "Other": 20.0})

    @patch("crawler.parse_repo_languages")
    def test_process_repo(self, mock_parse):
        mock_parse.return_value = {"Python": 100.0}
        result = crawler.process_repo("/user/repo", {"http": "proxy"})
        self.assertEqual(result["url"], crawler.GITHUB_BASE_URL + "/user/repo")
        self.assertEqual(result["extra"]["owner"], "user")
        self.assertEqual(result["extra"]["language_stats"], {"Python": 100.0})

    @patch("crawler.fetch_html")
    @patch("crawler.get_random_proxy")
    @patch("crawler.fetch_free_proxies")
    def test_crawler_non_repos(self, mock_free, mock_random, mock_fetch):
        mock_free.return_value = ["1.1.1.1:8080"]
        mock_random.return_value = {"http": "1.1.1.1:8080", "https": "1.1.1.1:8080"}
        mock_fetch.return_value = """
        <a class="prc-Link-Link-123" href="/user/repo1"></a>
        <a class="prc-Link-Link-456" href="/user/repo2"></a>
        """
        results = crawler.github_crawler(["python"], [], "Issues")
        self.assertEqual(len(results), 2)
        self.assertTrue(all("url" in r for r in results))

    @patch("crawler.process_repo")
    @patch("crawler.parse_search_results")
    @patch("crawler.fetch_html")
    @patch("crawler.get_random_proxy")
    @patch("crawler.fetch_free_proxies")
    def test_github_crawler_repos(
        self, mock_free, mock_random, mock_fetch, mock_parse_results, mock_process
    ):
        mock_free.return_value = ["1.1.1.1:8080"]
        mock_random.return_value = {"http": "1.1.1.1:8080", "https": "1.1.1.1:8080"}
        mock_fetch.return_value = "<html></html>"
        mock_parse_results.return_value = {"/user/repo1", "/user/repo2"}
        mock_process.side_effect = lambda r, p: {
            "url": crawler.GITHUB_BASE_URL + r,
            "extra": {
                "owner": r.strip("/").split("/")[0],
                "language_stats": {"Python": 100.0},
            },
        }

        results = crawler.github_crawler(["python"], [], "Repositories")
        self.assertEqual(len(results), 2)
        self.assertTrue(all("extra" in r for r in results))
        self.assertTrue(
            all(r["extra"]["language_stats"]["Python"] == 100.0 for r in results)
        )


if __name__ == "__main__":
    unittest.main()
