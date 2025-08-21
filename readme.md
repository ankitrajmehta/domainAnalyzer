
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
1. Run all queries first, only then resolve urls. currently urls are resolved after and for every query
2. Get proper prompt (Currently simple prompt)
3. Use gemini structed data config to get robust list of queries (Currently mannually verified to be in structure, little error handling present)
4. Multiple head requests to same site by same IP gets blocked by the site. ALso, there seems to be some SSL issues, need to user proper headers with a get request instead. Potentially use