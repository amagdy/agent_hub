import os

def read_file(file_path: str, start: int = 0, end: int | None = None) -> str:
    """
    {
        "description": "Read the contents of a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read."
                },
                "start": {
                    "type": "integer",
                    "description": "The starting character position to read from (default is 0)."
                },
                "end": {
                    "type": ["integer", "null"],
                    "description": "The ending character position to read to (default is None, which reads to the end of the file)."
                }
            },
            "required": ["file_path"]
        }
    }
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        if start != 0 or end is not None:
            end = end if end is not None else len(content)
            content = content[start:end]
        return content

def write_file(file_path: str, content: str) -> None:
    """
    {
        "description": "Write the given content to a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to write."
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file."
                }
            },
            "required": ["file_path", "content"]
        }
    }
    """
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def list_files_in_directory(directory_path: str) -> list[str]:
    """
    {
        "description": "List all files in the given directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "The path to the directory to list files from."
                }
            },
            "required": ["directory_path"]
        }
    }
    """
    return [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]

def get_file_size(file_path: str) -> int:
    """
    {
        "description": "Get the size of a file in bytes.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to get the size of."
                }
            },
            "required": ["file_path"]
        }
    }
    """
    return os.path.getsize(file_path)

