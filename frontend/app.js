// Frontend Application
class FrontendAPP {
    constructor() {
        this.API_BASE_URL = 'http://localhost:8000/api';
        this.currentQuery = null;
        this.aggregateChart = null;
        this.queryChart = null;
        this.pollingInterval = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.showPage('page1');
    }

    // Event Handlers
    bindEvents() {
        // Page 1: Start Analysis
        document.getElementById('startAnalysisBtn').addEventListener('click', () => {
            this.startAnalysis();
        });

        // Page 1: Enter key on URL input
        document.getElementById('urlInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.startAnalysis();
            }
        });

        // Page 3: New Analysis
        document.getElementById('newAnalysisBtn').addEventListener('click', () => {
            this.resetAnalysis();
        });

        // Page 4: Back to Results
        document.getElementById('backToResultsBtn').addEventListener('click', () => {
            this.showPage('page3');
        });
    }

    // Page Management
    showPage(pageId) {
        // Hide all pages
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });
        
        // Show target page
        document.getElementById(pageId).classList.add('active');
    }

    // API Methods
    async makeRequest(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            if (data) {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(`${this.API_BASE_URL}${endpoint}`, options);
            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'API request failed');
            }

            return result;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // Page 1: Start Analysis
    async startAnalysis() {
        const urlInput = document.getElementById('urlInput');
        const queryCountInput = document.getElementById('queryCount');
        const startBtn = document.getElementById('startAnalysisBtn');
        const errorDiv = document.getElementById('errorMessage');

        // Clear previous errors
        errorDiv.classList.add('hidden');

        // Validate inputs
        const url = urlInput.value.trim();
        const queryCount = parseInt(queryCountInput.value);

        if (!url) {
            this.showError('Please enter a valid URL');
            return;
        }

        if (!queryCount || queryCount < 1 || queryCount > 50) {
            this.showError('Please enter a valid number of queries (1-50)');
            return;
        }

        // Disable button and show loading state
        startBtn.disabled = true;
        startBtn.textContent = 'Starting...';

        try {
            // Start analysis
            await this.makeRequest('/start-analysis', 'POST', {
                url: url,
                numOfQueries: queryCount
            });

            // Switch to loading page and start polling
            this.showPage('page2');
            this.startStatusPolling();

        } catch (error) {
            this.showError(error.message);
        } finally {
            // Re-enable button
            startBtn.disabled = false;
            startBtn.textContent = 'Start Analysis';
        }
    }

    // Page 2: Status Polling
    startStatusPolling() {
        let pollCount = 0;
        this.pollingInterval = setInterval(async () => {
            try {
                const status = await this.makeRequest('/status');
                this.updateLoadingStatus(status, pollCount);

                if (status.status === 'complete') {
                    clearInterval(this.pollingInterval);
                    this.loadAggregateResults();
                } else if (status.status === 'error') {
                    clearInterval(this.pollingInterval);
                    this.showError('Analysis failed. Please try again.');
                    this.showPage('page1');
                }

                pollCount++;
            } catch (error) {
                console.error('Status polling error:', error);
                // Continue polling unless it's been too long
                if (pollCount > 60) { // 5 minutes
                    clearInterval(this.pollingInterval);
                    this.showError('Analysis timed out. Please try again.');
                    this.showPage('page1');
                }
            }
        }, 5000); // Poll every 5 seconds
    }

    updateLoadingStatus(status, pollCount) {
        const statusText = document.getElementById('loadingStatus');
        const progressText = document.getElementById('progressText');

        switch (status.status) {
            case 'analyzing':
                statusText.textContent = `Analyzing ${status.url}...`;
                
                if (pollCount < 2) {
                    progressText.textContent = 'Generating search queries...';
                } else if (pollCount < 6) {
                    progressText.textContent = 'Running queries and collecting data...';
                } else {
                    progressText.textContent = 'Processing results...';
                }
                break;
            
            case 'complete':
                statusText.textContent = 'Analysis complete!';
                progressText.textContent = 'Loading results...';
                break;
                
            default:
                progressText.textContent = 'Preparing analysis...';
        }
    }

    // Page 3: Aggregate Results
    async loadAggregateResults() {
        try {
            const results = await this.makeRequest('/aggregate-results');
            this.displayAggregateResults(results);
            this.showPage('page3');
        } catch (error) {
            this.showError('Failed to load results: ' + error.message);
            this.showPage('page1');
        }
    }

    displayAggregateResults(results) {
        // Update URL display
        document.getElementById('analyzedUrl').textContent = results.url;

        // Display queries list
        this.displayQueriesList(results.queries);

        // Create aggregate chart
        this.createAggregateChart(results.domain_percentages);
    }

    displayQueriesList(queries) {
        const queriesList = document.getElementById('queriesList');
        queriesList.innerHTML = '';

        queries.forEach((query, index) => {
            const queryItem = document.createElement('div');
            queryItem.className = 'query-item';
            queryItem.innerHTML = `
                <div class="query-text">${query}</div>
            `;
            
            queryItem.addEventListener('click', () => {
                this.selectQuery(query, queryItem);
            });

            queriesList.appendChild(queryItem);
        });
    }

    createAggregateChart(domainPercentages) {
        const ctx = document.getElementById('aggregateChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.aggregateChart) {
            this.aggregateChart.destroy();
        }

        // Prepare data - show top 10 domains
        const topDomains = domainPercentages.slice(0, 10);
        const labels = topDomains.map(d => d.domain);
        const data = topDomains.map(d => d.percentage);

        this.aggregateChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Percentage of Queries',
                    data: data,
                    backgroundColor: 'rgba(15, 23, 42, 0.8)',
                    borderColor: 'rgba(15, 23, 42, 1)',
                    borderWidth: 1,
                    borderRadius: 6,
                    borderSkipped: false,
                }]
            },
            options: {
                indexAxis: 'y', // Horizontal bar chart
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: 'rgba(15, 23, 42, 1)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                const domain = topDomains[context.dataIndex];
                                return `${domain.percentage}% (${domain.query_count} queries)`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(226, 232, 240, 0.5)',
                            borderColor: 'rgba(226, 232, 240, 0.8)',
                        },
                        ticks: {
                            color: '#64748b',
                            font: {
                                family: 'Inter',
                                size: 11,
                                weight: '500'
                            },
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#0f172a',
                            font: {
                                family: 'Inter',
                                size: 11,
                                weight: '600'
                            }
                        }
                    }
                }
            }
        });
    }

    // Page 4: Query Details
    async selectQuery(query, queryElement) {
        // Update selected state
        document.querySelectorAll('.query-item').forEach(item => {
            item.classList.remove('selected');
        });
        queryElement.classList.add('selected');

        this.currentQuery = query;

        try {
            const queryDetails = await this.makeRequest('/query-details', 'POST', {
                query: query
            });
            
            this.displayQueryDetails(queryDetails);
            this.showPage('page4');
        } catch (error) {
            this.showError('Failed to load query details: ' + error.message);
        }
    }

    displayQueryDetails(details) {
        // Update query title
        document.getElementById('queryTitle').textContent = `Query: "${details.query}"`;

        // Display Gemini response
        document.getElementById('geminiResponse').innerHTML = this.formatGeminiResponse(details.gemini_response);

        // Create query-specific chart
        this.createQueryChart(details.domains);
    }

    formatGeminiResponse(response) {
        // Simple formatting - add line breaks and basic styling
        return response
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold text
            .replace(/\*(.*?)\*/g, '<em>$1</em>'); // Italic text
    }

    createQueryChart(domains) {
        const ctx = document.getElementById('queryChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (this.queryChart) {
            this.queryChart.destroy();
        }

        // Prepare data
        const labels = domains.map(d => d.domain);
        const data = domains.map(d => d.count);

        this.queryChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Mentions',
                    data: data,
                    backgroundColor: 'rgba(51, 65, 85, 0.8)',
                    borderColor: 'rgba(51, 65, 85, 1)',
                    borderWidth: 1,
                    borderRadius: 6,
                    borderSkipped: false,
                }]
            },
            options: {
                indexAxis: 'y', // Horizontal bar chart
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: 'white',
                        bodyColor: 'white',
                        borderColor: 'rgba(15, 23, 42, 1)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                const count = context.parsed.x;
                                return `${count} mention${count !== 1 ? 's' : ''}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(226, 232, 240, 0.5)',
                            borderColor: 'rgba(226, 232, 240, 0.8)',
                        },
                        ticks: {
                            color: '#64748b',
                            font: {
                                family: 'Inter',
                                size: 11,
                                weight: '500'
                            },
                            precision: 0
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#0f172a',
                            font: {
                                family: 'Inter',
                                size: 11,
                                weight: '600'
                            }
                        }
                    }
                }
            }
        });
    }

    // Utility Methods
    showError(message) {
        const errorDiv = document.getElementById('errorMessage');
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }

    async resetAnalysis() {
        // Clear any polling
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }

        // Reset form
        document.getElementById('urlInput').value = '';
        document.getElementById('queryCount').value = '8';
        document.getElementById('errorMessage').classList.add('hidden');

        // Reset to first page
        this.showPage('page1');

        // Optionally reset the backend
        try {
            await this.makeRequest('/reset', 'POST');
        } catch (error) {
            console.log('Reset request failed:', error);
            // Continue anyway - user can still start a new analysis
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new FrontendAPP();
});
