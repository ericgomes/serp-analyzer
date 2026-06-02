from googlesearch import search
import json
import csv

def main():
    query = "Marcelo Baptista de Oliveira"
    print(f"Searching for: '{query}' using googlesearch-python...")
    
    results = []
    try:
        # search() returns a generator. advanced=True yields objects with title, url, description attributes
        search_generator = search(query, num_results=100, lang="pt", advanced=True)
        
        for idx, result in enumerate(search_generator, start=1):
            results.append({
                "rank": idx,
                "title": result.title,
                "url": result.url,
                "snippet": result.description
            })
            print(f"Result {idx}: {result.title} -> {result.url}")
            
    except Exception as e:
        print(f"An error occurred during search: {e}")
        
    print(f"\nFound {len(results)} results.")
    
    if results:
        # Save files
        with open("results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print("Saved results to results.json")
            
        with open("results.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["rank", "title", "url", "snippet"])
            writer.writeheader()
            writer.writerows(results)
        print("Saved results to results.csv")

if __name__ == "__main__":
    main()
