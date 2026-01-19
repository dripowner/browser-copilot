"""Page exploration browser tools.

Provides tools for discovering interactive elements on the page,
enabling the agent to understand page structure before interacting.
"""

import json

from langchain_core.tools import tool

from src.agent.tools._executor import BrowserExecutor
from src.agent.tools._templates import build_async_function


@tool
async def browser_explore_page(
    include_buttons: bool = True,
    include_inputs: bool = True,
    include_links: bool = False,
    limit: int = 30,
) -> str:
    """
    Discover interactive elements on the current page.

    USE THIS TOOL FIRST when you need to interact with a new page!
    It shows what buttons, inputs, and links are available and how to target them.

    Args:
        include_buttons: Include buttons and clickable elements (default: True)
        include_inputs: Include input fields, textareas, selects (default: True)
        include_links: Include links (default: False - usually too many)
        limit: Maximum elements per category (default: 30)

    Returns:
        JSON with discovered elements, each containing:
        - type: "button" | "input" | "link" | "select" | "textarea"
        - text: Visible text or label
        - selector: Recommended selector to use with browser tools
        - attributes: Relevant attributes (placeholder, name, type, href)
    """
    include_buttons_js = "true" if include_buttons else "false"
    include_inputs_js = "true" if include_inputs else "false"
    include_links_js = "true" if include_links else "false"

    code_body = f"""
    const results = {{
      buttons: [],
      inputs: [],
      links: [],
      summary: {{}}
    }};

    const limit = {limit};
    const includeButtons = {include_buttons_js};
    const includeInputs = {include_inputs_js};
    const includeLinks = {include_links_js};

    function cleanText(text) {{
      if (!text) return '';
      return text
        .replace(/\\xAD/g, '')  // Remove soft hyphens completely
        .replace(/[\\u200B-\\u200D\\uFEFF\\xA0]/g, ' ')
        .replace(/\\s+/g, ' ')
        .trim()
        .substring(0, 100);
    }}

    // Extract best available text from element (tries multiple sources)
    function getBestText(el) {{
      // 1. Try innerText (better for nested elements)
      let text = (el.innerText || '').trim();
      if (text && text.length > 0 && text.length < 200) return cleanText(text);

      // 2. Try textContent
      text = (el.textContent || '').trim();
      if (text && text.length > 0 && text.length < 200) return cleanText(text);

      // 3. Try aria-label
      const ariaLabel = el.getAttribute('aria-label');
      if (ariaLabel) return cleanText(ariaLabel);

      // 4. Try title
      const title = el.getAttribute('title');
      if (title) return cleanText(title);

      // 5. Try aria-labelledby
      const labelledBy = el.getAttribute('aria-labelledby');
      if (labelledBy) {{
        const labelEl = document.getElementById(labelledBy);
        if (labelEl) return cleanText(labelEl.textContent);
      }}

      // 6. For links, try to extract meaningful part from href
      const href = el.getAttribute('href');
      if (href) {{
        if (href.includes('cart') || href.includes('basket') || href.includes('корзин')) return '[Cart/Корзина]';
        if (href.includes('checkout')) return '[Checkout]';
        if (href.includes('login') || href.includes('auth')) return '[Login]';
      }}

      return '';
    }}

    // Get class hints for debugging
    function getClassHints(el) {{
      const classes = el.className;
      if (!classes || typeof classes !== 'string') return null;
      // Return first 3 meaningful class names
      const parts = classes.split(/\\s+/).filter(c => c.length > 2).slice(0, 3);
      return parts.length > 0 ? parts.join(' ') : null;
    }}

    function getSelectorRecommendation(el, type) {{
      // Priority: testid > role+name > placeholder > id > class
      const testId = el.getAttribute('data-testid') || el.getAttribute('data-test-id');
      if (testId) return `testid:${{testId}}`;

      const ariaLabel = el.getAttribute('aria-label');
      const text = cleanText(el.textContent || el.innerText);
      const placeholder = el.getAttribute('placeholder');
      const name = el.getAttribute('name');
      const id = el.getAttribute('id');

      // For buttons - prefer role:name
      if (type === 'button' && text) {{
        return `button:${{text}}`;
      }}

      // For links - prefer role:name
      if (type === 'link' && text) {{
        return `link:${{text}}`;
      }}

      // For inputs - prefer placeholder or label
      if (type === 'input' || type === 'textarea' || type === 'select') {{
        if (placeholder) return `placeholder:${{placeholder}}`;

        // Try to find associated label
        if (id) {{
          const label = document.querySelector(`label[for="${{id}}"]`);
          if (label) return `label:${{cleanText(label.textContent)}}`;
        }}

        if (ariaLabel) return `[aria-label="${{ariaLabel}}"]`;
        if (name) return `[name="${{name}}"]`;
      }}

      // Fallback to id or generate CSS
      if (id) return `#${{id}}`;

      return null;
    }}

    // Discover buttons - expanded selector to catch more interactive elements
    if (includeButtons) {{
      // Extended selector: standard buttons + cart-like links + clickable elements with icons
      const buttons = targetPage.locator(`
        button,
        [role="button"],
        input[type="submit"],
        input[type="button"],
        a.button, a.btn,
        a[class*="cart"], a[class*="basket"], a[class*="корзин"],
        a[href*="cart"], a[href*="basket"], a[href*="checkout"],
        [class*="CartButton"], [class*="cart-button"], [class*="basket-button"],
        div[class*="cart"][onclick], div[class*="basket"][onclick],
        [onclick]:not(a):not(button)
      `.replace(/\\s+/g, ' '));
      const count = await buttons.count();

      for (let i = 0; i < Math.min(count, limit); i++) {{
        try {{
          const el = buttons.nth(i);
          const isVisible = await el.isVisible().catch(() => false);
          if (!isVisible) continue;

          const type = await el.getAttribute('type').catch(() => null);
          const href = await el.getAttribute('href').catch(() => null);

          // Get element handle for better text extraction and selector
          const handle = await el.elementHandle().catch(() => null);
          let text = '';
          let selector = null;
          let classHints = null;

          if (handle) {{
            // Use getBestText for robust text extraction
            const extracted = await targetPage.evaluate((el) => {{
              // getBestText implementation inline for evaluate context
              let text = (el.innerText || '').trim();
              if (text && text.length > 0 && text.length < 200) {{
                text = text.replace(/\\xAD/g, '').replace(/[\\u200B-\\u200D\\uFEFF\\xA0]/g, ' ').replace(/\\s+/g, ' ').trim().substring(0, 100);
              }} else {{
                text = (el.textContent || '').trim();
                if (text && text.length > 0 && text.length < 200) {{
                  text = text.replace(/\\xAD/g, '').replace(/[\\u200B-\\u200D\\uFEFF\\xA0]/g, ' ').replace(/\\s+/g, ' ').trim().substring(0, 100);
                }} else {{
                  text = '';
                }}
              }}

              const ariaLabel = el.getAttribute('aria-label');
              if (!text && ariaLabel) text = ariaLabel;

              const title = el.getAttribute('title');
              if (!text && title) text = title;

              // For empty text, try to infer from href
              const href = el.getAttribute('href');
              if (!text && href) {{
                if (href.includes('cart') || href.includes('basket') || href.includes('корзин')) text = '[Cart/Корзина]';
                else if (href.includes('checkout')) text = '[Checkout]';
              }}

              // Get selector
              const testId = el.getAttribute('data-testid') || el.getAttribute('data-test-id');
              let selector = null;
              if (testId) {{
                selector = `testid:${{testId}}`;
              }} else if (text && text.length > 0 && !text.startsWith('[')) {{
                selector = `button:${{text.substring(0, 50)}}`;
              }} else if (ariaLabel) {{
                selector = `[aria-label="${{ariaLabel}}"]`;
              }} else {{
                const id = el.getAttribute('id');
                if (id) selector = `#${{id}}`;
              }}

              // Get class hints for debugging
              const classes = el.className;
              let classHints = null;
              if (classes && typeof classes === 'string') {{
                const parts = classes.split(/\\s+/).filter(c => c.length > 2).slice(0, 3);
                if (parts.length > 0) classHints = parts.join(' ');
              }}

              return {{ text: text || '[no text]', selector, classHints }};
            }}, handle);

            text = extracted.text;
            selector = extracted.selector;
            classHints = extracted.classHints;
          }}

          // Include element if it has selector OR text OR is a cart-like element
          const isCartLike = href && (href.includes('cart') || href.includes('basket') || href.includes('checkout'));
          if (selector || (text && text !== '[no text]') || isCartLike) {{
            const attrs = {{ type }};
            if (href) attrs.href = href.substring(0, 80);
            if (classHints && text === '[no text]') attrs.classHints = classHints;

            results.buttons.push({{
              type: 'button',
              text: text,
              selector: selector,
              attributes: attrs
            }});
          }}
        }} catch (e) {{
          // Skip problematic elements
        }}
      }}
      results.summary.buttons = results.buttons.length;
    }}

    // Discover inputs
    if (includeInputs) {{
      const inputs = targetPage.locator('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select');
      const count = await inputs.count();

      for (let i = 0; i < Math.min(count, limit); i++) {{
        try {{
          const el = inputs.nth(i);
          const isVisible = await el.isVisible().catch(() => false);
          if (!isVisible) continue;

          const tagName = await el.evaluate(e => e.tagName.toLowerCase()).catch(() => 'input');
          const inputType = await el.getAttribute('type').catch(() => 'text');
          const placeholder = await el.getAttribute('placeholder').catch(() => null);
          const name = await el.getAttribute('name').catch(() => null);
          const ariaLabel = await el.getAttribute('aria-label').catch(() => null);
          const id = await el.getAttribute('id').catch(() => null);

          // Try to find label
          let labelText = null;
          if (id) {{
            const label = await targetPage.locator(`label[for="${{id}}"]`).first().textContent().catch(() => null);
            if (label) labelText = cleanText(label);
          }}

          // Determine selector
          let selector = null;
          const handle = await el.elementHandle().catch(() => null);
          if (handle) {{
            selector = await targetPage.evaluate((el) => {{
              const testId = el.getAttribute('data-testid') || el.getAttribute('data-test-id');
              if (testId) return `testid:${{testId}}`;

              const placeholder = el.getAttribute('placeholder');
              if (placeholder) return `placeholder:${{placeholder}}`;

              const id = el.getAttribute('id');
              if (id) {{
                const label = document.querySelector(`label[for="${{id}}"]`);
                if (label) return `label:${{(label.textContent || '').trim().substring(0, 50)}}`;
              }}

              const ariaLabel = el.getAttribute('aria-label');
              if (ariaLabel) return `[aria-label="${{ariaLabel}}"]`;

              const name = el.getAttribute('name');
              if (name) return `[name="${{name}}"]`;

              if (id) return `#${{id}}`;

              return null;
            }}, handle);
          }}

          const displayName = labelText || placeholder || ariaLabel || name || `[${{tagName}}]`;

          if (selector || displayName !== `[${{tagName}}]`) {{
            results.inputs.push({{
              type: tagName === 'select' ? 'select' : (tagName === 'textarea' ? 'textarea' : 'input'),
              text: displayName,
              selector: selector,
              attributes: {{
                inputType: tagName === 'input' ? inputType : null,
                placeholder,
                name
              }}
            }});
          }}
        }} catch (e) {{
          // Skip problematic elements
        }}
      }}
      results.summary.inputs = results.inputs.length;
    }}

    // Discover links (optional, usually too many)
    if (includeLinks) {{
      const links = targetPage.locator('a[href]');
      const count = await links.count();

      for (let i = 0; i < Math.min(count, limit); i++) {{
        try {{
          const el = links.nth(i);
          const isVisible = await el.isVisible().catch(() => false);
          if (!isVisible) continue;

          const text = cleanText(await el.textContent().catch(() => ''));
          const href = await el.getAttribute('href').catch(() => null);

          if (text && text.length > 1) {{
            results.links.push({{
              type: 'link',
              text: text,
              selector: `link:${{text}}`,
              attributes: {{ href: href ? href.substring(0, 100) : null }}
            }});
          }}
        }} catch (e) {{
          // Skip problematic elements
        }}
      }}
      results.summary.links = results.links.length;
    }}

    return JSON.stringify({{
      success: true,
      elements: results,
      tip: 'Use the selector field with browser_click or browser_fill'
    }});
"""

    code = build_async_function(code_body, use_target_page=True)
    result = await BrowserExecutor.execute(code)

    try:
        parsed = json.loads(result)
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return json.dumps(
            {"success": False, "error": f"Invalid response: {result}"},
            ensure_ascii=False,
        )


@tool
async def browser_inspect_container(
    target: str,
    depth: int = 2,
    include_text: bool = True,
    max_children: int = 20,
) -> str:
    """
    Inspect DOM structure of a container to understand how data is organized.

    USE THIS TOOL when you need to extract data (like product names, prices, list items)
    but don't know the correct selectors. It shows the DOM tree structure with classes
    and text content, helping you find the right selectors for browser_get_text.

    Target formats:
    - CSS: ".cart-items", "#product-list", "[class*='Cart']"
    - Role: "list", "table"
    - Text: "text:Products"

    Args:
        target: Container selector to inspect
        depth: How deep to traverse children (default: 2, max: 4)
        include_text: Include text content of elements (default: True)
        max_children: Max children per element to show (default: 20)

    Returns:
        JSON with DOM structure showing:
        - tag: HTML tag name
        - classes: CSS classes (useful for selectors)
        - text: Text content (if include_text=True)
        - children: Nested child elements (up to depth)

    Example use case:
        1. browser_inspect_container(target="[class*='cart']", depth=2)
        2. See structure like: CartItem > ProductName (class="item-title")
        3. Use: browser_get_text(target=".item-title", all_matches=True)
    """
    from src.agent.tools._selectors import target_to_locator_js

    locator_js = target_to_locator_js(target, page_var="targetPage")
    depth = min(depth, 4)  # Cap depth to prevent huge outputs

    code_body = f"""
    const locator = {locator_js};
    const maxDepth = {depth};
    const includeText = {str(include_text).lower()};
    const maxChildren = {max_children};

    const count = await locator.count();

    if (count === 0) {{
      return JSON.stringify({{
        success: false,
        error: 'No elements found matching the selector',
        suggestion: 'Try a broader selector like "div", "[class*=\\'cart\\']", or use browser_explore_page first'
      }});
    }}

    function cleanText(text) {{
      if (!text) return '';
      return text
        .replace(/\\xAD/g, '')
        .replace(/[\\u200B-\\u200D\\uFEFF\\xA0]/g, ' ')
        .replace(/\\s+/g, ' ')
        .trim()
        .substring(0, 100);
    }}

    function getClassList(el) {{
      const classes = el.className;
      if (!classes || typeof classes !== 'string') return [];
      return classes.split(/\\s+/).filter(c => c.length > 0);
    }}

    function inspectElement(el, currentDepth) {{
      const tag = el.tagName.toLowerCase();
      const classes = getClassList(el);
      const id = el.id || null;

      const result = {{
        tag: tag,
      }};

      if (id) result.id = id;
      if (classes.length > 0) result.classes = classes;

      // Add useful attributes
      const href = el.getAttribute('href');
      const dataTestId = el.getAttribute('data-testid') || el.getAttribute('data-test-id');
      if (href) result.href = href.substring(0, 80);
      if (dataTestId) result.testId = dataTestId;

      // Add text content (direct text, not from children)
      if (includeText) {{
        // Get only direct text nodes
        let directText = '';
        for (const node of el.childNodes) {{
          if (node.nodeType === Node.TEXT_NODE) {{
            directText += node.textContent;
          }}
        }}
        directText = cleanText(directText);
        if (directText) result.text = directText;

        // Also get full innerText for leaf nodes
        if (el.children.length === 0) {{
          const fullText = cleanText(el.innerText);
          if (fullText && fullText !== directText) {{
            result.text = fullText;
          }}
        }}
      }}

      // Recurse into children
      if (currentDepth < maxDepth && el.children.length > 0) {{
        const children = [];
        const childCount = Math.min(el.children.length, maxChildren);
        for (let i = 0; i < childCount; i++) {{
          children.push(inspectElement(el.children[i], currentDepth + 1));
        }}
        if (children.length > 0) {{
          result.children = children;
          if (el.children.length > maxChildren) {{
            result.moreChildren = el.children.length - maxChildren;
          }}
        }}
      }} else if (el.children.length > 0) {{
        result.childCount = el.children.length;
      }}

      return result;
    }}

    // Inspect first matching element
    const handle = await locator.first().elementHandle();
    if (!handle) {{
      return JSON.stringify({{
        success: false,
        error: 'Could not get element handle'
      }});
    }}

    const structure = await targetPage.evaluate(
      ({{ el, maxDepth, includeText, maxChildren }}) => {{
        // Re-define functions inside evaluate context
        function cleanText(text) {{
          if (!text) return '';
          return text
            .replace(/\\xAD/g, '')
            .replace(/[\\u200B-\\u200D\\uFEFF\\xA0]/g, ' ')
            .replace(/\\s+/g, ' ')
            .trim()
            .substring(0, 100);
        }}

        function getClassList(el) {{
          const classes = el.className;
          if (!classes || typeof classes !== 'string') return [];
          return classes.split(/\\s+/).filter(c => c.length > 0);
        }}

        function inspectElement(el, currentDepth) {{
          const tag = el.tagName.toLowerCase();
          const classes = getClassList(el);
          const id = el.id || null;

          const result = {{ tag }};

          if (id) result.id = id;
          if (classes.length > 0) result.classes = classes;

          const href = el.getAttribute('href');
          const dataTestId = el.getAttribute('data-testid') || el.getAttribute('data-test-id');
          if (href) result.href = href.substring(0, 80);
          if (dataTestId) result.testId = dataTestId;

          if (includeText) {{
            let directText = '';
            for (const node of el.childNodes) {{
              if (node.nodeType === Node.TEXT_NODE) {{
                directText += node.textContent;
              }}
            }}
            directText = cleanText(directText);
            if (directText) result.text = directText;

            if (el.children.length === 0) {{
              const fullText = cleanText(el.innerText);
              if (fullText && fullText !== directText) {{
                result.text = fullText;
              }}
            }}
          }}

          if (currentDepth < maxDepth && el.children.length > 0) {{
            const children = [];
            const childCount = Math.min(el.children.length, maxChildren);
            for (let i = 0; i < childCount; i++) {{
              children.push(inspectElement(el.children[i], currentDepth + 1));
            }}
            if (children.length > 0) {{
              result.children = children;
              if (el.children.length > maxChildren) {{
                result.moreChildren = el.children.length - maxChildren;
              }}
            }}
          }} else if (el.children.length > 0) {{
            result.childCount = el.children.length;
          }}

          return result;
        }}

        return inspectElement(el, 0);
      }},
      {{ el: handle, maxDepth, includeText, maxChildren }}
    );

    return JSON.stringify({{
      success: true,
      matchCount: count,
      structure: structure,
      tip: 'Use class names from "classes" field to build selectors like ".className" or "[class*=\\'partial\\']"'
    }});
"""

    code = build_async_function(code_body, use_target_page=True)
    result = await BrowserExecutor.execute(code)

    try:
        parsed = json.loads(result)
        return json.dumps(parsed, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        return json.dumps(
            {"success": False, "error": f"Invalid response: {result}"},
            ensure_ascii=False,
        )
