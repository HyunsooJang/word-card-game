#!/usr/bin/env python3
import base64
import json
import os
import shlex
import subprocess
import sys
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parent
MAX_TEXT_LENGTH = 120


class AppError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def load_dotenv(dotenv_path):
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def get_provider_config():
    requested = os.getenv("TTS_PROVIDER", "").strip().lower()
    providers = {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "google": bool(
            os.getenv("GOOGLE_TTS_ACCESS_TOKEN")
            or os.getenv("GOOGLE_TTS_ACCESS_TOKEN_CMD")
        ),
    }

    if requested:
        if providers.get(requested):
            if requested == "google":
                try:
                    resolve_google_token()
                except AppError as exc:
                    return {
                        "available": False,
                        "provider": "google",
                        "label": "Google Cloud (auth required)",
                        "error": exc.message,
                    }
            return build_provider_payload(requested)
        return {
            "available": False,
            "provider": requested,
            "label": f"{requested} not configured",
            "error": f"TTS_PROVIDER is set to '{requested}', but credentials are missing.",
        }

    if providers["openai"]:
        return build_provider_payload("openai")
    if providers["google"]:
        try:
            resolve_google_token()
        except AppError as exc:
            return {
                "available": False,
                "provider": "google",
                "label": "Google Cloud (auth required)",
                "error": exc.message,
            }
        return build_provider_payload("google")

    return {
        "available": False,
        "provider": "none",
        "label": "not configured",
        "error": "No TTS provider credentials found.",
    }


def build_provider_payload(provider):
    if provider == "openai":
        voice = os.getenv("OPENAI_TTS_VOICE", "coral")
        model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
        return {
            "available": True,
            "provider": "openai",
            "label": f"OpenAI ({voice})",
            "voice": voice,
            "model": model,
        }

    voice_name = os.getenv("GOOGLE_TTS_VOICE_NAME", "").strip()
    language_code = os.getenv("GOOGLE_TTS_LANGUAGE_CODE", "en-US")
    label_voice = voice_name or f"{language_code} default"
    return {
        "available": True,
        "provider": "google",
        "label": f"Google Cloud ({label_voice})",
        "voice": label_voice,
    }


def read_json_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise AppError(HTTPStatus.BAD_REQUEST, f"Invalid JSON body: {exc}") from exc


def read_text(payload):
    text = str(payload.get("text", "")).strip()
    if not text:
        raise AppError(HTTPStatus.BAD_REQUEST, "Field 'text' is required.")
    if len(text) > MAX_TEXT_LENGTH:
        raise AppError(HTTPStatus.BAD_REQUEST, f"Text must be {MAX_TEXT_LENGTH} characters or fewer.")
    return text


def resolve_google_token():
    static_token = os.getenv("GOOGLE_TTS_ACCESS_TOKEN", "").strip()
    if static_token:
        return static_token

    token_cmd = os.getenv("GOOGLE_TTS_ACCESS_TOKEN_CMD", "").strip()
    if token_cmd:
        result = subprocess.run(
            shlex.split(token_cmd),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise AppError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                f"Failed to fetch Google access token: {result.stderr.strip() or 'unknown error'}",
            )
        token = result.stdout.strip()
        if token:
            return token

    raise AppError(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        "Google TTS is selected but GOOGLE_TTS_ACCESS_TOKEN or GOOGLE_TTS_ACCESS_TOKEN_CMD is missing.",
    )


def fetch_openai_tts(text):
    body = {
        "model": os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        "voice": os.getenv("OPENAI_TTS_VOICE", "coral"),
        "input": text,
        "format": "mp3",
    }
    instructions = os.getenv("OPENAI_TTS_INSTRUCTIONS", "").strip()
    if instructions:
        body["instructions"] = instructions

    request = Request(
        "https://api.openai.com/v1/audio/speech",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    return perform_binary_request(request, default_content_type="audio/mpeg")


def fetch_google_tts(text):
    token = resolve_google_token()
    voice_name = os.getenv("GOOGLE_TTS_VOICE_NAME", "").strip()
    voice = {"languageCode": os.getenv("GOOGLE_TTS_LANGUAGE_CODE", "en-US")}
    if voice_name:
        voice["name"] = voice_name
    else:
        voice["ssmlGender"] = os.getenv("GOOGLE_TTS_SSML_GENDER", "FEMALE")

    body = {
        "input": {"text": text},
        "voice": voice,
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": float(os.getenv("GOOGLE_TTS_SPEAKING_RATE", "0.92")),
        },
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    project_id = os.getenv("GOOGLE_TTS_PROJECT_ID", "").strip()
    if project_id:
        headers["x-goog-user-project"] = project_id

    request = Request(
        "https://texttospeech.googleapis.com/v1/text:synthesize",
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    raw_json, _ = perform_binary_request(request, expected_json=True)
    try:
        audio_content = json.loads(raw_json.decode("utf-8"))["audioContent"]
        return base64.b64decode(audio_content), "audio/mpeg"
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise AppError(HTTPStatus.BAD_GATEWAY, f"Invalid response from Google TTS: {exc}") from exc


def perform_binary_request(request, default_content_type="application/octet-stream", expected_json=False):
    try:
        with urlopen(request, timeout=45) as response:
            content_type = response.headers.get("Content-Type", default_content_type)
            payload = response.read()
            if expected_json:
                return payload, content_type
            return payload, content_type
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AppError(exc.code, body or f"Upstream request failed with status {exc.code}.") from exc
    except URLError as exc:
        raise AppError(HTTPStatus.BAD_GATEWAY, f"Upstream request failed: {exc.reason}") from exc


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/tts/config":
            self.send_json(HTTPStatus.OK, get_provider_config())
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/tts":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        try:
            provider_config = get_provider_config()
            if not provider_config["available"]:
                raise AppError(HTTPStatus.SERVICE_UNAVAILABLE, provider_config["error"])

            text = read_text(read_json_body(self))
            if provider_config["provider"] == "openai":
                audio_bytes, content_type = fetch_openai_tts(text)
            elif provider_config["provider"] == "google":
                audio_bytes, content_type = fetch_google_tts(text)
            else:
                raise AppError(HTTPStatus.SERVICE_UNAVAILABLE, "No TTS provider configured.")

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(audio_bytes)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(audio_bytes)
        except AppError as exc:
            self.send_json(exc.status, {"error": exc.message})

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_str, *args):
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format_str % args))


def main():
    load_dotenv(ROOT_DIR / ".env")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = ThreadingHTTPServer(("0.0.0.0", port), partial(AppHandler))
    print(f"Serving on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
