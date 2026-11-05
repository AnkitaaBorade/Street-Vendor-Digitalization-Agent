# Street Vendor Digitalization Agent

A RAG-powered AI assistant that helps local hawkers and micro-entrepreneurs in India become digitally visible and financially included. Built on IBM watsonx.ai (IBM Granite models) with a clean Python Flask backend.

---

## What It Does

- Generates structured **Digital Business Profiles** from a plain-language vendor description
- Provides step-by-step **UPI / QR code setup guides**
- Suggests **hyperlocal SEO strategies** and online listing platforms
- Evaluates eligibility across **four government credit schemes** (PM SVANidhi, Udyam Assist, MUDRA Shishu, PM Vishwakarma)
- Supports responses in **English, Hindi, and Marathi**
- Produces a **downloadable plain-text plan** for offline access
- Generates a **Digital Business Card** preview with QR placeholder
- Cites all **RAG source documents** (government portals, fintech APIs) inline

---

## Project Structure

```
STREET VENDOR/
├── app.py               # Flask server - routing and API endpoints
├── granite_client.py    # IBM Granite API client and RAG integration
├── vendor_agent.py      # Core agent logic - profile, schemes, export
├── config.py            # Environment configuration handler
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── index.html           # Frontend single-page application
└── README.md            # This file
```

---

## Prerequisites

- Python 3.11 or higher
- An active [IBM Cloud](https://cloud.ibm.com) account (Lite tier is sufficient)
- A [watsonx.ai](https://www.ibm.com/watsonx) project with the Granite model enabled

---

## Setup

### 1. Clone or download the project

```bash
cd "STREET VENDOR"
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your IBM Cloud credentials:

| Variable | Description |
|---|---|
| `IBM_API_KEY` | IBM Cloud IAM API key |
| `IBM_PROJECT_ID` | watsonx.ai Project ID |
| `IBM_WATSONX_URL` | Regional endpoint (default: `https://us-south.ml.cloud.ibm.com`) |
| `GRANITE_MODEL_ID` | Granite model to use (default: `ibm/granite-13b-instruct-v2`) |

### 5. Run the development server

```bash
python app.py
```

The application will be available at `http://localhost:5000`.

---

## API Reference

### `GET /api/health`
Liveness probe. Returns server status and missing config keys.

### `GET /api/config`
Returns non-sensitive runtime configuration for the frontend.

### `POST /api/generate-profile`
Runs the full vendor digitalization pipeline.

**Request body:**
```json
{
  "vendor_input": "I sell fruit in Pune's Camp area",
  "location": "Camp, Pune",
  "business_type": "Fruit Vendor",
  "language": "en"
}
```

**Response:** Generated AI text, scheme eligibility, business card, RAG sources, and export plan.

### `POST /api/scheme-eligibility`
Deep-dive government scheme analysis via Granite.

**Request body:**
```json
{
  "vendor_details": "Street fruit vendor, 5 years in business, no formal registration",
  "language": "hi"
}
```

### `GET /api/rag-sources`
Returns the full RAG source catalogue.

---

## Supported Languages

| Code | Language |
|---|---|
| `en` | English |
| `hi` | Hindi (हिंदी) |
| `mr` | Marathi (मराठी) |

---

## Government Schemes Covered

| Scheme | Amount | Portal |
|---|---|---|
| PM SVANidhi Micro-Loan | Rs 10,000 / 20,000 / 50,000 | pmsvanidhi.mohua.gov.in |
| Udyam Assist Platform | Free Registration | udyamassist.gov.in |
| MUDRA Shishu Loan | Up to Rs 50,000 | mudra.org.in |
| PM Vishwakarma Scheme | Rs 15,000 toolkit + Rs 1-2L credit | pmvishwakarma.gov.in |

---

## Production Deployment

For production, use Gunicorn behind a reverse proxy (e.g., Nginx):

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Set `FLASK_DEBUG=false` and use a strong `SECRET_KEY` in your production `.env`.

---

## Built With

- [IBM watsonx.ai](https://www.ibm.com/watsonx) - IBM Granite language models
- [Flask](https://flask.palletsprojects.com/) - Python web framework
- [Python Requests](https://requests.readthedocs.io/) - HTTP client for IBM IAM and Granite API
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable management
