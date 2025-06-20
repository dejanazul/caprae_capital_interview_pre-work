# Company Intelligence Platform

A Streamlit-based platform for collecting, exploring, and analyzing company data from Yellow Pages, enriched with website content extraction and AI-powered chat assistant.

## Features

- Scrape company listings from Yellow Pages Indonesia
- Extract detailed company info and website content using NeuScraper
- Save and manage datasets
- Explore company data interactively
- Chat with a Google Gemini-powered AI assistant about any company

## Setup Instructions

### 1. Clone the Repository

```sh
git clone https://github.com/dejanazul/caprae_capital_interview_pre-work
cd https://github.com/dejanazul/caprae_capital_interview_pre-work
```

### 2. Install Python Dependencies
It is recommended to use a virtual environment:
```sh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a .env file in the root directory and add your Google Gemini API key:
```sh
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Start the NeuScraper Service

1️⃣ **Open the deployment directory**
```sh
cd NeuScraper/app
```

2️⃣ **Fill in the model path in app**
```bash
args.model_path = "/path/to/your/model"
```
3️⃣ **Deploy NeuScraper**
```sh
uvicorn app:app --reload --host 0.0.0.0 --port 1688
```

### 5. Run the Streamlit App
In a new terminal, from the project root:
```sh
streamlit run app.py
```
