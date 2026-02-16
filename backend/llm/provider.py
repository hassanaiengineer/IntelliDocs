# backend/llm/provider.py - Enhanced LLM Provider System
import json
from xml.parsers.expat import model
import requests
from typing import Dict, Any, Optional, Tuple
from backend.core.config import get_settings

settings = get_settings()

class LLMProvider:
    """Enhanced LLM provider with optimized prompts"""
    
    @staticmethod
    def create_enhanced_prompt(question: str, context: str, sources_info: list = None) -> str:
        """Create optimized prompt for RAG responses"""
        
        # Count source files for context
        source_files = set()
        if sources_info:
            source_files = {source.get("filename", "Unknown") for source in sources_info}
        
        source_context = ""
        if source_files:
            file_list = ", ".join(source_files)
            source_context = f"Based on information from: {file_list}\n\n"
        
        prompt = f"""You are an intelligent document assistant. Your task is to provide accurate, helpful answers based on the provided document context.

{source_context}Context from documents:
{context}

User Question: {question}

Instructions:
1. Answer the question directly and comprehensively using ONLY information from the provided context
2. If the context contains relevant information, provide a detailed answer
3. If the answer spans multiple documents, clearly indicate which information comes from which source
4. If the context doesn't contain sufficient information to answer the question, clearly state this
5. Use a natural, conversational tone while being precise and informative
6. When referencing specific information, you may mention the source document name
7. Provide practical insights when relevant

Answer:"""
        
        return prompt
    
    @staticmethod
    def validate_api_key(provider: str, api_key: str) -> Tuple[bool, str]:
        """Validate API key for supported providers"""
        if not api_key or not api_key.strip():
            return False, "API key is required"
        
        provider = provider.lower()
        
        if provider == "openai":
            return LLMProvider._validate_openai_key(api_key)
        elif provider == "anthropic":
            return LLMProvider._validate_anthropic_key(api_key)
        elif provider == "gemini":
            return LLMProvider._validate_gemini_key(api_key)
        else:
            return False, f"Unsupported provider: {provider}"
    
    @staticmethod
    def _validate_openai_key(api_key: str) -> Tuple[bool, str]:
        """Validate OpenAI API key"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "OpenAI API key is valid"
            elif response.status_code == 401:
                return False, "Invalid OpenAI API key"
            else:
                return False, f"API validation failed: {response.status_code}"
                
        except requests.RequestException as e:
            return False, f"Network error during validation: {str(e)}"
    
    @staticmethod
    def _validate_anthropic_key(api_key: str) -> Tuple[bool, str]:
        """Validate Anthropic API key"""
        try:
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Use a minimal completion request to test
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=15
            )
            
            if response.status_code == 200:
                return True, "Anthropic API key is valid"
            elif response.status_code == 401:
                return False, "Invalid Anthropic API key"
            else:
                return False, f"API validation failed: {response.status_code}"
                
        except requests.RequestException as e:
            return False, f"Network error during validation: {str(e)}"
    
    @staticmethod
    def _validate_gemini_key(api_key: str) -> Tuple[bool, str]:
        """Validate Gemini API key"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return True, "Gemini API key is valid"
            elif response.status_code == 400:
                return False, "Invalid Gemini API key"
            else:
                return False, f"API validation failed: {response.status_code}"
                
        except requests.RequestException as e:
            return False, f"Network error during validation: {str(e)}"
    
    @staticmethod
    def generate_answer(provider: str, api_key: str, question: str, context: str, sources_info: list = None) -> str:
        """Generate answer using specified LLM provider"""
        provider = provider.lower()
        
        if provider == "openai":
            return LLMProvider._generate_openai_answer(api_key, question, context, sources_info)
        elif provider == "anthropic":
            return LLMProvider._generate_anthropic_answer(api_key, question, context, sources_info)
        elif provider == "gemini":
            return LLMProvider._generate_gemini_answer(api_key, question, context, sources_info)
        else:
            return f"Unsupported provider: {provider}"
    
    @staticmethod
    def _generate_openai_answer(api_key: str, question: str, context: str, sources_info: list = None) -> str:
        """Generate answer using OpenAI"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = LLMProvider.create_enhanced_prompt(question, context, sources_info)
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided document context."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000,
                "temperature": 0.3
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                return f"OpenAI API error: {response.status_code} - {response.text}"
                
        except requests.RequestException as e:
            return f"Network error: {str(e)}"
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    @staticmethod
    def _generate_anthropic_answer(api_key: str, question: str, context: str, sources_info: list = None) -> str:
        """Generate answer using Anthropic Claude"""
        try:
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            prompt = LLMProvider.create_enhanced_prompt(question, context, sources_info)
            
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["content"][0]["text"].strip()
            else:
                return f"Anthropic API error: {response.status_code} - {response.text}"
                
        except requests.RequestException as e:
            return f"Network error: {str(e)}"
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    @staticmethod
    def _generate_gemini_answer(api_key: str, question: str, context: str, sources_info: list = None) -> str:
        """Generate answer using Google Gemini"""
        try:
            model = "gemini-2.0-flash"   # or gemini-1.5-pro / 2.0-pro
            url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}"

            
            prompt = LLMProvider.create_enhanced_prompt(question, context, sources_info)
            
            data = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 1000,
                }
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                return f"Gemini API error: {response.status_code} - {response.text}"
                
        except requests.RequestException as e:
            return f"Network error: {str(e)}"
        except Exception as e:
            return f"Error generating answer: {str(e)}"

def normalize_provider(provider: str) -> str:
    """Normalize provider name"""
    provider = provider.lower().strip()
    if provider in ["openai", "gpt", "chatgpt"]:
        return "openai"
    elif provider in ["anthropic", "claude"]:
        return "anthropic"
    elif provider in ["gemini", "google", "bard"]:
        return "gemini"
    else:
        return settings.DEFAULT_PROVIDER

# Convenience functions for backward compatibility
def validate_api_key(provider: str, api_key: str) -> Tuple[bool, str]:
    """Legacy function"""
    return LLMProvider.validate_api_key(provider, api_key)

def generate_answer(provider: str, api_key: str, question: str, context: str) -> str:
    """Legacy function"""
    return LLMProvider.generate_answer(provider, api_key, question, context)
