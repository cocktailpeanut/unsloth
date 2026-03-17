# Unsloth Studio

This launcher clones the `unslothai/unsloth` repository and runs Unsloth Studio locally through Pinokio.

## What It Does

- Clones the upstream repository into `app/`
- Builds the Studio frontend from `studio/frontend`
- Installs the Studio Python stack into a local Pinokio venv at `env/`
- Clones `llama.cpp` under `app/.unsloth/llama.cpp` for GGUF tooling support
- Installs `conda-forge::llama.cpp` into an app-local conda prefix first, with source build fallback if needed
- Starts the Studio backend on `127.0.0.1` with an auto-assigned port
- Keeps Unsloth Studio runtime data under `app/.unsloth/`

## How To Use

1. Click `Install`.
2. Click `Start`.
3. On first launch, open the `Terminal` tab and copy the bootstrap password printed by the backend.
4. Sign in with username `unsloth` and the printed password.
5. Change the password when prompted.

The first install or update may still take longer than a normal Python-only setup because the launcher provisions GGUF tooling. It now prefers the `conda-forge` package for `llama.cpp`, and only falls back to a source build if that does not yield a usable `llama-server`.

The launcher keeps the cloned repo in `app/`. `Reset` removes the cloned repo and any launcher-created venv state.

## API

Most API routes require a bearer token from the auth endpoints below. Health and auth-status are available without login.

Replace `127.0.0.1:8000` below with the actual Studio URL shown by the launcher, for example the `Open Studio` tab or the `Terminal` output after startup.

### Curl

Check the server:

```bash
curl http://127.0.0.1:PORT/api/health
```

Check auth bootstrap state:

```bash
curl http://127.0.0.1:PORT/api/auth/status
```

Log in and get tokens:

```bash
curl -X POST http://127.0.0.1:PORT/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"unsloth","password":"YOUR_BOOTSTRAP_PASSWORD"}'
```

Query the current inference status:

```bash
curl http://127.0.0.1:PORT/api/inference/status \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

OpenAI-compatible chat after a model is loaded:

```bash
curl -X POST http://127.0.0.1:PORT/v1/chat/completions \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "active-model",
    "messages": [
      {"role": "user", "content": "Hello from Pinokio"}
    ],
    "stream": false
  }'
```

### Python

```python
import requests

base_url = "http://127.0.0.1:PORT"

health = requests.get(f"{base_url}/api/health", timeout=30)
print(health.json())

login = requests.post(
    f"{base_url}/api/auth/login",
    json={
        "username": "unsloth",
        "password": "YOUR_BOOTSTRAP_PASSWORD",
    },
    timeout=30,
)
token = login.json()["access_token"]

status = requests.get(
    f"{base_url}/api/inference/status",
    headers={"Authorization": f"Bearer {token}"},
    timeout=30,
)
print(status.json())
```

### JavaScript

```javascript
const baseUrl = "http://127.0.0.1:PORT";

const health = await fetch(`${baseUrl}/api/health`);
console.log(await health.json());

const login = await fetch(`${baseUrl}/api/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    username: "unsloth",
    password: "YOUR_BOOTSTRAP_PASSWORD",
  }),
});

const { access_token } = await login.json();

const status = await fetch(`${baseUrl}/api/inference/status`, {
  headers: {
    Authorization: `Bearer ${access_token}`,
  },
});

console.log(await status.json());
```
