import urllib.parse
import json
import csv
import time
import sys
import os
import requests
from bs4 import BeautifulSoup

def search_google_page(query, start=0):
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded_query}&start={start}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code} from Google at start={start}.")
            if response.status_code == 429:
                print("Google rate-limited the request (Too Many Requests / CAPTCHA).")
            return None, response.status_code
            
        return response.text, response.status_code
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, 500

def parse_results(html_content, current_rank_start):
    soup = BeautifulSoup(html_content, "html.parser")
    results = []
    
    # Try looking for search result blocks (commonly div class="g" or similar containers)
    search_blocks = soup.find_all("div", class_="g")
    
    # Fallback to search links that contain h3 tags directly
    links_with_h3 = []
    for a in soup.find_all("a", href=True):
        h3 = a.find("h3")
        if h3:
            # Avoid site links, people also ask, etc. by checking if the URL starts with /search?
            href = a["href"]
            if href.startswith("/search?") or "google.com" in href and "search?" in href:
                continue
            links_with_h3.append((a, h3))
            
    # Use the parsing strategy that yields results
    if not search_blocks and links_with_h3:
        for idx, (a, h3) in enumerate(links_with_h3):
            title = h3.get_text().strip()
            link = a["href"]
            
            if link.startswith("/url?q="):
                link = link.split("/url?q=")[1].split("&")[0]
                link = urllib.parse.unquote(link)
                
            # Basic cleaning of Google search result redirect links
            if not link.startswith("http"):
                continue
                
            snippet = ""
            # Try to find snippet
            parent = a.find_parent("div")
            # Go up a few levels if needed
            for _ in range(3):
                if not parent:
                    break
                # Look for potential text blocks
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
                
            if not link.startswith("http"):
                continue
                
            snippet = ""
            snippet_elem = block.find("div", {"style": "-webkit-line-clamp:2"}) or \
                           block.find("span", class_="aCOpRe") or \
                           block.find("div", class_="VwiC3b") or \
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
    
    # We want up to 100 results, typically 10 results per page, so 10 pages
    results_needed = 100
    start_index = 0
    pages_checked = 0
    
    while len(all_results) < results_needed and pages_checked < 15:
        print(f"Fetching page starting at result {start_index}...")
        html, status_code = search_google_page(query, start=start_index)
        
        if status_code == 429:
            print("Google rate-limited us. Waiting 10 seconds before stopping/trying again...")
            time.sleep(10)
            break
            
        if not html:
            print("Failed to get HTML from Google. Stopping.")
            break
            
        page_results = parse_results(html, len(all_results))
        if not page_results:
            print("No search results found on this page. Stopping.")
            # For debug: save page
            with open(f"debug_page_{start_index}.html", "w", encoding="utf-8") as f:
                f.write(html)
            break
            
        print(f"Found {len(page_results)} results on this page.")
        all_results.extend(page_results)
        
        # Stop if we hit the target
        if len(all_results) >= results_needed:
            all_results = all_results[:results_needed]
            break
            
        start_index += 10
        pages_checked += 1
        
        # Politely sleep between requests to avoid rate limits
        print("Sleeping 2 seconds before the next page...")
        time.sleep(2)
        
    if not all_results:
        print("No results could be parsed.")
        return
        
    print(f"Successfully retrieved {len(all_results)} results in total!")
    
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
