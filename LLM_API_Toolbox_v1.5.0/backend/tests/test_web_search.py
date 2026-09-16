from app.web_search import WebSearchService, normalize_result_url, parse_bing_rss, parse_results


def test_duckduckgo_html_results_are_parsed_and_redirects_unwrapped():
    html = """
    <div class="result">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fnews">Example news</a>
      <a class="result__snippet">A current result snippet.</a>
    </div>
    <a class="result__a" href="javascript:void(0)">Unsafe</a>
    """
    results = parse_results(html, 5)
    assert len(results) == 1
    assert results[0].title == "Example news"
    assert results[0].url == "https://example.com/news"
    assert results[0].snippet == "A current result snippet."
    assert normalize_result_url("javascript:void(0)") is None


async def test_search_context_is_marked_untrusted(monkeypatch):
    service = WebSearchService()

    async def fake_search(query):
        assert query == "今天有什么新闻"
        return parse_results(
            '<a class="result__a" href="https://example.com/latest">最新消息</a>',
            5,
        )

    monkeypatch.setattr(service, "search", fake_search)
    prompt = await service.enrich_system_prompt("今天有什么新闻", "原系统提示")
    assert "原系统提示" in prompt
    assert "不可信外部资料" in prompt
    assert "https://example.com/latest" in prompt
    assert "<web_search_results>" in prompt


def test_bing_rss_results_are_parsed():
    xml = """<?xml version="1.0"?>
    <rss><channel><item><title>Search result</title>
    <link>https://example.org/article</link>
    <description>Result description</description></item></channel></rss>"""
    results = parse_bing_rss(xml, 5)
    assert len(results) == 1
    assert results[0].title == "Search result"
    assert results[0].url == "https://example.org/article"
    assert results[0].snippet == "Result description"
