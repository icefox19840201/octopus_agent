from fastapi import Request
from pathlib import Path
import jinja2

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)))

async def default(request: Request):
    template = env.get_template("default.html")
    from starlette.responses import HTMLResponse
    return HTMLResponse(content=template.render(request=request))
