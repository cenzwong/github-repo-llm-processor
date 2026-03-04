# Repository Summarizer API

This is a FastAPI-based service that takes a GitHub repository URL and returns a human-readable summary of the project: what it does, what technologies are used, and how it's structured.

It leverages the Nebius Token Factory API (or OpenAI API) to generate the summary.

## Prerequisites

- Python 3.10+
- An API Key from Nebius Token Factory (or OpenAI).

## Step-by-Step Setup

1. **Clone the project / Extract the archive**
   ```bash
   # Navigate to the project directory
   cd repo-summarizer
   ```

2. **Create a virtual environment (optional but recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Environment Variables**
   Set your LLM provider API key. The application prioritizes `NEBIUS_API_KEY`. If it's not found, it falls back to `OPENAI_API_KEY`.

   ```bash
   export NEBIUS_API_KEY="your-nebius-api-key"
   # OR
   # export OPENAI_API_KEY="your-openai-api-key"
   ```

   *(Optional) If you plan to heavily test the API locally and encounter GitHub API rate limits, you can export a `GITHUB_TOKEN`.*

5. **Run the Application**
   Start the FastAPI server using Uvicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

6. **Test the Endpoint**
   The server exposes a `POST /summarize` endpoint. You can test it using `curl`:
   ```bash
   curl -X POST http://localhost:8000/summarize \
     -H "Content-Type: application/json" \
     -d '{"github_url": "https://github.com/psf/requests"}'
   ```

## Design Decisions

### LLM Model Choice

The application defaults to `meta-llama/Meta-Llama-3-8B-Instruct` when using the Nebius platform (or `gpt-3.5-turbo` as a fallback). These models were chosen because they are incredibly fast, cost-effective, and highly capable of structured JSON output generation, which is perfect for code summarization tasks where speed and strict output formatting are necessary.

### Handling Repository Contents (Context Management)

Sending an entire codebase to an LLM is both impossible (due to context window limits) and inefficient. My approach centers on **Information Density**:

1. **GitHub API Ingestion**: Instead of doing an expensive `git clone`, the app uses the GitHub API to fetch the repository tree.
2. **Noise Filtering**: We immediately exclude build artifacts (`dist`, `build`), environments (`venv`), and binary files (`.png`, `.pdf`, `.lock`).
3. **High-Priority Selection**: We concurrently fetch the raw content of up to 10 key files. We prioritize "Documentation" (`README.md`), "Dependency Configurations" (`package.json`, `requirements.txt`), and "Core Entry Points" (`main.py`, `app.py`). These files contain the highest density of information regarding the project's purpose and technology stack.
4. **Context Budgeting**: Instead of complex token counting, the app enforces strict character limits on the fetched files (e.g., 10,000 chars for a README, 5,000 for dependencies).
5. **ASCII Tree**: The remaining repository structure is converted into a simplified ASCII directory tree (max depth of 3) to provide the LLM with architectural context without token bloat.

This strategy guarantees that the prompt never exceeds standard 8k-16k context limits, runs incredibly fast via asynchronous I/O, and provides the LLM with exactly the right information to generate accurate summaries.
