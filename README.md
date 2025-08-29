# Portfolio Builder AI

An intelligent multi-agent system that creates personalized stock portfolios using collaborative AI agents.

## Architecture

- **Frontend**: Angular 18+ with Material Design
- **Backend**: Firebase Functions + Firestore
- **AI Agents**: Multi-language (Python + Java) with LangChain orchestration
- **APIs**: Alpha Vantage (market data), Claude API (LLM)
- **Deployment**: Firebase Hosting (Free Tier)

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- Java 17+
- Firebase CLI
- Ollama (for local development)

### Installation
```bash
# Clone and setup
git clone <your-repo>
cd portfolio-builder-ai

# Install all dependencies
npm run install:all

# Start development servers
npm run dev
```

### Development URLs
- Frontend: http://localhost:4200
- Python Agents: http://localhost:8001
- Java Agent: http://localhost:8002
- Firebase Functions: http://localhost:5001

## Agents

| Agent | Language | Purpose |
|-------|----------|---------|
| Coordinator | Python | Orchestrates multi-agent workflows |
| Risk Assessment | Python | Analyzes user risk profile |
| Market Research | Java | Fetches and processes market data |
| News Analysis | Python | Sentiment analysis of financial news |
| Portfolio Optimizer | Python | Creates optimized asset allocation |

## Features

- **Freemium Model**: 2 free interactions per user
- **Multi-Agent Collaboration**: Specialized agents for different tasks
- **Real-time Data**: Alpha Vantage integration
- **Personalized Risk Assessment**: Custom questionnaire
- **Portfolio Optimization**: Modern portfolio theory algorithms
- **Responsive UI**: Angular Material design

## Development

```bash
# Individual component development
npm run dev:frontend    # Angular dev server
npm run dev:functions   # Firebase functions
npm run dev:agents      # Python agents

# Testing
npm test               # Run all tests
npm run test:frontend  # Angular tests
npm run test:agents    # Python tests

# Building
npm run build          # Build all components
npm run deploy:staging # Deploy to staging
```

## Progress Tracking

- [x] Project structure and configuration
- [ ] Coordinator agent (Python/LangChain)
- [ ] Risk assessment agent (Python)
- [ ] Market research agent (Java)
- [ ] News analysis agent (Python) 
- [ ] Portfolio optimizer agent (Python)
- [ ] Angular frontend
- [ ] Firebase integration
- [ ] Multi-agent orchestration
- [ ] Testing and deployment

## Contributing

This explores multi-agent AI agent development. Feel free to explore the code and provide feedback!

## License

MIT License - see LICENSE file for details.