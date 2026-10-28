🌱 FarmDtech — AI-Powered Crop Price Intelligence & Advisory System

Ask. Receive. Decide.

Project: FarmDtech
Team: PYCODE Team
Programme: ITF-NECA Technical Skills Development Project (TSDP)
Category: Agritech | Artificial Intelligence | Machine Learning | Automation
Status: Completed and Deployed Capstone MVP

⸻

📖 Project Overview

FarmDtech is an AI-powered agricultural intelligence platform developed to help Nigerian farmers, agricultural traders and stakeholders make informed decisions about crop prices and market opportunities.

The system combines machine-learning price forecasting, market comparisons, estimated transportation costs and conversational AI assistance to support agricultural decision-making.

FarmDtech focuses on three major staple crops:

* Maize
* Rice
* Beans

The platform is accessible through a web application, supported by a Python backend, cloud database and automation workflows.

🌐 Live Project Links

Component	Link
Product Demo	https://farm-dtech-web.vercel.app
GitHub Repository	https://github.com/ajeksmarvins/FarmDtech
Backend API Documentation	https://farmdtech.onrender.com/docs
Frontend Repository	https://github.com/ajeksmarvins/FarmDtech-Web

🎯 Problem Statement

Many Nigerian farmers experience difficulties accessing reliable agricultural market information.

These challenges include:

* Limited access to transparent crop-price information.
* Dependence on middlemen for market information.
* Difficulty comparing prices across markets.
* Uncertainty about future crop prices.
* Transportation costs that reduce potential profits.
* Limited access to accessible agricultural advisory services.

FarmDtech addresses these challenges through an integrated agricultural intelligence and decision-support platform.

🚀 Core Features

1. Crop Price Intelligence

FarmDtech provides historical crop-price information for maize, rice and beans across markets represented in its dataset.

The system distinguishes historical observations, estimated price series and model-generated forecasts.

2. Machine Learning Price Forecasting

FarmDtech integrates XGBoost machine-learning models to generate next-month crop-price forecasts.

The models use historical monthly prices, seasonal patterns and market characteristics.

The forecasting system provides market-level predictions to support agricultural planning.

Note: Forecasts are estimates, not guaranteed selling prices or verified live market quotations.

3. Market Comparison and Recommendations

The platform helps users evaluate potential selling markets using estimated crop prices, quantities, transportation distances and costs.

Market recommendations are based on indicative net proceeds.

Gross Revenue = Price per kg × Quantity
Estimated Transport Cost =
Distance × Transport Rate + Fixed Costs
Estimated Net Proceeds =
Gross Revenue − Estimated Transport Cost

Distance calculations use approximate geographic coordinates rather than live road-routing information.

4. AI-Powered Agricultural Chatbot

FarmDtech integrates Google Gemini AI to provide conversational agricultural assistance.

Users can ask questions about farming, crop-price forecasts and market-related topics.

The chatbot provides a natural-language interface to agricultural information and can explain available forecast results.

5. Multilingual Interface

The FarmDtech interface provides language options including:

* English
* Hausa
* Yoruba
* Igbo
* Nigerian Pidgin

Language selection is available in the chatbot interface. Response quality and translation accuracy may vary.

6. Automation and Reporting

FarmDtech uses n8n for workflow automation.

A multi-crop forecast email workflow has been configured and successfully tested using Gmail.

The report includes forecasts for maize, rice and beans and summarizes selected markets.

The workflow is designed for weekly reporting. Continuous scheduled execution requires an active n8n environment.

Automatic ingestion of newly published prices and model retraining are separate development improvements.

🏗️ Technology Stack

Component	Technology
Frontend	React, TypeScript, Vite, Tailwind CSS
Backend	Python, FastAPI
Machine Learning	XGBoost
AI Chatbot	Google Gemini
Database	Supabase / PostgreSQL
Automation	n8n
Frontend Deployment	Vercel
Backend Deployment	Render
Version Control	Git and GitHub

⚙️ System Architecture

                  FARMER / USER
                        |
                        v
             FARMDTECH WEB APPLICATION
             React + TypeScript + Vite
                        |
                        v
                  FASTAPI BACKEND
                        |
           +------------+-------------+
           |            |             |
           v            v             v
      Supabase       XGBoost       Gemini AI
      Database       Forecasts      Chatbot
           |
           v
      Data Services
      n8n Automation
           |
           v
      Gmail Forecast Reports

📊 Dataset and Model Evaluation

The core forecasting research uses the World Bank Real-Time Food Prices dataset for Nigeria.

Source: https://microdata.worldbank.org/catalog/4503

The processed dataset contains approximately 52,283 records across 67 physical market identifiers.

The historical research dataset contains both observed and estimated price series.

Forecast Evaluation

A chronological six-month holdout was used to evaluate the XGBoost models against a last-month-price baseline.

Crop	XGBoost WMAPE	Baseline WMAPE
Beans	7.51%	5.38%
Maize	6.18%	4.27%
Rice	5.14%	3.91%

The baseline performed better on the reported holdout. These results are based on historical estimated price series and do not independently establish accuracy against current market quotations.

📁 Repository Structure

FarmDtech/
├── automation/
├── data/
├── docs/
├── models/
├── scripts/
├── src/
├── supabase/
├── tests/
├── api.py
├── app.py
├── alerts.py
├── market_advisor.py
├── price_predictor.py
├── scraper.py
├── streamlit_app.py
├── requirements.txt
└── README.md

💻 Local Setup

Requirements

* Python 3.11 or 3.12
* Git
* Python package installer (pip)

Clone the repository:

git clone https://github.com/ajeksmarvins/FarmDtech.git
cd FarmDtech

Create a virtual environment:

python -m venv .venv

Activate the environment on Windows:

.venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Run the original Streamlit research application:

streamlit run app.py

The React frontend is maintained in the separate FarmDtech-Web repository.

🔐 Security

Sensitive credentials are managed through private environment variables and deployment configuration.

API keys, Supabase service-role credentials, OAuth secrets and other sensitive information must not be committed to public repositories.

Database access should follow appropriate authentication and authorization controls.

📈 Business Value

FarmDtech is designed to support:

* Improved access to agricultural price intelligence.
* Better-informed market selection.
* More transparent crop-price comparisons.
* Agricultural planning using forecast estimates.
* Increased accessibility of farming information through conversational AI.
* Reduced manual effort in preparing forecast reports.

These are potential benefits; measured financial savings or increases in farmer income have not yet been established.

🔮 Future Improvements

Potential future enhancements include:

* Automated ingestion of verified, newly published market-price observations.
* Weekly forecasting based on sufficiently frequent observed price data.
* Automated model retraining after validated dataset updates.
* Expanded market and crop coverage.
* Road-based transportation estimates.
* SMS and WhatsApp notifications.
* Improved multilingual response evaluation.
* Cloud-hosted continuous automation.

👥 Project Team — PYCODE

1. Joanna Onah
2. Destiny Yahmin
3. Marvelous Ajekuko
4. Habeebah Yusuf
5. Collins Chukwuka
6. Matthew Joel

Programme: ITF-NECA Technical Skills Development Project (TSDP)

📚 Data Attribution

World Bank — Real-Time Food Prices, Nigeria
https://microdata.worldbank.org/catalog/4503

FEWS NET — Historical market-price data research
https://fews.net

External data is subject to the relevant provider’s licensing and usage conditions.

⚠️ Disclaimer

FarmDtech is an educational agritech decision-support application.

Crop-price forecasts, transportation estimates and AI-generated responses are indicative and should not be treated as guaranteed market prices, confirmed buyer offers or financial outcomes.

⸻

🌱 FarmDtech — Ask. Receive. Decide.
