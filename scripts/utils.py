def fillna_text(s):
    try:
        return s.fillna("")
    except Exception:
        return s