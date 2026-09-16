import asyncio
import json
import os
import re
from datetime import datetime
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


# ============================================================
# CONFIG
# ============================================================

DISEASES = [
    "diabetes",
    "malaria",
    "tuberculosis",
    "dengue",
    "pneumonia",
    "asthma",
    "hypertension",
    "influenza",
    "parkinson disease",
    "alzheimer disease",
]

OUTPUT_DIR = "knowledge_base"

# Trusted medical sources
TRUSTED_DOMAINS = [
    "who.int",
    "cdc.gov",
    "nih.gov",
    "ncbi.nlm.nih.gov",
    "medlineplus.gov",
    "mayoclinic.org",
]


# ============================================================
# HELPERS
# ============================================================

def clean_name(text):
    return re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        text.lower()
    ).strip("_")


def get_domain(url):
    try:
        return urlparse(url).netloc.lower()
    except:
        return ""


def is_trusted(url):
    domain = get_domain(url)

    return any(
        d in domain
        for d in TRUSTED_DOMAINS
    )


# ============================================================
# DUCKDUCKGO SEARCH
# ============================================================

async def search_web(page, disease):

    query = (
        f"{disease} medical information "
        f"WHO CDC NIH"
    )

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    print("   🔎 Searching:", query)

    try:

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        await page.wait_for_timeout(1000)

        results = await page.locator(
            "a.result__a"
        ).evaluate_all("""
            els => els.map(a => ({
                title: a.innerText,
                url: a.href
            }))
        """)

        # Only authoritative sources
        results = [
            r for r in results
            if is_trusted(r["url"])
        ]

        # Remove duplicates
        seen = set()
        unique = []

        for r in results:

            if r["url"] not in seen:

                seen.add(r["url"])
                unique.append(r)

        return unique[:10]

    except Exception as e:

        print(
            "   ❌ Search error:",
            str(e)[:150]
        )

        return []


# ============================================================
# DIRECT SEARCH FALLBACK
# ============================================================

async def direct_sources(page, disease):

    """
    If search engines fail completely,
    directly query authoritative sites.
    """

    queries = [

        f"https://www.who.int/search?query={quote(disease)}",

        f"https://www.cdc.gov/search/?query={quote(disease)}",

        f"https://www.ncbi.nlm.nih.gov/search/all/?term={quote(disease)}",

        f"https://medlineplus.gov/search.html?query={quote(disease)}",

    ]

    results = []

    for url in queries:

        try:

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=20000
            )

            links = await page.locator(
                "a"
            ).evaluate_all("""
                els => els.map(a => ({
                    title: a.innerText,
                    url: a.href
                }))
            """)

            for x in links:

                if (
                    x["url"].startswith("http")
                    and is_trusted(x["url"])
                ):

                    results.append(x)

        except:
            continue

    return results[:10]


# ============================================================
# EXTRACT PAGE
# ============================================================

async def extract_page(page, url):

    try:

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000
        )

        await page.wait_for_timeout(1500)

        final_url = page.url

        # Don't save redirects to search/error pages
        if (
            "google.com/sorry" in final_url
            or "captcha" in final_url.lower()
            or "access-denied" in final_url.lower()
        ):
            return None

        content_type = await page.evaluate("""
            () => document.contentType
        """)

        # ----------------------------------------------------
        # PDF
        # ----------------------------------------------------

        if (
            "application/pdf" in content_type
            or ".pdf" in final_url.lower()
        ):

            response = await page.request.get(
                final_url,
                timeout=60000
            )

            data = await response.body()

            if data.startswith(b"%PDF"):

                return {
                    "type": "pdf",
                    "url": final_url,
                    "data": data
                }

        # ----------------------------------------------------
        # HTML
        # ----------------------------------------------------

        html = await page.content()

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "noscript",
            "form",
            "aside"
        ]):
            tag.decompose()

        title = (
            soup.title.get_text(
                " ",
                strip=True
            )
            if soup.title
            else ""
        )

        main = (
            soup.find("main")
            or soup.find("article")
            or soup.body
        )

        if not main:
            return None

        text = main.get_text(
            "\n",
            strip=True
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        # Reject tiny/error pages
        if len(text) < 1000:
            return None

        return {
            "type": "html",
            "url": final_url,
            "title": title,
            "text": text
        }

    except Exception as e:

        print(
            "   ⚠️ Extraction failed:",
            str(e)[:100]
        )

        return None


# ============================================================
# SAVE
# ============================================================

def save_source(
    disease,
    number,
    source
):

    disease_dir = os.path.join(
        OUTPUT_DIR,
        clean_name(disease)
    )

    os.makedirs(
        disease_dir,
        exist_ok=True
    )

    if source["type"] == "pdf":

        filename = (
            f"{clean_name(disease)}_"
            f"{number}.pdf"
        )

        path = os.path.join(
            disease_dir,
            filename
        )

        with open(path, "wb") as f:
            f.write(source["data"])

    else:

        filename = (
            f"{clean_name(disease)}_"
            f"{number}.txt"
        )

        path = os.path.join(
            disease_dir,
            filename
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                f"TITLE: {source['title']}\n"
            )

            f.write(
                f"SOURCE: {source['url']}\n"
            )

            f.write(
                f"RETRIEVED: "
                f"{datetime.now().isoformat()}\n"
            )

            f.write(
                "\n"
                + "=" * 70
                + "\n\n"
            )

            f.write(source["text"])

    return filename


# ============================================================
# MAIN
# ============================================================

async def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page(
            viewport={
                "width": 1366,
                "height": 768
            }
        )

        for disease in DISEASES:

            print("\n" + "=" * 70)
            print("DISEASE:", disease)
            print("=" * 70)

            results = await search_web(
                page,
                disease
            )

            # Search fallback
            if not results:

                print(
                    "   ⚠️ Search returned nothing."
                )

                results = await direct_sources(
                    page,
                    disease
                )

            print(
                f"   Found {len(results)} sources"
            )

            records = []
            saved = 0

            for result in results:

                if saved >= 5:
                    break

                url = result["url"]

                print(
                    "\n   →",
                    url[:120]
                )

                source = await extract_page(
                    page,
                    url
                )

                if not source:

                    print(
                        "      ❌ Not usable"
                    )

                    continue

                saved += 1

                filename = save_source(
                    disease,
                    saved,
                    source
                )

                domain = get_domain(
                    source["url"]
                )

                print(
                    f"      ✅ {source['type'].upper()}"
                )

                print(
                    f"      📄 {filename}"
                )

                records.append({
                    "disease": disease,
                    "title": result.get(
                        "title",
                        ""
                    ),
                    "source": source["url"],
                    "domain": domain,
                    "type": source["type"],
                    "file": filename,
                    "retrieved_at":
                        datetime.now().isoformat()
                })

                await asyncio.sleep(1)

            # ------------------------------------------------
            # Metadata
            # ------------------------------------------------

            disease_dir = os.path.join(
                OUTPUT_DIR,
                clean_name(disease)
            )

            with open(
                os.path.join(
                    disease_dir,
                    "metadata.json"
                ),
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    records,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

            print(
                f"\n   📦 {saved} usable sources saved"
            )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())