# gemini.py 
Handles queries, parses the results and meta data in easier to work with format, and resolves Google's redirect url to actual urls
Can be used using process_query function
Results are saved to gemini_results.json

# domain_analyzer.py
The main domain analysis tool, use the analyze_queries function to get counts of each domain. also contains the full response of gemini.py module in case its needed for future purposes.
Results are saved to domain_analysis.json