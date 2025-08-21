# gemini.py 
Handles queries, parses the results and meta data in easier to work with format, and resolves Google's redirect url to actual urls
Can be used using process_query function
Results are saved to gemini_results.json

# domain_analyzer.py
The main domain analysis tool, use the analyze_queries function to get counts of each domain. also contains the full response of gemini.py module in case its needed for future purposes.
Results are saved to domain_analysis.json


# TO run:
1. pip install -r requirements.txt
2. playwright install 
3. Set up .env    
4. To Run end to end pipeline:
    a. set DEFAULT_URL in queryGenerator.py
    b. run queryGenerator.py
    c. Results are stored in domain_analysis_prompted.json

5. To get citations from a list of queries:
    a. set queries list in domain_analyzer.py
    b. run domain_analyzer.py


# TO-DO:
1. Run all queries first, only then resolve urls. currently urls are resolved after and for every query
2. Get proper prompt (Currently simple prompt)
3. Use gemini structed data config to get robust list of queries (Currently mannually verified to be in structure, little error handling present)
4. Multiple head requests to same site by same IP gets blocked by the site. ALso, there seems to be some SSL issues, need to user proper headers with a get request instead. Potentially use proxies.
