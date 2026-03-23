import os
import re
from pathlib import Path
from urllib.parse import urlparse, unquote


def ensure_dir(path: str | Path) -> Path:
    path = Path(path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    return path


def get_unique_filename(directory: str | Path, filename: str) -> str:
    directory = Path(directory)
    ensure_dir(directory)
    
    name, ext = os.path.splitext(filename)
    counter = 1
    final_filename = filename
    
    while (directory / final_filename).exists():
        final_filename = f"{name}_{counter}{ext}"
        counter += 1
    
    return final_filename


def sanitize_filename(filename: str) -> str:
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, '_', filename)
    sanitized = sanitized.strip()
    sanitized = re.sub(r'\.{2,}', '.', sanitized)
    
    if not sanitized:
        sanitized = "unnamed"
    
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        name = name[:max_length - len(ext)]
        sanitized = name + ext
    
    return sanitized


def get_file_extension(url: str) -> str:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    
    filename = os.path.basename(path)
    
    if '.' in filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext and len(ext) <= 10:
            return ext
    
    query = parsed.query.lower()
    if 'format=' in query:
        match = re.search(r'format=(\w+)', query)
        if match:
            return f".{match.group(1)}"
    
    if 'video' in url.lower() or 'mp4' in url.lower():
        return '.mp4'
    elif 'image' in url.lower() or 'jpg' in url.lower() or 'jpeg' in url.lower():
        return '.jpg'
    elif 'png' in url.lower():
        return '.png'
    elif 'gif' in url.lower():
        return '.gif'
    
    return '.bin'


def format_file_size(size_bytes: int | float) -> str:
    if size_bytes < 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"


def get_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = os.path.basename(path)
    
    if not filename or filename == '/':
        filename = "download"
    
    return sanitize_filename(filename)


def get_content_type(extension: str) -> str:
    extension = extension.lower().lstrip('.')
    
    content_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'mov': 'video/quicktime',
        'avi': 'video/x-msvideo',
        'mkv': 'video/x-matroska',
    }
    
    return content_types.get(extension, 'application/octet-stream')


def is_media_file(extension: str) -> bool:
    extension = extension.lower().lstrip('.')
    
    media_extensions = {
        'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg',
        'mp4', 'webm', 'mov', 'avi', 'mkv', 'flv', 'wmv',
        'mp3', 'wav', 'ogg', 'flac', 'aac',
    }
    
    return extension in media_extensions
