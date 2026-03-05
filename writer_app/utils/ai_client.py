import json
import logging
import re
import time
from typing import Optional, Tuple, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from writer_app.core.exceptions import (
    AIServiceError,
    AIConnectionError,
    AITimeoutError,
    AIResponseError,
    AIConfigError
)

logger = logging.getLogger(__name__)


class AIClient:
    """
    处理与本地 LM Studio 或 OpenAI 兼容 API 的交互。

    特性:
    - 自动重试（可配置）
    - 指数退避
    - 连接池复用
    - 详细错误分类
    """

    # 默认重试配置
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_FACTOR = 0.5  # 0.5, 1.0, 2.0 秒
    DEFAULT_TIMEOUT = 120

    def __init__(self, max_retries: int = None, backoff_factor: float = None):
        """
        初始化 AI 客户端。

        Args:
            max_retries: 最大重试次数（默认 3）
            backoff_factor: 指数退避因子（默认 0.5）
        """
        self.max_retries = max_retries or self.DEFAULT_MAX_RETRIES
        self.backoff_factor = backoff_factor or self.DEFAULT_BACKOFF_FACTOR

        # 创建带重试的 Session
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """创建带有重试策略的 HTTP Session。"""
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
            raise_on_status=False
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def call_lm_studio_with_prompts(
        self,
        api_url: str,
        model: str,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = None
    ) -> str:
        """
        向 LM Studio API 发送请求。

        Args:
            api_url: API 端点 URL
            model: 模型名称
            api_key: API 密钥（可选）
            system_prompt: 系统提示
            user_prompt: 用户提示
            temperature: 温度参数
            max_tokens: 最大令牌数
            timeout: 超时时间（秒）

        Returns:
            模型生成的文本内容

        Raises:
            AIConfigError: 配置错误
            AIConnectionError: 连接错误
            AITimeoutError: 超时错误
            AIResponseError: 响应解析错误
        """
        if not api_url or not model:
            raise AIConfigError("请配置 API URL 和模型名称")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        request_timeout = timeout or self.DEFAULT_TIMEOUT
        start_time = time.time()

        try:
            response = self._session.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=request_timeout
            )

            elapsed = time.time() - start_time
            logger.debug(f"AI 请求完成，耗时 {elapsed:.2f}s，状态码 {response.status_code}")

            # 检查 HTTP 错误
            if response.status_code >= 500:
                raise AIConnectionError(
                    f"服务器错误 (HTTP {response.status_code})",
                    cause=Exception(response.text[:500])
                )
            elif response.status_code == 429:
                raise AIConnectionError(
                    "请求过于频繁，请稍后重试",
                    cause=Exception("Rate limited")
                )
            elif response.status_code >= 400:
                raise AIResponseError(
                    f"请求错误 (HTTP {response.status_code})",
                    response_text=response.text[:500]
                )

            response.raise_for_status()
            data = response.json()

        except requests.exceptions.Timeout as e:
            raise AITimeoutError(
                f"请求超时（{request_timeout}秒）",
                timeout=request_timeout,
                cause=e
            )
        except requests.exceptions.ConnectionError as e:
            raise AIConnectionError(
                f"无法连接到 AI 服务: {api_url}",
                cause=e
            )
        except requests.exceptions.RequestException as e:
            raise AIServiceError(
                f"请求失败: {str(e)}",
                cause=e,
                retryable=True
            )
        except json.JSONDecodeError as e:
            raise AIResponseError(
                "无法解析 AI 响应",
                response_text=response.text[:500] if 'response' in locals() else None,
                cause=e
            )

        # 解析响应
        choices = data.get("choices")
        if not choices:
            raise AIResponseError(
                "AI 未返回有效内容",
                response_text=str(data)[:500]
            )

        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise AIResponseError(
                "AI 返回空内容",
                response_text=str(choices[0])[:500]
            )

        return content

    def call_with_retry(
        self,
        api_url: str,
        model: str,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = None,
        **kwargs
    ) -> str:
        """
        带手动重试的 API 调用（用于需要自定义重试逻辑的场景）。

        Args:
            max_retries: 最大重试次数
            **kwargs: 传递给 call_lm_studio_with_prompts 的其他参数

        Returns:
            模型生成的文本内容
        """
        retries = max_retries or self.max_retries
        last_error = None

        for attempt in range(retries + 1):
            try:
                return self.call_lm_studio_with_prompts(
                    api_url, model, api_key, system_prompt, user_prompt, **kwargs
                )
            except AIServiceError as e:
                last_error = e
                if not e.retryable or attempt >= retries:
                    raise

                wait_time = self.backoff_factor * (2 ** attempt)
                logger.warning(f"AI 请求失败，{wait_time:.1f}秒后重试 (尝试 {attempt + 1}/{retries}): {e}")
                time.sleep(wait_time)

        raise last_error

    @staticmethod
    def extract_json_from_text(text):
        """Extract JSON object or array from text, handling markdown code blocks and common errors."""
        if not text:
            return None

        decoder = json.JSONDecoder()

        def try_parse(candidate):
            if not candidate:
                return None

            for idx, ch in enumerate(candidate):
                if ch not in "[{":
                    continue
                snippet = candidate[idx:]
                for attempt in (snippet, re.sub(r",\s*([\]}])", r"\1", snippet)):
                    try:
                        obj, _ = decoder.raw_decode(attempt)
                        return obj
                    except Exception:
                        continue
            return None

        def iter_candidates(raw):
            fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if fenced:
                for block in fenced:
                    yield block.strip()
            yield raw.strip()

        for candidate in iter_candidates(text):
            result = try_parse(candidate)
            if result is not None:
                return result

        return None

    def test_connection(self, api_url: str, model: str, api_key: str = "") -> Tuple[bool, str]:
        """
        执行轻量级请求以验证 AI 服务是否可达。

        Args:
            api_url: API 端点 URL
            model: 模型名称
            api_key: API 密钥（可选）

        Returns:
            (成功标志, 消息)
        """
        if not api_url or not model:
            return False, "请先填写接口URL和模型名称。"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
            "temperature": 0.0
        }
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        start = time.time()
        try:
            resp = self._session.post(api_url, json=payload, headers=headers, timeout=15)
            latency_ms = int((time.time() - start) * 1000)

            if resp.status_code == 401:
                return False, "认证失败，请检查 API 密钥。"
            elif resp.status_code == 404:
                return False, "接口地址不正确或模型不存在。"
            elif resp.status_code >= 500:
                return False, f"服务器错误 (HTTP {resp.status_code})。"

            resp.raise_for_status()
            data = resp.json()

            if not data.get("choices"):
                return False, "接口响应成功，但未返回 choices 字段。"

            return True, f"连接成功，延迟约 {latency_ms} ms。"

        except requests.exceptions.Timeout:
            return False, "连接超时，请检查网络或服务状态。"
        except requests.exceptions.ConnectionError:
            return False, f"无法连接到 {api_url}，请检查地址是否正确。"
        except Exception as exc:
            logger.warning("AI connection test failed: %s", exc)
            return False, f"连接失败: {exc}"

    def close(self):
        """关闭 HTTP 会话，释放连接池资源。"""
        if self._session:
            self._session.close()
            logger.debug("AI 客户端会话已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
