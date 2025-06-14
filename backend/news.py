import requests
from datetime import datetime
import json
import os
from openai import OpenAI
from typing import List, Optional
from pydantic import BaseModel, Field
from threading import Lock

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

# Pydantic Models
class Article(BaseModel):
    """Model for news article data"""
    title: str
    summary: str
    link: str
    published: str
    source: str

class Analysis(BaseModel):
    """Model for GPT analysis result"""
    severity: float = Field(..., ge=0, le=1, description="Severity rating from 0 to 1")
    explanation: str = Field(..., description="Brief explanation of the rating")

class ArticleResult(BaseModel):
    """Model for individual article analysis result"""
    title: str
    published: str
    source: str
    analysis: Analysis
    link: str

class DoomsdayAnalysis(BaseModel):
    """Model for the complete doomsday analysis response"""
    timestamp: str
    doomsday_probability: float = Field(..., ge=0, le=100, description="Doomsday probability percentage")
    analysis_basis: int = Field(..., ge=0, description="Number of articles analyzed")
    detailed_results: List[ArticleResult]
    interpretation: str

def fetch_fresh_headlines() -> List[Article]:
    """Fetch latest headlines from NewsAPI"""
    newsapi_key = os.getenv('NEWSAPI_KEY')
    if not newsapi_key:
        print("Warning: NEWSAPI_KEY environment variable not set")
        return []
    
    try:
        print("Fetching fresh headlines from NewsAPI...")
        
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'apiKey': newsapi_key,
            'language': 'en',
            'pageSize': 10,
            'country': 'us',
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'ok':
            raise Exception(f"NewsAPI error: {data.get('message', 'Unknown error')}")
        
        print(f"Found {data['totalResults']} articles")
        
        articles_list: List[Article] = []
        seen_urls = set()
        
        for article in data['articles']:
            url = article.get('url')
            title = article.get('title')
            description = article.get('description')
            
            if not url or not title or url in seen_urls:
                continue
            
            clean_article = Article(
                title=title,
                summary=description or '',
                link=url,
                published=article.get('publishedAt', ''),
                source=article.get('source', {}).get('name', 'Unknown')
            )
            
            articles_list.append(clean_article)
            seen_urls.add(url)
            
            if len(articles_list) >= 5:
                break
        
        return articles_list
        
    except Exception as e:
        print(f"Error fetching news: {str(e)}")
        return []

def analyze_with_gpt(text: str) -> Analysis:    
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
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI specialized in assessing global risks and threats to human civilization. Be objective and analytical in your assessment."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=150
        )
        
        # Parse the response and create Analysis model
        analysis_data = json.loads(response.choices[0].message.content)
        return Analysis(
            severity=analysis_data['severity'],
            explanation=analysis_data['explanation']
        )
    except Exception as e:
        print(f"Error in GPT analysis: {str(e)}")
        return Analysis(
            severity=0.0,
            explanation="Error in analysis"
        )

def interpret_probability(probability: float) -> str:
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

def fetch_news_data() -> DoomsdayAnalysis:
    """Fetch and analyze news articles for doomsday probability"""
    articles = fetch_fresh_headlines()
    
    if not articles:
        print("No articles found!")
        return DoomsdayAnalysis(
            timestamp=datetime.now().isoformat(),
            doomsday_probability=0.0,
            analysis_basis=0,
            detailed_results=[],
            interpretation="Unable to assess - no news articles found"
        )
    
    print(f"Analyzing {len(articles)} articles...")
    results: List[ArticleResult] = []
    total_severity = 0.0
    
    for i, article in enumerate(articles, 1):
        # Combine title and summary
        full_text = f"{article.title} {article.summary}".strip()
        
        # Skip empty articles
        if not full_text:
            continue
            
        print(f"Analyzing article {i}/{len(articles)}: {article.title[:50]}...")
        
        # Analyze with GPT
        analysis = analyze_with_gpt(full_text)
        
        # Add to results
        result = ArticleResult(
            title=article.title,
            published=article.published,
            source=article.source,
            analysis=analysis,
            link=article.link
        )
        results.append(result)
        total_severity += analysis.severity
        
        print(f"Severity: {analysis.severity}")
    
    # Calculate average severity and convert to doomsday probability
    avg_severity = total_severity / len(results) if results else 0.0
    doomsday_probability = round(avg_severity * 100, 2)
    
    return DoomsdayAnalysis(
        timestamp=datetime.now().isoformat(),
        doomsday_probability=doomsday_probability,
        analysis_basis=len(results),
        detailed_results=results,
        interpretation=interpret_probability(doomsday_probability)
    )

# Global variable to store news data
news_data: Optional[DoomsdayAnalysis] = None
lock = Lock()

def update_news_data():
    global news_data
    with lock:
        news_data = fetch_news_data()

def get_news_data() -> Optional[DoomsdayAnalysis]:
    """Get the current news data safely"""
    with lock:
        return news_data.copy() if news_data else None
