from app.storage.hh_parser import parse_search_page


def test_parse_search_page_collects_standard_cards() -> None:
    html = """
    <div data-qa="vacancy-serp__vacancy vacancy-serp-item_clickme">
      <a data-qa="serp-item__title" href="/vacancy/123456789?from=search">
        <span data-qa="serp-item__title-text">Python Developer</span>
      </a>
      <span data-qa="vacancy-serp__vacancy-employer-text">Acme</span>
      <span data-qa="vacancy-serp__vacancy-address">Москва</span>
    </div>
    """

    items = parse_search_page(html)

    assert len(items) == 1
    assert items[0].vacancy_id == "123456789"
    assert items[0].title == "Python Developer"
    assert items[0].company == "Acme"
    assert items[0].location == "Москва"


def test_parse_search_page_falls_back_to_plain_links() -> None:
    html = """
    <html>
      <body>
        <a href="/vacancy/987654321?query=python">Backend Engineer</a>
      </body>
    </html>
    """

    items = parse_search_page(html)

    assert len(items) == 1
    assert items[0].vacancy_id == "987654321"
    assert items[0].title == "Backend Engineer"
