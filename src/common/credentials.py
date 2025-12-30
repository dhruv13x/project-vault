import os
import sys
import json
import base64
import urllib.request
from typing import Tuple, Optional, Dict, Any
from . import config as config_loader

def load_env_file(filepath: str = ".env") -> Dict[str, str]:
    """
    Parses a simple KEY=VALUE .env file.
    """
    env_vars = {}
    if not os.path.exists(filepath):
        return env_vars
    
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    value = value.strip()
                    # Remove surrounding quotes if present
                    if len(value) >= 2:
                        first_char = value[0]
                        last_char = value[-1]
                        if first_char == last_char and first_char in ['"', "'"]:
                            value = value[1:-1]
                    env_vars[key.strip()] = value
    except Exception as e:
        # Silently fail or log? User requested robust logic.
        pass
    return env_vars

def get_doppler_secrets() -> Dict[str, str]:
    """
    Fetches secrets from Doppler if DOPPLER_TOKEN is present.
    Checks os.environ, then .env for the token.
    """
    # Check real env first
    token = os.environ.get("DOPPLER_TOKEN")
    
    # Check .env if not in real env
    if not token:
        local_env = load_env_file(".env")
        token = local_env.get("DOPPLER_TOKEN")
        
        # Check doppler.env (common pattern)
        if not token:
            doppler_env = load_env_file("doppler.env")
            token = doppler_env.get("DOPPLER_TOKEN")

    if not token:
        return {}

    url = "https://api.doppler.com/v3/configs/config/secrets/download?format=json"
    req = urllib.request.Request(url)
    auth_str = f"{token}:"
    b64_auth = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
    req.add_header("Authorization", f"Basic {b64_auth}")

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.load(response)
    except Exception:
        # Failed to fetch from Doppler (network, bad token, etc.)
        return {}

def resolve_credentials(args: Any, allow_fail: bool = False) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Resolves Cloud Credentials (AWS/B2) using the Priority Ladder:
    1. CLI Arguments (args.key_id, args.secret_key) - if they existed
    2. Doppler Secrets
    3. Environment Variables
    4. .env Files
    5. Persistent Config (pv.toml)

    Returns:
        (key_id, secret_key, source)
        source is a string like "CLI", "Doppler", "Environment", ".env", "Config", or None.
    """
    
    # 1. CLI Arguments
    cli_key = getattr(args, 'key_id', None)
    cli_secret = getattr(args, 'secret_key', None)
    
    if cli_key and cli_secret:
        return cli_key, cli_secret, "CLI"

    # Initialize generic placeholders
    access_key: Optional[str] = cli_key
    secret_key: Optional[str] = cli_secret
    current_source: Optional[str] = None

    def check_source(source_dict: Dict[str, Any], source_name: str) -> bool:
        nonlocal access_key, secret_key, current_source
        updated = False
        
        # List of candidate keys for Access Key ID
        candidates_key = [
            "PV_AWS_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID",
            "PV_B2_KEY_ID", "B2_KEY_ID"
        ]
        # List of candidate keys for Secret Key
        candidates_secret = [
            "PV_AWS_SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY",
            "PV_B2_APP_KEY", "B2_APP_KEY"
        ]

        if not access_key:
            for k in candidates_key:
                if source_dict.get(k):
                    access_key = str(source_dict.get(k))
                    current_source = source_name
                    updated = True
                    break
        
        if not secret_key:
            for k in candidates_secret:
                if source_dict.get(k):
                    secret_key = str(source_dict.get(k))
                    # Only set source if not already set by key
                    if not current_source:
                        current_source = source_name
                    updated = True
                    break
        return updated

    # 2. Doppler
    doppler_secrets = get_doppler_secrets()
    if doppler_secrets:
        check_source(doppler_secrets, "Doppler")
        if access_key and secret_key: return access_key, secret_key, "Doppler"

    # 3. Environment Variables
    check_source(os.environ, "Environment")
    if access_key and secret_key: return access_key, secret_key, "Environment"

    # 4. .env File
    dotenv = load_env_file(".env")
    check_source(dotenv, ".env File")
    if access_key and secret_key: return access_key, secret_key, ".env File"

    # 5. Persistent Config (pv.toml) - Opt-In Insecure Storage
    config = config_loader.load_project_config()
    creds_section = config.get("credentials", {})
    
    # Check if explicit opt-in is enabled (optional but good practice, though presence of keys implies intent)
    # We check simply for the keys.
    if not access_key and creds_section.get("key_id"):
        access_key = creds_section.get("key_id")
        current_source = "Config (pv.toml)"
        
    if not secret_key and creds_section.get("secret_key"):
        secret_key = creds_section.get("secret_key")
        if current_source != "Config (pv.toml)": 
             current_source = "Config (pv.toml)"

    if access_key and secret_key:
        return access_key, secret_key, current_source

    if allow_fail:
        return None, None, None

    return None, None, None

def resolve_setting(
    key: str, 
    args: Any, 
    arg_name: str = None, 
    env_keys: list = None, 
    config_key: str = None,
    default: Any = None
) -> Any:
    """
    Resolves a general setting (bucket, endpoint, paths) using Priority Ladder.
    """
    # 1. CLI Argument
    if arg_name and getattr(args, arg_name, None):
        return getattr(args, arg_name)

    # 2. Doppler
    doppler_secrets = get_doppler_secrets()
    if doppler_secrets and env_keys:
        for ek in env_keys:
            if doppler_secrets.get(ek):
                return doppler_secrets.get(ek)

    # 3. Environment Variables
    if env_keys:
        for ek in env_keys:
            if os.environ.get(ek):
                return os.environ.get(ek)

    # 4. .env File
    dotenv = load_env_file(".env")
    if env_keys:
        for ek in env_keys:
            if dotenv.get(ek):
                return dotenv.get(ek)

    # 5. Persistent Config
    if config_key:
        config = config_loader.load_project_config()
        if config.get(config_key):
            return config.get(config_key)

    return default

def get_full_env() -> Dict[str, str]:
    """
    Returns a merged environment dictionary following priority:
    1. Doppler Secrets
    2. Real Environment Variables
    3. .env File
    """
    # Base: .env
    full_env = load_env_file(".env")
    
    # Overlay: Real Env
    full_env.update(os.environ)
    
    # Overlay: Doppler (Highest Env priority)
    doppler = get_doppler_secrets()
    if doppler:
        full_env.update(doppler)
        
    return full_env


def get_cloud_provider_info() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Determines the cloud provider, bucket, and endpoint for display purposes.

    Returns:
        (provider, bucket, endpoint)
    """
    full_env = get_full_env()
    config = config_loader.load_project_config()
    provider = "Unknown"

    # 1. Determine Provider from credentials
    env_keys = set(full_env.keys())
    has_b2_keys = any(k in env_keys for k in ["B2_KEY_ID", "PV_B2_KEY_ID"])
    has_aws_keys = any(k in env_keys for k in ["AWS_ACCESS_KEY_ID", "PV_AWS_ACCESS_KEY_ID"])

    if has_b2_keys:
        provider = "Backblaze B2"
    elif has_aws_keys:
        provider = "AWS S3"
    
    # 2. Try to infer from endpoint if keys are ambiguous or not in env
    endpoint = config.get("endpoint") or full_env.get("PV_ENDPOINT")
    if provider == "Unknown" and endpoint:
        if "backblazeb2.com" in endpoint:
            provider = "Backblaze B2"
        elif "amazonaws.com" in endpoint or "s3" in endpoint:
            provider = "AWS S3"

    # 3. Get bucket
    bucket = config.get("bucket") or full_env.get("PV_BUCKET")

    return provider, bucket, endpoint
