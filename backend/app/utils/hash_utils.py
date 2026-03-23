import hashlib
from collections.abc import AsyncGenerator
from typing import BinaryIO


SUPPORTED_ALGORITHMS = {
    'md5': hashlib.md5,
    'sha1': hashlib.sha1,
    'sha256': hashlib.sha256,
    'sha512': hashlib.sha512,
}


def calculate_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"不支持的哈希算法: {algorithm}。支持的算法: {list(SUPPORTED_ALGORITHMS.keys())}")
    
    hash_func = SUPPORTED_ALGORITHMS[algorithm]()
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def calculate_bytes_hash(data: bytes, algorithm: str = 'sha256') -> str:
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"不支持的哈希算法: {algorithm}。支持的算法: {list(SUPPORTED_ALGORITHMS.keys())}")
    
    hash_func = SUPPORTED_ALGORITHMS[algorithm]()
    hash_func.update(data)
    
    return hash_func.hexdigest()


def calculate_stream_hash(stream: BinaryIO, algorithm: str = 'sha256') -> str:
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"不支持的哈希算法: {algorithm}。支持的算法: {list(SUPPORTED_ALGORITHMS.keys())}")
    
    hash_func = SUPPORTED_ALGORITHMS[algorithm]()
    
    original_position = stream.tell()
    stream.seek(0)
    
    try:
        while chunk := stream.read(8192):
            hash_func.update(chunk)
    finally:
        stream.seek(original_position)
    
    return hash_func.hexdigest()


async def calculate_file_hash_async(file_path: str, algorithm: str = 'sha256') -> str:
    import aiofiles
    
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"不支持的哈希算法: {algorithm}。支持的算法: {list(SUPPORTED_ALGORITHMS.keys())}")
    
    hash_func = SUPPORTED_ALGORITHMS[algorithm]()
    
    async with aiofiles.open(file_path, 'rb') as f:
        while True:
            chunk = await f.read(8192)
            if not chunk:
                break
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


async def calculate_async_stream_hash(
    stream: AsyncGenerator[bytes, None],
    algorithm: str = 'sha256'
) -> str:
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"不支持的哈希算法: {algorithm}。支持的算法: {list(SUPPORTED_ALGORITHMS.keys())}")
    
    hash_func = SUPPORTED_ALGORITHMS[algorithm]()
    
    async for chunk in stream:
        hash_func.update(chunk)
    
    return hash_func.hexdigest()


def verify_hash(data: bytes | str, expected_hash: str, algorithm: str = 'sha256') -> bool:
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    actual_hash = calculate_bytes_hash(data, algorithm)
    return actual_hash.lower() == expected_hash.lower()


def verify_file_hash(file_path: str, expected_hash: str, algorithm: str = 'sha256') -> bool:
    actual_hash = calculate_file_hash(file_path, algorithm)
    return actual_hash.lower() == expected_hash.lower()
