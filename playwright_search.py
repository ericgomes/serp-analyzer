import urllib.parse
import json
import csv
import time
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def handle_consent_if_needed(page):
    try:
        consent_selectors = [
            "button:has-text('Rejeitar tudo')",
            "button:has-text('Aceitar tudo')",
            "button:has-text('Accept all')",
            "button:has-text('Reject all')",
            "button:has-text('Concordo')",
            "button:has-text('I agree')",
            "#L2AGLb"
        ]
        
        for selector in consent_selectors:
            btn = page.locator(selector)
            if btn.count() > 0 and btn.is_visible():
                print(f"Consent prompt found. Clicking: '{selector}'")
                btn.click()
                page.wait_for_load_state("networkidle")
                break
    except Exception:
        pass

def check_captcha_and_wait(page):
    # Check if we are on a captcha page
    if "google.com/recaptcha" in page.url or page.locator("#captcha-form").count() > 0:
        print("\n" + "="*60)
        print("GOOGLE CAPTCHA DETECTED!")
        print("Please solve the CAPTCHA in the browser window that just opened.")
        print("Once you have solved it and see the search results, press Enter here to continue...")
        print("="*60 + "\n")
        input("Press Enter after solving the CAPTCHA...")
        page.wait_for_load_state("networkidle")

def scrape_page(page, query, start):
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded_query}&start={start}"
    print(f"Navigating to page starting at result {start}...")
    
    page.goto(url)
    page.wait_for_load_state("domcontentloaded")
    
    # Handle consent and CAPTCHAs
    handle_consent_if_needed(page)
    check_captcha_and_wait(page)
    
    # Extra check if captcha popped up after consent click
    check_captcha_and_wait(page)
    
    time.sleep(1.5)
    return page.content()

def parse_results(html_content, current_rank_start):
    soup = BeautifulSoup(html_content, "html.parser")
    results = []
    
    # Find results block
    search_blocks = soup.find_all("div", class_="g")
    
    # Fallback to search links that contain h3 tags directly
    links_with_h3 = []
    for a in soup.find_all("a", href=True):
        h3 = a.find("h3")
        if h3:
            href = a["href"]
            if href.startswith("/search?") or "google.com" in href and "search?" in href:
                continue
            links_with_h3.append((a, h3))
            
    if not search_blocks and links_with_h3:
        for a, h3 in links_with_h3:
            title = h3.get_text().strip()
            link = a["href"]
            
            if link.startswith("/url?q="):
                link = link.split("/url?q=")[1].split("&")[0]
                link = urllib.parse.unquote(link)
                
            if not link.startswith("http") or "google.com" in link:
                continue
                
            snippet = ""
            parent = a.find_parent("div")
            for _ in range(3):
                if not parent:
                    break
                divs = parent.find_all("div")
                for d in divs:
                    text = d.get_text().strip()
                    if text and text != title and len(text) > 40 and not text.startswith("http"):
                        snippet = text
                        break
                if snippet:
                    break
                parent = parent.parent
                
            results.append({
                "rank": current_rank_start + len(results) + 1,
                "title": title,
                "url": link,
                "snippet": snippet
            })
    else:
        for block in search_blocks:
            a_tag = block.find("a", href=True)
            h3_tag = block.find("h3")
            
            if not a_tag or not h3_tag:
                continue
                
            title = h3_tag.get_text().strip()
            link = a_tag["href"]
            
            if link.startswith("/url?q="):
                link = link.split("/url?q=")[1].split("&")[0]
                link = urllib.parse.unquote(link)
                
            if not link.startswith("http") or "google.com" in link:
                continue
                
            snippet = ""
            snippet_elem = block.find("div", class_="VwiC3b") or \
                           block.find("span", class_="aCOpRe") or \
                           block.find("div", {"style": "-webkit-line-clamp:2"}) or \
                           block.find("div", class_="kb0Bzd")
            
            if snippet_elem:
                snippet = snippet_elem.get_text().strip()
            else:
                divs = block.find_all("div")
                for d in divs:
                    text = d.get_text().strip()
                    if text and title not in text and len(text) > 40 and not text.startswith("http"):
                        snippet = text
                        break
                        
            results.append({
                "rank": current_rank_start + len(results) + 1,
                "title": title,
                "url": link,
                "snippet": snippet
            })
            
    return results

def main():
    query = '"Marcelo Baptista de Oliveira"'
    all_results = []
    results_needed = 100
    start_index = 0
    pages_checked = 0
    
    with sync_playwright() as p:
        # Launch headful browser so user can solve CAPTCHA
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        while len(all_results) < results_needed and pages_checked < 15:
            try:
                html = scrape_page(page, query, start_index)
                page_results = parse_results(html, len(all_results))
                
                if not page_results:
                    print("No search results found on this page. Google might have blocked us or layout has changed.")
                    # Keep browser open for debug if it fails
                    input("Press Enter to close browser and exit...")
                    break
                
                print(f"Found {len(page_results)} results on this page.")
                for pr in page_results:
                    if not any(ar["url"] == pr["url"] for ar in all_results):
                        pr["rank"] = len(all_results) + 1
                        all_results.append(pr)
                
                print(f"Total unique results collected so far: {len(all_results)}")
                
                if len(all_results) >= results_needed:
                    all_results = all_results[:results_needed]
                    break
                    
                start_index += 10
                pages_checked += 1
                
                # Polite sleep
                time.sleep(2)
            except Exception as e:
                print(f"An error occurred: {e}")
                break
                
        browser.close()
        
    if not all_results:
        print("No results could be parsed.")
        return
        
    print(f"\nSuccessfully retrieved {len(all_results)} results in total!")
    
    # Save files
    json_filename = "results.json"
    csv_filename = "results.csv"
    
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)
    print(f"Saved results to {json_filename}")
        
    with open(csv_filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["rank", "title", "url", "snippet"])
        writer.writeheader()
        writer.writerows(all_results)
    print(f"Saved results to {csv_filename}")

if __name__ == "__main__":
    main()
