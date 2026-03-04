import os
import re
import asyncio
import httpx
from typing import List, Dict, Tuple, Optional

# Constants for filtering
EXCLUDED_DIRS = {
    "node_modules", "venv", ".venv", "env", ".env", "dist", "build", "out",
    "__pycache__", ".git", ".github", ".vscode", ".idea", "vendor", "target", "bin", "obj"
}

EXCLUDED_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".class", ".jar",
    ".mp3", ".mp4", ".wav", ".avi", ".mkv", ".mov",
    ".lock", ".pyc", ".pyo", ".pyd", ".log"
}

HIGH_PRIORITY_FILES = {
    "readme.md", "readme.rst", "readme.txt", "readme",
    "package.json", "requirements.txt", "pyproject.toml",
    "pom.xml", "build.gradle", "go.mod", "cargo.toml",
    "docker-compose.yml", "dockerfile", "makefile",
    "main.py", "app.py", "index.js", "server.js", "main.go", "main.rs"
}


class GitHubClient:
    def __init__(self):
        self.github_api_base = "https://api.github.com"
        self.raw_content_base = "https://raw.githubusercontent.com"

        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Repo-Summarizer-API"
        }

        token = os.getenv("GITHUB_TOKEN")
        if token:
            self.headers["Authorization"] = f"token {token}"

    def parse_github_url(self, url: str) -> Tuple[str, str]:
        """Parses a GitHub URL and returns the owner and repo."""
        # Remove trailing slash
        url = url.rstrip("/")
        # Extract owner and repo from URL
        match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
        if not match:
            raise ValueError("Invalid GitHub URL format. Expected: https://github.com/owner/repo")
        return match.group(1), match.group(2)

    async def get_repo_info(self, client: httpx.AsyncClient, owner: str, repo: str) -> dict:
        """Fetches repository info to get the default branch."""
        url = f"{self.github_api_base}/repos/{owner}/{repo}"
        response = await client.get(url, headers=self.headers)
        if response.status_code == 404:
            raise ValueError(f"Repository {owner}/{repo} not found or is private.")
        response.raise_for_status()
        return response.json()

    async def get_repo_tree(self, client: httpx.AsyncClient, owner: str, repo: str, branch: str) -> List[dict]:
        """Fetches the full git tree of the repository recursively."""
        url = f"{self.github_api_base}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        response = await client.get(url, headers=self.headers)
        response.raise_for_status()

        data = response.json()
        if data.get("truncated"):
            # Tree is too large, GitHub truncated it. We will work with what we have.
            pass

        return data.get("tree", [])

    def filter_tree(self, tree: List[dict]) -> List[dict]:
        """Filters out noise from the tree."""
        filtered_tree = []
        for item in tree:
            path = item.get("path", "")

            # Check for excluded directories in the path
            path_parts = path.split("/")
            if any(part in EXCLUDED_DIRS or part.startswith(".") for part in path_parts):
                continue

            # For files, check extensions
            if item.get("type") == "blob":
                _, ext = os.path.splitext(path)
                if ext.lower() in EXCLUDED_EXTS:
                    continue

            filtered_tree.append(item)

        return filtered_tree

    def select_high_priority_files(self, tree: List[dict], limit: int = 10) -> List[str]:
        """Selects the most relevant files to fetch content for."""
        files = []

        # Add files based on priority matching
        for item in tree:
            if item.get("type") == "blob":
                path = item.get("path", "")
                filename = os.path.basename(path).lower()

                if filename in HIGH_PRIORITY_FILES:
                    files.append(path)

        # If we have space, add some other interesting files (like root level source files)
        if len(files) < limit:
            for item in tree:
                if item.get("type") == "blob" and "/" not in item.get("path", ""):
                    path = item.get("path", "")
                    if path not in files and not os.path.basename(path).startswith("."):
                        files.append(path)
                        if len(files) >= limit:
                            break

        return files[:limit]

    async def fetch_file_content(self, client: httpx.AsyncClient, owner: str, repo: str, branch: str, file_path: str) -> Tuple[str, Optional[str]]:
        """Fetches the raw content of a specific file."""
        url = f"{self.raw_content_base}/{owner}/{repo}/{branch}/{file_path}"
        try:
            response = await client.get(url)
            response.raise_for_status()
            return file_path, response.text
        except httpx.HTTPStatusError as e:
            return file_path, f"<Error fetching file: {e.response.status_code}>"
        except Exception as e:
            return file_path, f"<Error fetching file: {str(e)}>"

    async def fetch_repo_context(self, github_url: str) -> Tuple[List[dict], Dict[str, str]]:
        """Orchestrates fetching the repo tree and key file contents."""
        owner, repo = self.parse_github_url(github_url)

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Get default branch
            repo_info = await self.get_repo_info(client, owner, repo)
            default_branch = repo_info.get("default_branch", "main")

            # 2. Get full tree
            raw_tree = await self.get_repo_tree(client, owner, repo, default_branch)

            # 3. Filter tree
            filtered_tree = self.filter_tree(raw_tree)

            # 4. Select files to fetch
            key_files = self.select_high_priority_files(filtered_tree)

            # 5. Fetch file contents concurrently
            tasks = [
                self.fetch_file_content(client, owner, repo, default_branch, file_path)
                for file_path in key_files
            ]
            results = await asyncio.gather(*tasks)

            file_contents = {path: content for path, content in results if content is not None}

            return filtered_tree, file_contents
