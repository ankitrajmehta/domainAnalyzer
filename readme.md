
# TO run:

## Prerequisites:
1. pip install -r requirements.txt
2. playwright install 
3. Set up .env file with required API keys

## Running the Web Application:
1. **Start the Backend API:**
   ```bash
   python app.py
   ```
   This will start the Flask API server on http://localhost:8000

2. **Start the Frontend Server:**
   ```bash
   python frontend_server.py
   ```
   This will serve the frontend on http://localhost:3000

3. **Access the Application:**
   - Open your browser and go to http://localhost:3000
   - The frontend will communicate with the backend API automatically

# TO-DO:
1. Run all queries first, only then resolve urls. currently urls are resolved after and for every query. Potentially remove the url resolver, as gemini returned 'title' should be enough.
2. Use gemini structured data functionality for crawler and structure analyzer as well (Currently only for query generation)
4. Multiple head requests to same site by same IP gets blocked by the site. ALso, there seems to be some SSL issues, need to user proper headers with a get request instead. Potentially use the title returned by gemini itself instead of manually decoding the redirect link, since its usually the same.
5. Improvement needed in structure analyzer, particularly checking for meta tags, descriptions, and FAQ sections. Currently the rule-based system is too strict. Also priority can be wrong sometimes currently.