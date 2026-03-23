import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.exceptions import TelegramAPIException


class TDLService:
    def __init__(self, tdl_path: str | None = None, config_path: str | None = None):
        self.tdl_path = tdl_path or settings.TDL_PATH
        self.config_path = config_path or os.path.join(settings.DOWNLOAD_DIR, "tdl")
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        config_dir = Path(self.config_path)
        config_dir.mkdir(parents=True, exist_ok=True)

    async def configure(self, api_id: int, api_hash: str, phone: str) -> dict[str, Any]:
        config_data = {
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone,
        }
        
        config_file = os.path.join(self.config_path, "config.json")
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        
        return {
            "success": True,
            "message": "TDL配置已保存",
            "config_path": config_file,
        }

    async def login(self) -> dict[str, Any]:
        result = await self._run_tdl_command(["login"])
        return result

    async def check_login_status(self) -> dict[str, Any]:
        try:
            result = await self._run_tdl_command(["chat", "ls"])
            if result.get("success"):
                return {
                    "logged_in": True,
                    "message": "已登录Telegram",
                }
            return {
                "logged_in": False,
                "message": "未登录或登录已过期",
            }
        except Exception:
            return {
                "logged_in": False,
                "message": "未登录或登录已过期",
            }

    async def upload_file(
        self,
        file_path: str,
        chat_id: str,
        caption: str | None = None,
    ) -> dict[str, Any]:
        if not os.path.exists(file_path):
            raise TelegramAPIException(message=f"文件不存在: {file_path}")
        
        file_size = os.path.getsize(file_path)
        max_size = 2 * 1024 * 1024 * 1024
        if file_size > max_size:
            raise TelegramAPIException(
                message=f"文件大小超过限制 (2GB): {file_path}"
            )
        
        args = ["upload", "-p", file_path, "-c", chat_id]
        
        if caption:
            caption_file = os.path.join(self.config_path, "caption.txt")
            with open(caption_file, "w", encoding="utf-8") as f:
                f.write(caption)
            args.extend(["--caption", caption_file])
        
        result = await self._run_tdl_command(args, timeout=600)
        
        if result.get("success"):
            return {
                "success": True,
                "message": "文件上传成功",
                "file_path": file_path,
                "chat_id": chat_id,
            }
        
        raise TelegramAPIException(
            message=result.get("error", "文件上传失败"),
            details=result,
        )

    async def upload_files(
        self,
        file_paths: list[str],
        chat_id: str,
        captions: list[str] | None = None,
    ) -> dict[str, Any]:
        results = []
        success_count = 0
        failed_count = 0
        
        for i, file_path in enumerate(file_paths):
            caption = None
            if captions and i < len(captions):
                caption = captions[i]
            
            try:
                result = await self.upload_file(file_path, chat_id, caption)
                results.append({
                    "file_path": file_path,
                    "success": True,
                    "message": result.get("message"),
                })
                success_count += 1
            except Exception as e:
                results.append({
                    "file_path": file_path,
                    "success": False,
                    "error": str(e),
                })
                failed_count += 1
        
        return {
            "success": failed_count == 0,
            "message": f"上传完成: {success_count}成功, {failed_count}失败",
            "total": len(file_paths),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
        }

    async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
        result = await self._run_tdl_command(["chat", "info", "-c", chat_id])
        
        if result.get("success"):
            return {
                "success": True,
                "chat_id": chat_id,
                "data": result.get("data"),
            }
        
        raise TelegramAPIException(
            message="获取聊天信息失败",
            details=result,
        )

    async def get_me(self) -> dict[str, Any]:
        result = await self._run_tdl_command(["chat", "me"])
        
        if result.get("success"):
            return {
                "success": True,
                "data": result.get("data"),
            }
        
        raise TelegramAPIException(
            message="获取用户信息失败",
            details=result,
        )

    async def _run_tdl_command(
        self,
        args: list[str],
        timeout: int = 300,
    ) -> dict[str, Any]:
        if not shutil.which(self.tdl_path) and not os.path.exists(self.tdl_path):
            raise TelegramAPIException(
                message=f"TDL可执行文件不存在: {self.tdl_path}"
            )
        
        cmd = [self.tdl_path] + args
        
        env = os.environ.copy()
        env["TDL_HOME"] = self.config_path
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self.config_path,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TelegramAPIException(
                    message=f"TDL命令执行超时 ({timeout}秒)",
                    details={"args": args},
                )
            
            stdout_str = stdout.decode("utf-8", errors="ignore")
            stderr_str = stderr.decode("utf-8", errors="ignore")
            
            if process.returncode == 0:
                data = None
                try:
                    if stdout_str.strip():
                        data = json.loads(stdout_str)
                except json.JSONDecodeError:
                    pass
                
                return {
                    "success": True,
                    "returncode": process.returncode,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "data": data,
                }
            
            return {
                "success": False,
                "returncode": process.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "error": stderr_str or stdout_str or "未知错误",
            }
            
        except FileNotFoundError:
            raise TelegramAPIException(
                message=f"TDL可执行文件不存在: {self.tdl_path}"
            )
        except Exception as e:
            raise TelegramAPIException(
                message=f"TDL命令执行失败: {str(e)}",
                details={"args": args, "error": str(e)},
            )

    async def get_chats(self, limit: int = 50) -> dict[str, Any]:
        result = await self._run_tdl_command(["chat", "ls", "-n", str(limit)])
        
        if result.get("success"):
            return {
                "success": True,
                "chats": result.get("data", []),
            }
        
        raise TelegramAPIException(
            message="获取聊天列表失败",
            details=result,
        )

    async def logout(self) -> dict[str, Any]:
        result = await self._run_tdl_command(["logout"])
        
        if result.get("success"):
            return {
                "success": True,
                "message": "已退出登录",
            }
        
        raise TelegramAPIException(
            message="退出登录失败",
            details=result,
        )
