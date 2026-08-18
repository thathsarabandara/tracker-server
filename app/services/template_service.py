import os
from datetime import datetime, timezone
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Locate template directory relative to project structure
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "email")

jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"])
)


class TemplateService:
    """Template rendering service for modern HTML email layouts."""

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render specified Jinja2 HTML template with context variables."""
        if not template_name.endswith(".html"):
            template_name += ".html"
        
        # Inject default common global template variables
        default_context = {
            "current_year": datetime.now(timezone.utc).year,
            "company_name": "Pulse",
            "support_email": "noreply@pulse.io"
        }
        merged_context = {**default_context, **context}
        
        template = jinja_env.get_template(template_name)
        return template.render(**merged_context)


template_service = TemplateService()
