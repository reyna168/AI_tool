"""LLM 介面 - 支援 OpenAI 與 Ollama"""

from rag.config import RAGConfig


class LLMClient:
    """統一的 LLM 客戶端"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self._provider = config.llm_provider

        if self._provider == "openai":
            self._init_openai()
        elif self._provider == "ollama":
            self._init_ollama()
        else:
            raise ValueError(f"不支援的 LLM provider: {self._provider}")

    def _init_openai(self):
        from openai import OpenAI

        self._client = OpenAI(api_key=self.config.openai_api_key)

    def _init_ollama(self):
        import ollama

        self._client = ollama

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """發送對話請求"""
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        if self._provider == "openai":
            return self._chat_openai(system_prompt, user_prompt, temp, tokens)
        else:
            return self._chat_ollama(system_prompt, user_prompt, temp)

    def _chat_openai(
        self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int
    ) -> str:
        response = self._client.chat.completions.create(
            model=self.config.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _chat_ollama(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        response = self._client.chat(
            model=self.config.ollama_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": temperature},
        )
        return response["message"]["content"]

    def stream_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """串流回應"""
        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        if self._provider == "openai":
            yield from self._stream_openai(system_prompt, user_prompt, temp, tokens)
        else:
            yield from self._stream_ollama(system_prompt, user_prompt, temp)

    def _stream_openai(
        self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int
    ):
        stream = self._client.chat.completions.create(
            model=self.config.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _stream_ollama(self, system_prompt: str, user_prompt: str, temperature: float):
        stream = self._client.chat(
            model=self.config.ollama_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": temperature},
            stream=True,
        )
        for chunk in stream:
            if chunk["message"]["content"]:
                yield chunk["message"]["content"]
