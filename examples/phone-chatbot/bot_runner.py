import argparse
import json
import os
import shlex
import subprocess
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import aiohttp
from bot_constants import (
    MAX_SESSION_TIME,
    REQUIRED_ENV_VARS,
)
from bot_definitions import bot_registry
from bot_runner_helpers import (
    determine_room_capabilities,
    ensure_prompt_config,
    process_dialin_request,
)
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, APIRouter, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import sys
import traceback

from pipecat.transports.services.helpers.daily_rest import (
    DailyRESTHelper,
    DailyRoomParams,
    DailyRoomProperties,
    DailyRoomSipParams,
)

load_dotenv(override=True)

daily_helpers = {}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Optional environment variables
OPTIONAL_ENV_VARS = {
    "DAILY_API_KEY": "Daily.co API key (optional)",
    "GOOGLE_API_KEY": "Google API key (optional)",
    "DEEPGRAM_API_KEY": "Deepgram API key (optional)"
}

# Log environment variables (without values for security)
logger.info("Checking environment variables...")
for var, description in OPTIONAL_ENV_VARS.items():
    if os.getenv(var):
        logger.info(f"{var} is set")
    else:
        logger.warning(f"{var} is not set - {description}")

# Pydantic models
class BotStartRequest(BaseModel):
    room_name: str
    bot_name: Optional[str] = "AI Assistant"

class BotResponse(BaseModel):
    status: str
    message: str
    room_name: Optional[str] = None
    bot_name: Optional[str] = None

router = APIRouter()

# ----------------- Environment Validation ----------------- #

def validate_environment():
    missing_vars = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing_vars.append(var)
    if missing_vars:
        print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
        return False
    return True

# ----------------- Daily Room Management ----------------- #


async def create_daily_room(room_url: str = None, config_body: Dict[str, Any] = None):
    """Create or retrieve a Daily room with appropriate properties based on the configuration.

    Args:
        room_url: Optional existing room URL
        config_body: Optional configuration that determines room capabilities

    Returns:
        Dict containing room URL, token, and SIP endpoint
    """
    if not room_url:
        # Get room capabilities based on the configuration
        capabilities = determine_room_capabilities(config_body)

        # Configure SIP parameters if dialin is needed
        sip_params = None
        if capabilities["enable_dialin"]:
            sip_params = DailyRoomSipParams(
                display_name="dialin-user", video=False, sip_mode="dial-in", num_endpoints=2
            )

        # Create the properties object with the appropriate settings
        properties = DailyRoomProperties(sip=sip_params)

        # Set dialout capability if needed
        if capabilities["enable_dialout"]:
            properties.enable_dialout = True

        # Log the capabilities being used
        capability_str = ", ".join([f"{k}={v}" for k, v in capabilities.items()])
        print(f"Creating room with capabilities: {capability_str}")

        params = DailyRoomParams(properties=properties)

        print("Creating new room...")
        room = await daily_helpers["rest"].create_room(params=params)
    else:
        # Check if passed room URL exists
        try:
            room = await daily_helpers["rest"].get_room_from_url(room_url)
        except Exception:
            raise HTTPException(status_code=500, detail=f"Room not found: {room_url}")

    print(f"Daily room: {room.url} {room.config.sip_endpoint}")

    # Get token for the agent
    token = await daily_helpers["rest"].get_token(room.url, MAX_SESSION_TIME)

    if not room or not token:
        raise HTTPException(status_code=500, detail="Failed to get room or token")

    return {"room": room.url, "token": token, "sip_endpoint": room.config.sip_endpoint}


# ----------------- Bot Process Management ----------------- #


async def start_bot(room_details: Dict[str, str], body: Dict[str, Any], example: str) -> bool:
    """Start a bot process with the given configuration.

    Args:
        room_details: Room URL and token
        body: Bot configuration
        example: Example script to run

    Returns:
        Boolean indicating success
    """
    room_url = room_details["room"]
    token = room_details["token"]

    # Properly format body as JSON string for command line
    body_json = json.dumps(body).replace('"', '\\"')
    print(f"++++ Body JSON: {body_json}")

    # Modified to use non-LLM-specific bot module names
    bot_proc = f'python3 -m {example} -u {room_url} -t {token} -b "{body_json}"'
    print(f"Starting bot. Example: {example}, Room: {room_url}")

    try:
        command_parts = shlex.split(bot_proc)
        subprocess.Popen(command_parts, bufsize=1, cwd=os.path.dirname(os.path.abspath(__file__)))
        return True
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start subprocess: {e}")


# ----------------- API Setup ----------------- #


@asynccontextmanager
async def lifespan(app: FastAPI):
    aiohttp_session = aiohttp.ClientSession()
    daily_helpers["rest"] = DailyRESTHelper(
        daily_api_key=os.getenv("DAILY_API_KEY", ""),
        daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        aiohttp_session=aiohttp_session,
    )
    yield
    await aiohttp_session.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------- API Endpoints ----------------- #


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        env_status = {
            var: bool(os.getenv(var))
            for var in OPTIONAL_ENV_VARS.keys()
        }
        
        return {
            "status": "ok",
            "message": "Bot Runner is healthy",
            "environment": {
                "variables": env_status
            }
        }
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=BotResponse)
async def start_bot(request: BotStartRequest, background_tasks: BackgroundTasks):
    """Start a bot in a room."""
    try:
        logger.info(f"Starting bot {request.bot_name} in room {request.room_name}")
        
        # Add your bot initialization logic here
        # This is where you would integrate with your bot framework
        
        return BotResponse(
            status="success",
            message=f"Bot {request.bot_name} started in room {request.room_name}",
            room_name=request.room_name,
            bot_name=request.bot_name
        )
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=BotResponse)
async def stop_bot(request: BotStartRequest):
    """Stop a bot in a room."""
    try:
        logger.info(f"Stopping bot {request.bot_name} in room {request.room_name}")
        
        # Add your bot cleanup logic here
        
        return BotResponse(
            status="success",
            message=f"Bot {request.bot_name} stopped in room {request.room_name}",
            room_name=request.room_name,
            bot_name=request.bot_name
        )
    except Exception as e:
        logger.error(f"Error stopping bot: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ----------------- Main ----------------- #

if __name__ == "__main__":
    # Check environment variables
    for env_var in REQUIRED_ENV_VARS:
        if env_var not in os.environ:
            raise Exception(f"Missing environment variable: {env_var}.")

    parser = argparse.ArgumentParser(description="Pipecat Bot Runner")
    parser.add_argument(
        "--host", type=str, default=os.getenv("HOST", "0.0.0.0"), help="Host address"
    )
    parser.add_argument("--port", type=int, default=os.getenv("PORT", 7860), help="Port number")
    parser.add_argument("--reload", action="store_true", default=True, help="Reload code on change")

    config = parser.parse_args()

    try:
        import uvicorn

        uvicorn.run("bot_runner:app", host=config.host, port=config.port, reload=config.reload)

    except KeyboardInterrupt:
        print("Pipecat runner shutting down...")
