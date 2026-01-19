"""Selector parsing and Playwright locator generation.

This module provides smart detection of selector types and generates
corresponding Playwright locator JavaScript code.

Supported formats:
- CSS selectors: .class, #id, [attribute]
- Role patterns: button:Submit, link:Learn more, button (all buttons)
- Text patterns: text:Add to cart
- Placeholder: placeholder:Email
- Label: label:Username
- Testid: testid:submit-button
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class ParsedSelector:
    """Parsed selector information."""

    type: Literal["role", "text", "placeholder", "label", "css", "testid"]
    value: str
    role: str | None = None  # For role type selectors
    name: str | None = None  # For role type selectors with name


# Common HTML tags that should be treated as CSS tag selectors
# These are interpreted as page.locator('tag') not page.getByText('tag')
HTML_TAGS = {
    # Document structure
    "html",
    "head",
    "body",
    "main",
    "header",
    "footer",
    "nav",
    "aside",
    "section",
    "article",
    # Content
    "div",
    "span",
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    # Lists
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    # Tables
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    # Forms
    "form",
    "input",
    "button",
    "select",
    "option",
    "textarea",
    "label",
    "fieldset",
    "legend",
    # Media
    "img",
    "video",
    "audio",
    "canvas",
    "svg",
    "iframe",
    # Interactive
    "a",
    "details",
    "summary",
    "dialog",
    # Semantic
    "figure",
    "figcaption",
    "blockquote",
    "pre",
    "code",
    "em",
    "strong",
    "small",
    "mark",
    "time",
    "address",
}

# ARIA roles supported by Playwright getByRole()
SUPPORTED_ROLES = {
    "button",
    "link",
    "textbox",
    "checkbox",
    "radio",
    "combobox",
    "listbox",
    "option",
    "menuitem",
    "menu",
    "dialog",
    "tab",
    "tabpanel",
    "heading",
    "img",
    "list",
    "listitem",
    "table",
    "row",
    "cell",
    "navigation",
    "main",
    "article",
    "region",
    "form",
    "search",
    "alert",
    "status",
    "progressbar",
    "slider",
    "spinbutton",
    "switch",
    "tree",
    "treeitem",
    "grid",
    "gridcell",
}


def parse_target(target: str) -> ParsedSelector:
    """
    Parse target string into structured selector information.

    Args:
        target: Target string in one of supported formats

    Returns:
        ParsedSelector with type and value information

    Examples:
        >>> parse_target("button:Submit")
        ParsedSelector(type='role', value='button', role='button', name='Submit')

        >>> parse_target(".submit-btn")
        ParsedSelector(type='css', value='.submit-btn')

        >>> parse_target("text:Add to cart")
        ParsedSelector(type='text', value='Add to cart')
    """
    # Explicit prefixes
    if target.startswith("text:"):
        return ParsedSelector(type="text", value=target[5:])

    if target.startswith("placeholder:"):
        return ParsedSelector(type="placeholder", value=target[12:])

    if target.startswith("label:"):
        return ParsedSelector(type="label", value=target[6:])

    if target.startswith("testid:"):
        return ParsedSelector(type="testid", value=target[7:])

    # CSS multiple selector (contains comma) - e.g., "span, p, div"
    if "," in target:
        return ParsedSelector(type="css", value=target)

    # CSS selectors (start with . # or [)
    if target.startswith(".") or target.startswith("#") or target.startswith("["):
        return ParsedSelector(type="css", value=target)

    # Check for role patterns (role:name or just role)
    if ":" in target:
        parts = target.split(":", 1)
        role = parts[0].lower()
        name = parts[1] if len(parts) > 1 else None

        if role in SUPPORTED_ROLES:
            return ParsedSelector(type="role", value=target, role=role, name=name)

    # Check if it's just a role name
    if target.lower() in SUPPORTED_ROLES:
        return ParsedSelector(type="role", value=target, role=target.lower(), name=None)

    # Check if it's an HTML tag name (treat as CSS selector)
    if target.lower() in HTML_TAGS:
        return ParsedSelector(type="css", value=target.lower())

    # Default: treat as text
    return ParsedSelector(type="text", value=target)


def generate_locator_js(parsed: ParsedSelector, page_var: str = "page") -> str:
    """
    Generate Playwright locator JavaScript code from parsed selector.

    Args:
        parsed: ParsedSelector from parse_target()
        page_var: Variable name for the page object (default "page").
                  Use "targetPage" for multi-tab support.

    Returns:
        JavaScript code string for Playwright locator
    """
    if parsed.type == "role":
        if parsed.name:
            # Escape single quotes in name
            escaped_name = parsed.name.replace("'", "\\'")
            return f"{page_var}.getByRole('{parsed.role}', {{ name: '{escaped_name}' }})"
        return f"{page_var}.getByRole('{parsed.role}')"

    if parsed.type == "text":
        escaped_text = parsed.value.replace("'", "\\'")
        return f"{page_var}.getByText('{escaped_text}')"

    if parsed.type == "placeholder":
        escaped = parsed.value.replace("'", "\\'")
        return f"{page_var}.getByPlaceholder('{escaped}')"

    if parsed.type == "label":
        escaped = parsed.value.replace("'", "\\'")
        return f"{page_var}.getByLabel('{escaped}')"

    if parsed.type == "testid":
        escaped = parsed.value.replace("'", "\\'")
        return f"{page_var}.getByTestId('{escaped}')"

    if parsed.type == "css":
        escaped = parsed.value.replace("'", "\\'")
        return f"{page_var}.locator('{escaped}')"

    # Fallback to text
    escaped = parsed.value.replace("'", "\\'")
    return f"{page_var}.getByText('{escaped}')"


def target_to_locator_js(target: str, page_var: str = "page") -> str:
    """
    Convert target string directly to Playwright locator JavaScript.

    Convenience function combining parse_target and generate_locator_js.
    Supports Playwright chaining syntax with ' >> '.

    Args:
        target: Target string in any supported format.
                Supports chaining: "text:Product >> button" becomes
                page.getByText('Product').locator('button')
        page_var: Variable name for the page object (default "page").
                  Use "targetPage" for multi-tab support.

    Returns:
        JavaScript code string for Playwright locator
    """
    # Support Playwright chaining syntax: "selector1 >> selector2 >> selector3"
    if " >> " in target:
        parts = target.split(" >> ")
        # First part uses the page variable
        result = generate_locator_js(parse_target(parts[0]), page_var)
        # Subsequent parts chain with .locator()
        for part in parts[1:]:
            parsed = parse_target(part)
            if parsed.type == "css":
                escaped = parsed.value.replace("'", "\\'")
                result = f"{result}.locator('{escaped}')"
            elif parsed.type == "role":
                if parsed.name:
                    escaped_name = parsed.name.replace("'", "\\'")
                    result = f"{result}.getByRole('{parsed.role}', {{ name: '{escaped_name}' }})"
                else:
                    result = f"{result}.getByRole('{parsed.role}')"
            elif parsed.type == "text":
                escaped = parsed.value.replace("'", "\\'")
                result = f"{result}.getByText('{escaped}')"
            elif parsed.type == "testid":
                escaped = parsed.value.replace("'", "\\'")
                result = f"{result}.getByTestId('{escaped}')"
            else:
                # Default: use locator for other types
                escaped = parsed.value.replace("'", "\\'")
                result = f"{result}.locator('{escaped}')"
        return result

    parsed = parse_target(target)
    return generate_locator_js(parsed, page_var)
