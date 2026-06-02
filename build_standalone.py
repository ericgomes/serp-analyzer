import os
import json

def build():
    print("Bundling all files into a standalone HTML dashboard...")
    
    # Read HTML structure
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
        
    # Read CSS styles
    with open("style.css", "r", encoding="utf-8") as f:
        css = f.read()
        
    # Read JS app logic
    with open("app.js", "r", encoding="utf-8") as f:
        js = f.read()
        
    # Read search data and analysis results
    with open("results.json", "r", encoding="utf-8") as f:
        results = f.read()
        
    with open("analysis_results.json", "r", encoding="utf-8") as f:
        analysis_results = f.read()
        
    with open("consolidated_report.md", "r", encoding="utf-8") as f:
        consolidated_report = f.read()
        
    # Extract timestamp from consolidated report markdown
    import re
    timestamp_match = re.search(r"Análise consolidada gerada em:\s*([^\*\n\r]+)", consolidated_report)
    if timestamp_match:
        consolidated_report_time = timestamp_match.group(1).strip()
    else:
        import datetime
        try:
            mtime = os.path.getmtime("analysis_results.json")
            consolidated_report_time = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        except:
            consolidated_report_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    # Embed data directly by replacing script tag loads
    data_js_inline = f"const searchResults = {results};\n"
    analysis_js_inline = f"const analysisResults = {analysis_results};\nconst consolidatedReport = {json.dumps(consolidated_report, ensure_ascii=False)};\nconst consolidatedReportTime = '{consolidated_report_time}';\nwindow.analysisDataLoaded = true;\n"
    
    # Replace stylesheets and external script tags in the HTML
    html = html.replace('<link rel="stylesheet" href="style.css">', f'<style>\n{css}\n</style>')
    
    script_data_tag = '<script src="data.js"></script>'
    script_analysis_tag = '<script src="analysis_data.js" onerror="window.analysisDataLoaded = false;" onload="window.analysisDataLoaded = true;"></script>'
    script_app_tag = '<script src="app.js"></script>'
    
    html = html.replace(script_data_tag, "")
    html = html.replace(script_analysis_tag, "")
    
    # Place inline scripts at the bottom
    combined_scripts = f"""
    <script>
    // Inline data
    {data_js_inline}
    {analysis_js_inline}
    
    // Inline app logic
    {js}
    </script>
    """
    
    html = html.replace(script_app_tag, combined_scripts)
    
    # Save the standalone compartivel HTML
    output_path = "dashboard_compartilhavel.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    print(f"Success! Generated single self-contained dashboard at: '{output_path}'")

if __name__ == "__main__":
    build()
