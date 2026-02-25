cd "d:\Web Scraping"
.\venv\Scripts\Activate.ps1
python pipeline.py              # scrapes up to 50 posts (default)
python pipeline.py --max-posts 10   # or limit it