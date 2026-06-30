

def get_trunc_text(text:str, max_length:int=100) -> str:
    """Truncate text to the given number of characters, adding ellipsis if necessary."""
    if len(text) > max_length:
        return text[:max_length-2] + ".."
    return text