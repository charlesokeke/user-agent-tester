from flask import Flask, render_template, request, jsonify
import requests
from concurrent.futures import ThreadPoolExecutor
import time
import json
from urllib.parse import urlparse, parse_qsl

app = Flask(__name__)

# List of diverse user agents focusing on scripts and tools
USER_AGENTS = [
    # PowerShell
    "Powershell",
    "Python",
    "Microsoft",
    "Mozilla/5.0 (Windows NT 10.0; Microsoft Windows 10.0.22621; en-US) PowerShell/7.3.1",
    "Mozilla/5.0 (Windows NT; Windows NT 10.0; en-US) WindowsPowerShell/5.1.22621.1778",
    
    # Python
    "python-requests/2.31.0",
    "Python-urllib/3.10",
    "Python/3.9 aiohttp/3.8.3",
    "pyspider/0.3.10 (+https://github.com/binux/pyspider)",
    
    # Curl
    "curl/7.83.1",
    "curl/8.1.0",
    "curl/7.85.0-DEV",
    
    # JavaScript/Node.js
    "node-fetch/1.0 (+https://github.com/bitinn/node-fetch)",
    "axios/1.3.4",
    "Mozilla/5.0 (compatible; Node.js)",
    
    # Other tools
    "Wget/1.21.3",
    "Wget/1.21.4 (linux-gnu)",
    "Apache-HttpClient/4.5.13 (Java/11.0.15)",
    "Go-http-client/1.1",
    "Ruby/3.1.3",
    "insomnia/8.2.0",
    "PostmanRuntime/7.32.2",
    "Scrapy/2.8.0 (+https://scrapy.org)",
    "HTTPie/3.2.1",
    # VBScript/Windows Scripting
    "MSXML2.ServerXMLHTTP.6.0",
    "Mozilla/4.0 (compatible; Win32; MSXML 6.0)",
    "MSXML2.XMLHTTP.3.0",
    # Batch/.NET Scripting
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; .NET CLR 2.0.50727)",
    "Mozilla/4.0 (compatible; Win32; .NET CLR 3.5.30729)",
    "DotNetScraper/1.0",
    # Common HTTP Clients
    "curl/7.77.0",
    "Wget/1.21.1",
    "Go-http-client/1.1",
    
    # Browser User Agents (common examples)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"

]

def parse_url_parameters(url):
    """Parse and return URL parameters as a dictionary"""
    parsed_url = urlparse(url)
    query_params = dict(parse_qsl(parsed_url.query))
    
    url_info = {
        "scheme": parsed_url.scheme,
        "netloc": parsed_url.netloc,
        "path": parsed_url.path,
        "params": parsed_url.params,
        "query": parsed_url.query,
        "fragment": parsed_url.fragment,
        "query_params": query_params
    }
    
    return url_info

def make_request(url, user_agent):
    """Make a request with the given user agent and return the result."""
    headers = {"User-Agent": user_agent}
    try:
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        end_time = time.time()
        
        # Parse URL info including parameters
        url_info = parse_url_parameters(url)
        final_url_info = parse_url_parameters(response.url)
        
        # Capture all response attributes
        result = {
            "success": response.status_code >= 200 and response.status_code < 300,
            "user_agent": user_agent,
            "status_code": response.status_code,
            "reason": response.reason,
            "content": response.text,
            "headers": dict(response.headers),
            "cookies": {k: v for k, v in response.cookies.items()},
            "elapsed": str(response.elapsed),
            "time_taken": round(end_time - start_time, 2),
            "url": response.url,
            "history": [{"url": r.url, "status_code": r.status_code} for r in response.history],
            "encoding": response.encoding,
            "apparent_encoding": response.apparent_encoding,
            "content_type": response.headers.get("Content-Type"),
            "content_length": len(response.content),
            "is_redirect": response.is_redirect,
            "is_permanent_redirect": response.is_permanent_redirect,
            "original_url": url,
            "original_url_info": url_info,
            "final_url_info": final_url_info,
        }
        
        # Add if there was a redirect
        if response.history:
            result["redirected"] = True
            result["redirect_count"] = len(response.history)
        else:
            result["redirected"] = False
            
        return result
    except Exception as e:
        return {
            "success": False,
            "user_agent": user_agent,
            "error": str(e),
            "original_url": url,
            "original_url_info": parse_url_parameters(url)
        }

@app.route('/')
def index():
    return render_template('index.html', user_agents=USER_AGENTS)

@app.route('/fetch', methods=['POST'])
def fetch():
    url = request.form.get('url')
    selected_agents = request.form.getlist('agents')
    
    # Use all agents if none selected
    agents_to_use = selected_agents if selected_agents else USER_AGENTS
    
    results = []
    successful_result = None
    
    # Use ThreadPoolExecutor for concurrent requests
    with ThreadPoolExecutor(max_workers=min(10, len(agents_to_use))) as executor:
        future_to_agent = {executor.submit(make_request, url, agent): agent for agent in agents_to_use}
        for future in future_to_agent:
            result = future.result()
            results.append(result)
            # Store the first successful result
            if result.get("success") and not successful_result:
                successful_result = result

            if successful_result:
                return render_template(
                        'results.html', 
                        results=results, 
                        successful_result=successful_result, 
                        url=urlparse(url).netloc
                    )
                
    return render_template('no_results.html',results=results)
    

if __name__ == '__main__':
    app.run(debug=True)