from django.shortcuts import render
import aiohttp
import asyncio
import logging

api_key = '3c157269727f5dcd8993d8af582c8ab0'
logging.basicConfig(level=logging.DEBUG)

async def fetch_json(session, url, retries=3, timeout=10):
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=timeout) as response:
                data = await response.json()
                logging.debug(f"Fetched data from {url}: {data}")
                return data
        except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                logging.error(f"Failed to fetch data from {url} after {retries} attempts: {e}")
                raise e

async def fetch_movie_details(movie, session):
    genre_names = []
    genre_url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={api_key}"
    genre_data = await fetch_json(session, genre_url)
    genres = genre_data.get('genres', [])
    
    for genre_id in movie.get('genre_ids', []):
        for genre in genres:
            if genre['id'] == genre_id:
                genre_names.append(genre['name'])
    
    genres = ', '.join(genre_names) if genre_names else 'Not available'
    
    movie_id = movie['id']
    details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=en-US"
    details_data = await fetch_json(session, details_url)
    
    credits = details_data.get('credits', {})
    actors = ", ".join([actor['name'] for actor in credits.get('cast', [])[:5]])  # Get first 5 actors
    writers = ", ".join([writer['name'] for writer in credits.get('crew', []) if writer['department'] == 'Writing'])
    
    movie_details = {
        'title': movie.get('title', 'Title not available'),
        'release_date': movie.get('release_date', 'Release date not available'),
        'overview': movie.get('overview', 'Overview not available'),
        'vote_average': movie.get('vote_average', 'Vote average not available'),
        'popularity': movie.get('popularity', 'Popularity not available'),
        'poster_path': movie.get('poster_path', 'Poster not available'),
        'backdrop_path': movie.get('backdrop_path', 'Backdrop not available'),
        'genres': genres,
        'actors': actors if actors else 'Actors not available',
        'writers': writers if writers else 'Writers not available',
        'budget': f"${details_data.get('budget', 0):,}" if details_data.get('budget') else "Budget: Not available",
        'revenue': f"${details_data.get('revenue', 0):,}" if details_data.get('revenue') else "Revenue: Not available",
        'original_language': details_data.get('original_language', 'Language not available'),
        'original_title': details_data.get('original_title', 'Original title not available'),
        'vote_count': details_data.get('vote_count', 'Vote count not available'),
        'adult': details_data.get('adult', 'Not available'),
    }
    
    return movie_details

async def fetch_moviess(movie_name, year):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}&year={year}"
    async with aiohttp.ClientSession() as session:
        data = await fetch_json(session, url)
        logging.debug(f"Fetched movies data: {data}")
        tasks = [fetch_movie_details(movie, session) for movie in data.get('results', [])]
        movies = await asyncio.gather(*tasks)
        return movies

def index(request):
    movies = []
    if request.method == "POST":
        movie_name = request.POST.get("movieName", "").strip()
        year = request.POST.get("Year", "").strip()
        
        if movie_name:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                movies = loop.run_until_complete(fetch_moviess(movie_name, year))
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
                logging.error(f"Error fetching movies: {e}")
                movies = []
    years = range(2040, 1979, -1)
    return render(request, 'index.html', {'movies': movies, 'years': years})
