"""A cutting tool's titles (tooling.model.tool_titles) as the screens read
them from its view, ``titleParts``: ToolTitles.js colours the parts."""

from teachinlathe.tooling.model.tool_titles import card_title_parts, list_title, list_title_parts


def title_parts(tool) -> dict:
    """{"card": [{text, role}], "list": [{text, role}], "text": the list's
    title as plain text}."""
    def parts(titles):
        return [{"text": part.text, "role": part.role} for part in titles]
    return {"card": parts(card_title_parts(tool)), "list": parts(list_title_parts(tool)),
            "text": list_title(tool)}
