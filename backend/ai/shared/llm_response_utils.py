# ai/shared/llm_response_utils.py

def extract_llm_text(response) -> str:
    """
    Extracts the actual text output from an LLM response.

    GPT-4o-style responses usually return response.content as a plain string.
    GPT-5-style responses can return response.content as a list of blocks,
    such as reasoning blocks and text blocks. For JSON parsing, we only want
    the text block content and should ignore reasoning/metadata blocks.
    """
    content = response.content

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if text:
                    text_parts.append(text)

        if text_parts:
            return "\n".join(text_parts)

    raise ValueError(f"Unable to extract text from LLM response: {content!r}")
