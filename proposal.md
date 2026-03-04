AI Performance Engineering: Repository Summarizer API

1. System Architecture Overview

The system is divided into four logical layers. FastAPI is selected as the web framework to fully leverage asynchronous I/O, which is critical for optimizing the network-bound operations involved in querying the GitHub API and the LLM provider.

API Layer (FastAPI): Handles HTTP request routing, input/output validation via Pydantic schemas, and global error handling.

Ingestion Layer: Interfaces with GitHub to retrieve the repository structure and fetch specific file contents.

Context Management Layer: Executes filtering, prioritization, and strict character/token budgeting to maximize information density.

LLM Integration Layer: Constructs the prompt, communicates with the Nebius Token Factory (or alternative providers like OpenAI/Anthropic) using native JSON mode, and parses the structured output.

2. Component Design & Mechanics

2.1 Ingestion Layer: Fetching Strategy (KISS Optimized)

Mechanism: Avoid using git clone. For a lightweight API service, disk I/O and network bandwidth costs are prohibitively high. We will use a hybrid HTTP fetching approach to bypass aggressive rate limits.

Step 1: Resolve Default Branch: Fetch GET https://api.github.com/repos/{owner}/{repo} to dynamically determine the default_branch (e.g., main or master).

Step 2: Fetch Tree: Fetch GET https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1. This returns all file paths instantly, allowing us to build the project structure mapping.

Step 3: Fetch Raw Contents: Utilize an asynchronous HTTP client (httpx) to fetch the filtered files via GET https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{file_path}.

Why? Accessing raw.githubusercontent.com does not count towards the standard GitHub API rate limit, vastly improving the reliability of the application without requiring a GITHUB_TOKEN.

2.2 Context Management Layer: Filtering & Prioritization (The Core Challenge)

Mechanism: LLM context windows are strictly limited. We cannot blindly dump all files into the prompt. A strict "Information Density" strategy is mandatory.

Tier 1: Mandatory Exclusion (Noise)
These files are ignored entirely based on regex/extension matching:

Binary files (images, compiled binaries, PDFs, .lock files).

Dependencies and Build artifacts (node_modules/, venv/, dist/, __pycache__/).

Tier 2: High Priority Extraction (High Information Density)

Project Structure: Transform the raw GitHub API file paths into a simplified ASCII directory tree string. Maximum depth of 3 or 4 to avoid token explosion.

Documentation: README.md, CONTRIBUTING.md. Usually contains the exact "summary".

Dependency Definitions: pyproject.toml, requirements.txt, package.json, go.mod, docker-compose.yml. These files map directly to the "technologies" requirement.

Core Entry Points: main.py, app.py, src/index.js.

Token Budgeting Strategy (Simplified):

Instead of complex token counting logic, we enforce strict character limits per file category before concatenation.

e.g., Allow max 10,000 characters for the README, 5,000 for dependencies, and 5,000 for the directory tree. Truncate any file that exceeds its allocation. This guarantees we stay well within standard 8k-16k context limits with zero computational overhead.

2.3 LLM Integration Layer: Prompt Engineering

Mechanism:
Utilize System Prompts combined with the LLM provider's native JSON mode (response_format={"type": "json_object"}) to guarantee parsable output.

Prompt Structure:

You are a senior software architect analyzing a GitHub repository.
Based on the provided repository tree, documentation, and configuration files, extract the following:
1. "summary": A human-readable description of what the project does.
2. "technologies": A list of main technologies, languages, and frameworks.
3. "structure": A brief description of the project structure.

Output strictly as JSON matching this schema:
{"summary": "...", "technologies": ["..."], "structure": "..."}

--- REPOSITORY TREE ---
{tree_string}

--- KEY FILES ---
{file_contents}


3. Scalability & Performance Implications

Concurrency: Leverage asyncio.gather to parallelize the raw.githubusercontent.com file fetching. Fetching 5 key files concurrently reduces I/O latency to the time it takes to download the single largest file.

Error Handling & Resilience:

Handle GitHub 404s (Private/Invalid repo) -> Fast-fail and return HTTP 400 Bad Request.

Implement basic try/except blocks around the LLM API call to catch timeouts or 50x errors and return a clean {"status": "error", "message": "..."} response as required by the assignment.

4. Next Steps for Implementation

Initialize dependencies (fastapi, uvicorn, httpx, pydantic, openai).

Implement the GitHub HTTP fetching logic (Branch -> Tree -> Raw Contents).

Implement the string filtering and truncation logic.

Wire up the FastAPI POST /summarize endpoint and test with the psf/requests repository.