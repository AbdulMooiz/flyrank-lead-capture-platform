from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.core.config import settings
from app.api import auth, dashboard, embed, submissions, widgets

app = FastAPI(title="FlyRank Lead Capture Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key"],
)


@app.middleware("http")
async def body_size_limit(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_body_bytes:
                return JSONResponse(status_code=413, content={"detail": "Request body is too large"})
        return await call_next(request)


app.include_router(auth.router)
app.include_router(widgets.router)
app.include_router(embed.router)
app.include_router(submissions.router)
app.include_router(dashboard.router)


@app.get("/widget.v1.js", response_class=Response)
def widget_bundle() -> Response:
        script = """(() => {
    const host = document.currentScript;
    const mount = host.previousElementSibling?.matches('[data-flyrank-widget]') ? host.previousElementSibling : document.querySelector('[data-flyrank-widget]');
    if (!mount) return;
    const id = mount.dataset.flyrankWidget;
    const api = new URL(host.src).origin;
    fetch(`${api}/api/widgets/${id}/config`).then(r => r.json()).then(config => {
        const form = document.createElement('form');
        form.innerHTML = `<h3>${config.title}</h3><p>${config.description || ''}</p>` + config.fields.map(f => `<label>${f.label || f.name}<input name="${f.name}" type="${f.type || 'text'}" ${f.required ? 'required' : ''}></label>`).join('') + '<input name="website" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px" aria-hidden="true"><button type="submit">' + config.button_text + '</button><output></output>';
        form.addEventListener('submit', async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(form)); const honeypot = data.website || ''; delete data.website; const output = form.querySelector('output'); const response = await fetch(config.submit_url, {method:'POST', headers:{'Content-Type':'application/json','Idempotency-Key':crypto.randomUUID()}, body:JSON.stringify({widget_id:id,data,honeypot})}); output.textContent = response.ok ? 'Thanks, we received your message.' : ((await response.json()).detail || 'Please check your entries.'); });
        mount.replaceChildren(form);
    });
})();"""
        return Response(content=script, media_type="application/javascript", headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
