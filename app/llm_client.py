import os
import json
import logging
from openai import AsyncOpenAI
from app.schemas import SummarizeResponse

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        nebius_key = os.environ.get("NEBIUS_API_KEY")
        if not nebius_key:
            raise ValueError("NEBIUS_API_KEY environment variable is not set.")
        self.client = AsyncOpenAI(
            api_key=nebius_key, base_url="https://api.studio.nebius.ai/v1/"
        )
        # self.model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
        self.model = os.getenv("LLM_MODEL", "MiniMaxAI/MiniMax-M2.1")

    async def generate_summary(self, context: str) -> SummarizeResponse:
        system_prompt = (
            "You are a senior software architect analyzing a GitHub repository.\n"
            "Based on the provided repository tree, documentation, and configuration files, extract the following:\n"
            "1. 'summary': A brief, human-readable description of what the project does.\n"
            "2. 'technologies': A list of the main technologies, languages, and frameworks used. No need to include the test frameworks.\n"
            "3. 'structure': A brief description of the project's directory structure and architecture.\n\n"
            "Output your response strictly as a JSON object matching this schema:\n"
            "{\n"
            '  "summary": "...",\n'
            '  "technologies": ["..."],\n'
            '  "structure": "..."\n'
            "}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context},
                ],
                response_format={
                    "type": "json_object",
                    "json_schema": {
                        "name": "summarize_response",
                        "strict": True,
                        "schema": SummarizeResponse.model_json_schema(),
                    },
                },
                temperature=0.2,
                max_tokens=2048,
            )

            result_content = response.choices[0].message.content

            # Parse JSON to validate
            data = json.loads(result_content)
            print(data)

            return SummarizeResponse(
                summary=data.get("summary", "Summary not available."),
                technologies=data.get("technologies", []),
                structure=data.get("structure", "Structure not available."),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise Exception("LLM returned malformed JSON.")
            # TODO: I would like to try fixing the JSON response by passing it back to the LLM and ask it to fix the JSON response.

        except Exception as e:
            logger.error(f"LLM API Error: {str(e)}")
            raise Exception(f"Failed to communicate with LLM: {str(e)}")
