import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.schemas import SummarizeRequest, SummarizeResponse, ErrorResponse
from app.github_client import GitHubClient
from app.context_manager import ContextManager
from app.llm_client import LLMClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Repository Summarizer API")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "An internal server error occurred."},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422, content={"status": "error", "message": str(exc)}
    )


@app.post(
    "/summarize",
    response_model=SummarizeResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def summarize_repo(request: SummarizeRequest):
    logger.info(f"Received request to summarize: {request.github_url}")

    url_str = str(request.github_url)
    github_client = GitHubClient()

    # 1. Fetch Repository Context
    try:
        tree, contents = await github_client.fetch_repo_context(url_str)
    except ValueError as ve:
        # Invalid URL or 404 Not Found
        return JSONResponse(
            status_code=400, content={"status": "error", "message": str(ve)}
        )
    except Exception as e:
        logger.error(f"GitHub client error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Failed to fetch repository data: {str(e)}",
            },
        )

    # 2. Manage and Format Context
    context_manager = ContextManager()
    formatted_context = context_manager.format_context(tree, contents)

    # 3. Generate Summary using LLM
    try:
        llm_client = LLMClient()
        try:
            return await llm_client.generate_summary(formatted_context)
        except Exception as e:
            logger.error(f"LLM API Error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"Failed to communicate with LLM: {str(e)}",
                },
            )

    except ValueError as ve:
        # E.g. Missing API Keys
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(ve)}
        )
    except Exception as e:
        logger.error(f"Top-level error processing request: {str(e)}")
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.get("/health")
async def health_check():
    return {"status": "ok"}
