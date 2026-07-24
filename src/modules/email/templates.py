"""Render reusable HTML email templates.

This module configures Jinja to load templates from the application's ``src``
directory. It supports shared template inheritance, such as an application email
extending the general email layout, and automatically escapes values inserted
into HTML or XML templates.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# ``templates.py`` lives in ``src/modules/email``. Moving two parents upward
# provides ``src`` as the common root for templates owned by any application or
# shared module.
TEMPLATE_ROOT = Path(__file__).resolve().parents[2]


class EmailTemplateRenderer:
    """A configured Jinja renderer for application and shared email templates.

    An instance represents the email-template environment: it knows where
    templates are stored, how inheritance is resolved, and which template types
    require automatic escaping. A different root can be supplied by tests or by
    an application that stores its templates elsewhere.
    """

    def __init__(self, template_root: Path = TEMPLATE_ROOT):
        """Create a renderer that loads templates beneath ``template_root``."""
        self.environment = Environment(
            loader=FileSystemLoader(template_root),
            autoescape=select_autoescape(("html", "xml")),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, **context: object) -> str:
        """Render ``template_name`` with the provided context values."""
        return self.environment.get_template(template_name).render(**context)
