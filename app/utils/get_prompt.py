def read_from_txt_path(txt_path: str):
    with open(txt_path, "r", encoding="utf-8") as file:
        return file.read()