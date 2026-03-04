import os
from typing import List, Dict


class ContextManager:
    def __init__(self, max_tree_depth: int = 3):
        self.max_tree_depth = max_tree_depth

    def build_ascii_tree(self, tree: List[dict]) -> str:
        """Converts the flat Git tree into a simplified ASCII directory tree structure."""
        paths = [item["path"] for item in tree if item.get("type") == "blob"]

        # Build a nested dictionary representing the directory structure
        root = {}
        for path in paths:
            parts = path.split("/")
            current = root
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = None  # None represents a file

        return self._render_tree(root, depth=0)

    def _render_tree(self, node: dict, depth: int) -> str:
        if depth > self.max_tree_depth:
            return "    " * depth + "└── ... (max depth reached)\n"

        output = ""
        keys = sorted(node.keys())
        for i, key in enumerate(keys):
            is_last = i == len(keys) - 1
            prefix = "└── " if is_last else "├── "

            if node[key] is None:
                # File
                output += "    " * depth + prefix + key + "\n"
            else:
                # Directory
                output += "    " * depth + prefix + key + "/\n"
                output += self._render_tree(node[key], depth + 1)

        return output

    def format_context(self, tree: List[dict], file_contents: Dict[str, str]) -> str:
        """Combines the ASCII tree and budgeted file contents into a prompt-ready string."""
        ascii_tree = self.build_ascii_tree(tree)

        # Define strict character budgets to avoid token explosion
        # Note: 1 token is roughly 4 characters in English
        # A 15,000 character limit overall is safe for a typical 8k-16k context window.
        BUDGET_README = 10000
        BUDGET_DEPENDENCIES = 5000
        BUDGET_CODE = 5000

        context_parts = []

        # 1. Add Tree Structure
        tree_section = f"--- REPOSITORY TREE ---\n{ascii_tree}\n\n"
        # Truncate tree if absolutely massive
        if len(tree_section) > 5000:
            tree_section = (
                tree_section[:5000] + "\n... (Tree truncated due to length)\n"
            )
        context_parts.append(tree_section)

        # 2. Add File Contents based on categories
        context_parts.append("--- KEY FILES ---\n")

        for file_path, content in file_contents.items():
            filename = os.path.basename(file_path).lower()

            # Determine budget
            if "readme" in filename:
                budget = BUDGET_README
            elif filename in {
                "package.json",
                "requirements.txt",
                "pyproject.toml",
                "pom.xml",
                "go.mod",
                "docker-compose.yml",
            }:
                budget = BUDGET_DEPENDENCIES
            else:
                budget = BUDGET_CODE

            # Truncate if necessary
            if len(content) > budget:
                content = (
                    content[:budget]
                    + "\n\n... (File truncated due to length constraints) ..."
                )

            context_parts.append(f"File: {file_path}\n```\n{content}\n```\n\n")

        return "".join(context_parts)
