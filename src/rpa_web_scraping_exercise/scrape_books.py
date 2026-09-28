from decimal import Decimal
from typing import TypedDict
from urllib.parse import urljoin

from playwright.sync_api import Page

URL: str = "https://books.toscrape.com/"


class BookData(TypedDict):
    url: str
    name: str
    rating: int
    price: Decimal
    in_stock: bool


# Mapeamento do texto das estrelas no HTML para números inteiros
RATING_MAP: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


def _parse_rating(rating_class: str) -> int:
    classes = rating_class.lower().split()
    for cls in classes:
        if cls in RATING_MAP:
            return RATING_MAP[cls]
    return 0


def _extract_books_from_page(page: Page, max_books: int, collected_books: list[BookData]) -> None:
    articles = page.locator("article.product_pod")
    count = articles.count()

    for i in range(count):
        if len(collected_books) >= max_books:
            break

        article = articles.nth(i)

        # 1. Title e Absolute URL
        link = article.locator("h3 a")
        title = link.get_attribute("title") or link.inner_text()
        relative_url = link.get_attribute("href") or ""
        absolute_url = urljoin(page.url, relative_url)

        # 2. Rating (1 a 5)
        rating_element = article.locator("p.star-rating")
        rating_class = rating_element.get_attribute("class") or ""
        rating = _parse_rating(rating_class)

        # 3. Price (Decimal limpo sem £)
        price_text = article.locator("p.price_color").inner_text()
        clean_price = "".join(c for c in price_text if c.isdigit() or c == ".")
        price = Decimal(clean_price)

        # 4. Availability (in_stock)
        stock_text = article.locator(".instock.availability").inner_text()
        in_stock = "in stock" in stock_text.lower()

        collected_books.append(
            BookData(
                url=absolute_url,
                name=title,
                rating=rating,
                price=price,
                in_stock=in_stock,
            )
        )


def scrape_books(page: Page, *, category: str | None, max_books: int) -> list[BookData]:
    if max_books <= 0:
        return []

    ## 1. Validação de categoria vazia ou composta só de espaços
    if category is not None and not category.strip():
        return []

    ## 2. Navegar para a homepage
    page.goto(URL)

    ## 3. Filtrar por Categoria (se fornecida)
    if category is not None:
        sidebar_links = page.locator("div.side_categories ul.nav-list ul li a")
        category_count = sidebar_links.count()

        target_link = None
        clean_category = category.strip().lower()

        for i in range(category_count):
            link = sidebar_links.nth(i)
            cat_name = link.inner_text().strip().lower()
            if cat_name == clean_category:
                target_link = link
                break

        ## Categoria não encontrada na sidebar
        if target_link is None:
            return []

        ## Navega para a categoria correspondente
        target_link.click()

    ## 4. Loop de coleta de dados com paginação
    books: list[BookData] = []

    while True:
        _extract_books_from_page(page, max_books, books)

        if len(books) >= max_books:
            break

        ## Paginação
        next_button = page.locator("li.next a")
        if next_button.count() > 0 and next_button.is_visible():
            next_button.click()
        else:
            break

    return books


    ## uv run python -m rpa_web_scraping_exercise.main --category Travel --max-books 5