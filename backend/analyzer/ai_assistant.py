import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any

class AILogAnalyzer:
    def __init__(self):
        pass
        
    def analyze(self, provider: str, model: str, api_key: str, context: str, query: str = None) -> str:
        """
        Routes the analysis request to the appropriate AI provider.
        """
        if not api_key:
            return "> [!CRITICAL]\n> **Missing API Key**\n> Please provide a valid API key in the configuration."
            
        system_prompt = (
            "You are an expert enterprise software diagnostic engineer specializing in root cause analysis (RCA) "
            "for distributed systems, microservices, and databases (including Redis/Sentinel and Magic Software). "
            "Your task is to analyze the provided log trace or offline RCA report and provide a deep, highly technical, "
            "and actionable root cause analysis."
        )
        
        user_prompt = f"Here is the context data:\n\n{context}"
        if query:
            user_prompt += f"\n\nUser Question/Instruction:\n{query}"
        else:
            user_prompt += "\n\nPlease provide a comprehensive deep-dive analysis, explain what went wrong, and suggest exact remediation steps."

        try:
            if provider == "openai":
                return self._call_openai(api_key, model, system_prompt, user_prompt)
            elif provider == "claude":
                return self._call_anthropic(api_key, model, system_prompt, user_prompt)
            elif provider == "gemini":
                return self._call_gemini(api_key, model, system_prompt, user_prompt)
            elif provider == "microsoft":
                return self._call_azure(api_key, model, system_prompt, user_prompt)
            else:
                return f"> [!WARNING]\n> **Unsupported Provider**: {provider}"
        except Exception as e:
            return f"> [!CRITICAL]\n> **AI Analysis Failed**\n> Error: {str(e)}"

    def _call_openai(self, api_key: str, model: str, system_prompt: str, user_prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        return self._make_request(url, headers, data, lambda resp: resp["choices"][0]["message"]["content"])

    def _call_anthropic(self, api_key: str, model: str, system_prompt: str, user_prompt: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": model,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 4096,
            "temperature": 0.2
        }
        return self._make_request(url, headers, data, lambda resp: resp["content"][0]["text"])

    def _call_gemini(self, api_key: str, model: str, system_prompt: str, user_prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"System: {system_prompt}\n\nUser: {user_prompt}"}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2
            }
        }
        return self._make_request(url, headers, data, lambda resp: resp["candidates"][0]["content"]["parts"][0]["text"])
        
    def _call_azure(self, api_key: str, endpoint_url: str, system_prompt: str, user_prompt: str) -> str:
        # For Microsoft Azure OpenAI, the user must provide the full endpoint URL as the "model" string in the UI
        # e.g., https://<resource>.openai.azure.com/openai/deployments/<deployment>/chat/completions?api-version=2024-02-15-preview
        if not endpoint_url.startswith("http"):
            return "> [!WARNING]\n> For Microsoft Co-Pilot (Azure OpenAI), please enter the full Endpoint URL as the Model name."
            
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        data = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        return self._make_request(endpoint_url, headers, data, lambda resp: resp["choices"][0]["message"]["content"])

    def _make_request(self, url: str, headers: Dict, data: Dict, extractor) -> str:
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers=headers,
            method='POST'
        )
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return extractor(result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {error_body}")
        except Exception as e:
            raise Exception(str(e))
