from src.modules.email.templates import EmailTemplateRenderer


def test_base_email_template_renders_basic_elements_and_escapes_values() -> None:
    html = EmailTemplateRenderer().render(
        "modules/email/templates/base.html",
        heading="Account update",
        message="Hello <Admin>",
    )

    assert "<h2" in html
    assert "font-family:Arial, Helvetica, sans-serif" in html
    assert "font-size:16px" in html
    assert "Account update" in html
    assert "Hello &lt;Admin&gt;" in html


def test_zaansrecht_template_inherits_base_layout_and_overrides_font() -> None:
    html = EmailTemplateRenderer().render(
        "modules/forms/templates/zaansrecht_email.html",
        fields=({"label": "Naam", "value": "Zaansrecht User"},),
        email="reply@example.com",
    )

    assert "<!doctype html>" in html
    assert "This is an automated notification" not in html
    assert "Verdana, Geneva, sans-serif" in html
    assert "Nieuwe formulierinzending" in html
    assert "Zaansrecht User" in html
    assert "reply@example.com" in html
