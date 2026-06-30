# Retail Site Product Research — browser_vision Pattern

## The Problem

Major retail sites (Amazon, John Lewis, Currys, and manufacturer sites like Brother UK) aggressively block non-browser HTTP clients. Attempting:

- **curl/terminal scraping** → returns gzipped binary, CAPTCHA walls, or Cloudflare blocks
- **browser text snapshot** → heavily truncated (1000+ lines), product data buried in DOM noise
- **scrapling** → may work for some sites but not reliably on JS-heavy SPAs

## The Fix

**Use `browser_vision(question)` as the primary extraction tool.** It takes a screenshot of the rendered page and uses vision analysis to return structured data straight from the pixels — bypassing all DOM/truncation/blocking issues.

## Amazon UK Pattern (verified working)

### Search Results Page

```python
browser_navigate(f"https://www.amazon.co.uk/s?k={product_name}")
# Wait for page to render (browser_navigate already waits)
browser_vision(question="What are the prices of the printer listings?")
```

**What you get back:** structured description of each product listing including:
- Full product title
- Current price (with RRP/strikethrough if discounted)
- Star rating + number of reviews
- Delivery speed ("FREE delivery tomorrow")
- Stock status ("Only 15 left", "50+ bought this month")
- Additional offers ("4 month free trial", "Service Setup")
- Which listings are Amazon direct vs 3rd-party sellers

### Comparison Pattern

For comparing two products, query each separately:
```python
# Product A
browser_navigate("https://www.amazon.co.uk/s?k=Brother+DCP-L3520CDWE")
a_data = browser_vision(question="Prices and specs for this printer")
# Product B
browser_navigate("https://www.amazon.co.uk/s?k=Brother+MFC-L3740CDWE")
b_data = browser_vision(question="Prices and specs for this printer")
```

### Known Limitations

- Vision returns a narrative description, not structured JSON — you'll need to extract key:value pairs manually
- Image URLs and specific ASINs are rarely visible in the output
- Some sponsored products may appear mixed with organic results (vision usually calls these out)
- Prices change frequently — verify at checkout
- Works best with specific product model numbers in the search query

## Other Sites

This pattern works for any JS-heavy retail site where:
- curl returns `Service Unavailable`, Cloudflare, or gzipped junk
- Browser snapshot is truncated but the page renders successfully
- You need prices, specs, or availability data

Examples that work: John Lewis, Currys, Argos (partial — simpler site, curl sometimes works), printer specialist retailers.
