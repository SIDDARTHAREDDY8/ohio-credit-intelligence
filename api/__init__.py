"""Load environment variables before any submodule reads them at import time."""

from dotenv import load_dotenv

# override=True: the parent shell exports an empty ANTHROPIC_API_KEY, which
# would otherwise shadow the real value in .env (load_dotenv won't replace an
# existing var unless told to). The .env file is this project's source of truth.
load_dotenv(override=True)
