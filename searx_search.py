import urllib.parse
import json
import csv
import time
import requests
from bs4 import BeautifulSoup

# A list of some active public SearXNG instances that often support JSON output
SEARX_INSTANCES = [
    "https://searx.be",
    "https://searx.space",
    "https://searx.mx",
    "https://searx.work",
    "https://searx.xyz",
    "https://priv.au",
    "https://baresearch.org",
    "https://search.ononoki.org",
    "https://search.sapti.me",
    "https://searxng.ch",
    "https://searx.ch"
]

def search_searxng(instance_url, query, page=1):
    # SearXNG uses 'pageno' for pagination (1, 2, 3...)
    url = f"{instance_url}/search"
    params = {
        "q": query,
        "format": "json",
        "pageno": page
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("results", [])
        else:
            print(f"Instance {instance_url} returned status code {response.status_code}")
            return None
    except Exception as e:
        # Silently fail for individual instances since we try multiple
        return None

def main():
    query = "Marcelo Baptista de Oliveira"
    all_results = []
    seen_urls = set()
    
    print(f"Searching for '{query}' using public SearXNG instances...")
    
    # We will try the instances one by one until we get the results we need (100 results)
    instance_index = 0
    page = 1
    max_pages = 10  # 10 pages * 10 results = 100 results
    
    # Let's dynamically fetch more instances from searx.space if needed
    try:
        res = requests.get("https://searx.space/data/instances.json", timeout=10)
        if res.status_code == 200:
            instances_data = res.json()
            fetched_instances = []
            for name, details in instances_data.get("instances", {}).items():
                # Check if JSON format is supported and HTTPS is true
                if details.get("html", {}).get("grade") == "A" or details.get("json", False):
                    # Clean up URL format
                    url = name if name.startswith("http") else f"https://{name}"
                    fetched_instances.append(url)
            if fetched_instances:
                # Put them at the front of the list
                global SEARX_INSTANCES
                SEARX_INSTANCES = list(dict.fromkeys(fetched_instances + SEARX_INSTANCES))
                print(f"Loaded {len(fetched_instances)} public instances from searx.space")
    except Exception as e:
        print("Could not load instances from searx.space, using fallback list.")
        
    results_needed = 100
    
    # We query page-by-page. If one instance fails or blocks, we switch to another instance
    current_instance = SEARX_INSTANCES[0]
    instance_ptr = 0
    
    while len(all_results) < results_needed and page <= max_pages:
        print(f"Requesting page {page} from {current_instance}...")
        results = search_searxng(current_instance, query, page)
        
        if results is None or len(results) == 0:
            print(f"Failed or empty results from {current_instance}. Switching instance...")
            instance_ptr += 1
            if instance_ptr >= len(SEARX_INSTANCES):
                print("All instances exhausted.")
                break
            current_instance = SEARX_INSTANCES[instance_ptr]
            time.sleep(1) # short wait before retry
            continue
            
        print(f"Retrieved {len(results)} results from page {page}")
        
        # Process and de-duplicate results
        for r in results:
            url = r.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append({
                    "rank": len(all_results) + 1,
                    "title": r.get("title", ""),
                    "url": url,
                    "snippet": r.get("content", "")
                })
                
        page += 1
        time.sleep(1.5)  # polite delay between page requests
        
    if not all_results:
        print("No results could be retrieved from any SearXNG instance.")
        return
        
    # Trim to exactly 100 results if we have more
    all_results = all_results[:results_needed]
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
