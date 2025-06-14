import requests
from datetime import datetime
import json
import os
from openai import OpenAI
import time
from pathlib import Path
import random

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')  # Make sure to set this environment variable
)

# Constants
CACHE_FILE = 'headlines_cache.json'
CACHE_DIR = Path('cache')

def load_cached_headlines():
    """Load cached headlines from JSON file"""
    cache_path = CACHE_DIR / CACHE_FILE
    if not cache_path.exists():
        return {}
    
    try:
        with open(cache_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading cache: {str(e)}")
        return {}

def save_headlines_to_cache(date_str, headlines):
    """Save headlines to JSON cache file"""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / CACHE_FILE
    
    # Load existing cache
    cache = load_cached_headlines()
    
    # Update cache with new headlines
    cache[date_str] = {
        'timestamp': datetime.now().isoformat(),
        'headlines': headlines
    }
    
    # Save updated cache
    try:
        with open(cache_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Error saving to cache: {str(e)}")

def fetch_fresh_headlines():
    """Fetch latest headlines from NewsAPI"""
    newsapi_key = os.getenv('NEWSAPI_KEY')
    if not newsapi_key:
        raise ValueError("NEWSAPI_KEY environment variable not set")
    
    try:
        print("Fetching fresh headlines from NewsAPI...")
        
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'apiKey': newsapi_key,
            'language': 'en',
            'pageSize': 100,  # Get maximum results in one request
            'country': 'us',  # Focus on US news
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'ok':
            raise Exception(f"NewsAPI error: {data.get('message', 'Unknown error')}")
        
        print(f"Found {data['totalResults']} articles")
        
        articles = []
        seen_urls = set()
        
        for article in data['articles']:
            url = article['url']
            
            if url in seen_urls:
                continue
            
            clean_article = {
                'title': article['title'],
                'summary': article['description'] or '',
                'link': url,
                'published': article['publishedAt'],
                'source': article['source']['name']
            }
            
            articles.append(clean_article)
            seen_urls.add(url)
            print(f"Processing article: {clean_article['title']}")
            
            if len(articles) >= 20:
                break
        
        return articles
        
    except Exception as e:
        print(f"Error fetching news: {str(e)}")
        return []

def get_news(target_date=None):
    """Fetch news articles, using cache if available"""
    # If no target date specified, use current date
    if target_date is None:
        target_date = datetime.now()
    
    # Convert date to string format for cache key
    date_str = target_date.strftime('%Y-%m-%d')
    
    # Load cached headlines
    cache = load_cached_headlines()
    
    # Check if we have cached headlines for this date
    if date_str in cache:
        cached_data = cache[date_str]
        cached_time = datetime.fromisoformat(cached_data['timestamp'])
        current_time = datetime.now()
        
        # Use cache if it's from the same day and not too old (less than 12 hours old)
        if (current_time - cached_time).total_seconds() < 43200:  # 12 hours in seconds
            print(f"Using cached headlines from {cached_time.isoformat()}")
            return cached_data['headlines']
    
    # If we reach here, we need fresh headlines
    articles = fetch_fresh_headlines()
    
    # Cache the fresh headlines
    if articles:
        save_headlines_to_cache(date_str, articles)
    
    return articles

def analyze_with_gpt(text):
    """Analyze the text using GPT-3.5 for doomsday probability"""
    
    prompt = f"""Analyze this news article and rate its severity in terms of potential threat to human civilization or global stability.

Article: {text}

Rate this on a scale from 0 to 1, where:
0 = Completely harmless, no impact on global stability
0.25 = Minor local concerns
0.5 = Regional issues that could escalate
0.75 = Serious global concerns
1.0 = Major threat to civilization

You may also rate it in between these values. For example, if the article is about a minor local issue that could escalate, you could rate it 0.35.

Provide your response in this exact JSON format:
{{
    "severity": 0.X,
    "explanation": "Brief explanation of why you gave this rating"
}}

Be extremely conservative with high ratings. A severity of 1.0 should only be used for truly apocalyptic scenarios."""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI specialized in assessing global risks and threats to human civilization. Be objective and analytical in your assessment."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=150
        )
        
        # Parse the response
        analysis = json.loads(response.choices[0].message.content)
        return {
            'severity': analysis['severity'],
            'explanation': analysis['explanation']
        }
    except Exception as e:
        print(f"Error in GPT analysis: {str(e)}")
        return {
            'severity': 0,
            'explanation': "Error in analysis"
        }

def calculate_doomsday_probability():
    """Calculate the overall doomsday probability based on news analysis"""
    print("Fetching news articles...")
    articles = get_news()
    
    if not articles:
        print("No articles found!")
        return {
            'timestamp': datetime.now().isoformat(),
            'doomsday_probability': 0,
            'analysis_basis': 0,
            'detailed_results': [],
            'interpretation': "Unable to assess - no news articles found"
        }
    
    print(f"\nAnalyzing {len(articles)} articles...")
    results = []
    total_severity = 0
    
    for i, article in enumerate(articles, 1):
        # Combine title and summary
        full_text = f"{article['title']} {article['summary']}"
        
        # Skip empty articles
        if not full_text.strip():
            continue
            
        print(f"\nAnalyzing article {i}/{len(articles)}: {article['title'][:100]}...")
        
        # Analyze with GPT
        analysis = analyze_with_gpt(full_text)
        
        # Add to results
        result = {
            'title': article['title'],
            'published': article['published'],
            'source': article.get('source', ''),
            'analysis': analysis,
            'link': article['link']
        }
        results.append(result)
        total_severity += analysis['severity']
        
        print(f"Severity: {analysis['severity']}")
    
    # Calculate average severity and convert to doomsday probability
    avg_severity = total_severity / len(results) if results else 0
    doomsday_probability = round(avg_severity * 100, 2)
    
    return {
        'timestamp': datetime.now().isoformat(),
        'doomsday_probability': doomsday_probability,
        'analysis_basis': len(results),
        'detailed_results': results,
        'interpretation': interpret_probability(doomsday_probability)
    }

def interpret_probability(probability):
    """Provide a human-readable interpretation of the doomsday probability"""
    if probability < 20:
        return "Business as usual - no significant global threats detected"
    elif probability < 40:
        return "Some concerning developments, but nothing civilization-threatening"
    elif probability < 60:
        return "Multiple serious global challenges present"
    elif probability < 80:
        return "High level of global instability - multiple severe threats active"
    else:
        return "EXTREME ALERT: Multiple potential civilization-threatening events detected"

if __name__ == "__main__":
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key with:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        exit(1)
    
    print("Starting doomsday analysis...")
    results = calculate_doomsday_probability()
    print("\nFinal Results:")
    print(json.dumps(results, indent=2)) 