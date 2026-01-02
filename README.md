# Portfolio Builder AI

An intelligent stock portfolio recommendation system that uses AI to create personalized investment portfolios. Users answer questions about their investment preferences, and the system generates tailored portfolio recommendations using Claude as the reasoning engine.

## Architecture

The application follows a three-tier architecture deployed on Google Cloud Platform:

**Frontend** - Angular 18 single-page application served from Firebase Hosting

**BFF (Backend for Frontend)** - NestJS application running on Cloud Run via Firebase Functions. Handles security validation, rate limiting, and request routing.

**Agent** - Python application running on Cloud Run via Firebase Functions. Integrates with Anthropic Claude API to generate portfolio recommendations using specialized data tools.

### Data Flow

1. User interacts with the Angular SPA in their browser
2. Requests pass through security validation (Firebase App Check with reCAPTCHA v3, application key)
3. BFF validates the request and forwards to the Agent
4. Agent uses Claude with tools to analyze user preferences, economic and market data
5. Portfolio recommendations are returned to the user

### Agent Tools

The AI agent has access to four specialized tools for gathering investment data:

| Tool               | Description                                 |
| ------------------ | ------------------------------------------- |
| Macroeconomic Data | Economic indicators by region and country   |
| Stock Universe     | Available stocks for portfolio construction |
| Stock Fundamentals | Financial metrics and company data          |
| Market Sentiments  | Market sentiment analysis                   |

Data sources include many data sources like Alpha Vantage for market data and FRED for economic indicators.

## Tech Stack

| Layer    | Technology                                |
| -------- | ----------------------------------------- |
| Frontend | Angular 18, Angular Material              |
| BFF      | NestJS, TypeScript, Firebase Functions v2 |
| Agent    | Python 3.13, Anthropic Claude API         |
| Database | Cloud Firestore                           |
| Hosting  | Firebase Hosting                          |
| Runtime  | Google Cloud Run (via Firebase Functions) |
| Security | Firebase App Check, reCAPTCHA v3          |
| CI/CD    | GitHub Actions                            |

## Project Structure

```
portfolio-builder-ai/
├── frontend/                # Angular 18 application
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/  # UI components
│   │   │   ├── services/    # API and business logic services
│   │   │   ├── guards/      # Route guards (rate limiting)
│   │   │   ├── interceptors/# HTTP interceptors (auth, error handling)
│   │   │   └── mocks/       # MSW mock handlers for development and initial testing
│   │   └── environments/    # Environment configurations
│   └── angular.json
│
├── functions/               # NestJS BFF
│   ├── src/
│   │   ├── modules/         # Feature modules (portfolio, rate-limit, config)
│   │   ├── common/          # Shared DTOs, middleware, types
│   │   ├── services/        # Agent service, Firestore service, mocks
│   │   └── config/          # Environment and Firebase configuration
│   └── package.json
│
├── agents/                  # Python Agent
│   ├── src/
│   │   ├── agent/           # Anthropic service, prompts, tools
│   │   ├── models/          # Data transfer objects
│   │   └── utils/           # Security utilities
│   ├── batch_jobs/          # Data loading scripts
│   ├── tests/               # Agent evaluations
│   └── requirements.txt
│
├── .github/
│   └── workflows/           # CI/CD pipelines
│       ├── deploy-frontend.yml
│       ├── deploy-bff.yml
│       └── deploy-agent.yml
│
└── firebase.json            # Firebase configuration
```

## Prerequisites

- Node.js 20+
- Python 3.13+
- Firebase CLI
- Google Cloud account with Firebase project

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/portfolio-builder-ai.git
cd portfolio-builder-ai

# Install frontend dependencies
cd frontend
npm install

# Install BFF dependencies
cd ../functions
npm install

# Install agent dependencies
cd ../agents
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

### Environment Variables

Create `.env` files in the respective directories based on the `.env.example` templates.

**Frontend** (`frontend/src/environments/environment.ts`):

- Firebase configuration
- API endpoints
- reCAPTCHA site key

**BFF** (`functions/.env`):

- Firebase service account
- Agent URL
- Application security key

**Agent** (`agents/.env`):

- Anthropic API key
- Alpha Vantage API key
- FRED API key
- Agent authentication key

## Development

### Running Locally

```bash
# Terminal 1: Frontend (http://localhost:4200)
cd frontend
npm start

# Terminal 2: BFF with Firebase Emulators (http://localhost:5001)
cd functions
npm run start:dev

# Terminal 3: Agent
cd agents
source venv/bin/activate
python main.py
```

### Development Commands

**Frontend:**

```bash
npm start          # Start development server
npm run build      # Production build
npm test           # Run unit tests
npm run lint       # Lint code
```

**BFF:**

```bash
npm run start:dev  # Start with hot reload
npm run build      # Build for production
npm test           # Run unit tests
npm run lint       # Lint and fix code
```

**Agent:**

```bash
python main.py                    # Start agent server
python -m pytest tests/           # Run evaluations
```

### Using Mocks

The frontend includes MSW (Mock Service Worker) handlers for development without backend dependencies. Mock data is located in `frontend/src/app/mocks/`.

The BFF includes a mock agent service that can be enabled via environment configuration for testing without the Python agent.

## Testing

### Frontend

Unit tests using Jest and Angular testing utilities.

### BFF

Unit and e2e tests using Jest and Supertest.

### Agent

Evaluation tests for validating agent behavior and tool usage:

- `Test_Complete_Agent.py` - End-to-end agent evaluation
- `Test_Firestore_Tools.py` - Tool integration tests
- `test_macro_data_all_countries.py` - Macroeconomic data tool tests

## Deployment

The project uses GitHub Actions for continuous deployment. Three separate workflows handle deployment of each component:

- **deploy-frontend.yml** - Deploys Angular app to Firebase Hosting
- **deploy-bff.yml** - Deploys NestJS BFF to Firebase Functions
- **deploy-agent.yml** - Deploys Python agent to Firebase Functions

Deployments are triggered by:

- Push to `main` branch (path-specific)
- Manual workflow dispatch

### Required GitHub Secrets

| Secret                       | Description                            |
| ---------------------------- | -------------------------------------- |
| FIREBASE_API_KEY             | Firebase project API key               |
| FIREBASE_AUTH_DOMAIN         | Firebase auth domain                   |
| FIREBASE_PROJECT_ID          | Firebase project ID                    |
| FIREBASE_STORAGE_BUCKET      | Firebase storage bucket                |
| FIREBASE_MESSAGING_SENDER_ID | Firebase messaging sender ID           |
| FIREBASE_APP_ID              | Firebase app ID                        |
| FIREBASE_SERVICE_ACCOUNT     | Service account JSON for deployment    |
| RECAPTCHA_SITE_KEY           | reCAPTCHA v3 site key                  |
| FRONTEND_APP_KEY             | Application key for API authentication |
| ANTHROPIC_API_KEY            | Anthropic API key for Claude           |
| ALPHA_VANTAGE_API_KEY        | Alpha Vantage API key                  |
| FRED_API_KEY                 | FRED API key                           |

## Security

The application implements multiple security layers:

- **Firebase App Check** with reCAPTCHA v3 for bot protection
- **Application Key** validation between frontend and BFF
- **HTTPS** for all communications
- **Firestore Security Rules** for database access control

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
