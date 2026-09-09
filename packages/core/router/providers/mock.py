"""Mock Model Provider for deterministic offline testing and CI."""
import json
import re
from decimal import Decimal
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

from packages.core.router.interface import BaseModelProvider, ModelResponse


class MockModelProvider(BaseModelProvider):
    """Deterministic mock provider returning predefined or generated mock responses."""

    def __init__(self, predefined_response: Optional[str] = None):
        super().__init__(name="mock")
        self.predefined_response = predefined_response
        self.call_history = []

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> ModelResponse:
        self.call_history.append({"prompt": prompt, "schema": schema})

        if schema:
            # Generate a valid default model instance
            mock_data = {}
            for field_name, field_info in schema.model_fields.items():
                if field_info.annotation is str:
                    mock_data[field_name] = "mock_value"
                elif field_info.annotation is int:
                    mock_data[field_name] = 1
                elif field_info.annotation is bool:
                    mock_data[field_name] = True
                elif field_info.annotation is list:
                    mock_data[field_name] = []
                elif field_info.annotation is dict:
                    mock_data[field_name] = {}
                else:
                    mock_data[field_name] = None

            # If predefined response given, attempt to parse it
            if self.predefined_response:
                try:
                    mock_data = json.loads(self.predefined_response)
                except Exception:
                    pass

            validated_obj = schema.model_validate(mock_data)
            content = validated_obj.model_dump_json()
            return ModelResponse(
                content=content,
                structured_data=validated_obj.model_dump(),
                model=model_name or "mock-model",
                tokens_in=50,
                tokens_out=25,
                cost_usd=Decimal("0.000000"),
                latency_ms=10,
                provider="mock",
            )

        if self.predefined_response:
            content = self.predefined_response
        else:
            # Extract actual user text if prompt is formatted with template
            target_text = prompt
            if 'User says: "' in prompt:
                target_text = prompt.split('User says: "')[-1].split('"')[0]
            elif 'User Message: "' in prompt:
                target_text = prompt.split('User Message: "')[-1].split('"')[0]

            prompt_lower = target_text.lower()
            words = set(re.findall(r"\b\w+\b", prompt_lower))

            # Detect Devanagari Hindi or Hinglish keywords
            has_devanagari = any("\u0900" <= char <= "\u097F" for char in target_text)
            hinglish_keywords = {
                "kaise", "kaisa", "kaisi", "kya", "namaste", "namaskar", "kaho", "karo", "tum", "aap",
                "meri", "mera", "bhai", "hai", "bat", "baat", "bolo", "theek",
                "kaun", "dhanyawad", "madad", "aaj", "kuch", "shuru", "haan", "sun", "apna", "apni"
            }
            is_hindi = has_devanagari or bool(words.intersection(hinglish_keywords))

            if "prime minister" in prompt_lower and "india" in prompt_lower:
                content = "The Prime Minister of India is Narendra Modi." if not is_hindi else "भारत के माननीय प्रधानमंत्री श्री नरेंद्र मोदी हैं।"
            elif "president" in prompt_lower and "india" in prompt_lower:
                content = "The President of India is Droupadi Murmu." if not is_hindi else "भारत की माननीय राष्ट्रपति श्रीमती द्रौपदी मुर्मू हैं।"
            elif "capital" in prompt_lower and "india" in prompt_lower:
                content = "The capital of India is New Delhi." if not is_hindi else "भारत की राजधानी नई दिल्ली है।"
            elif is_hindi:
                # Check for capabilities / what can you do
                if any(kw in prompt_lower for kw in ["kya kar", "kya kya", "kaam kar", "capabilities", "kya kar skti", "kya karti ho", "features"]):
                    content = (
                        "नमस्ते! मैं Friday हूँ, आपका पर्सनल AI ऑपरेटिंग सिस्टम। मैं आपके लिए निम्नलिखित कार्य कर सकती हूँ:\n\n"
                        "1. 📧 ईमेल्स: महत्वपूर्ण ईमेल्स खोजना, सार प्रस्तुत करना और ड्राफ्ट तैयार करना।\n"
                        "2. 📅 कैलेंडर: आपकी दैनिक मीटिंग्स देखना और नए इवेंट्स शेड्यूल करना।\n"
                        "3. 📁 ड्राइव और फाइल्स: डॉक्युमेंट्स खोजना और मैनेज करना।\n"
                        "4. 📊 शीट्स: डेटा एंट्री और स्प्रेडशीट अपडेट्स।\n"
                        "5. 🌅 प्रोएक्टिव ब्रीफिंग: हर सुबह आपके पूरे दिन का शेड्यूल और ऑडियो ब्रीफिंग तैयार करना।\n\n"
                        "कहिए, आज मैं आपके लिए किस कार्य से शुरुआत करूँ?"
                    )
                elif any(w in words for w in ["kaun", "naam", "parichay"]) or "who are you" in prompt_lower:
                    content = "नमस्ते! मैं Friday हूँ, आपकी पर्सनल ऑटोनॉमस AI असिस्टेंट। मैं आपके दैनिक वर्कस्पेस टास्क्स, ईमेल्स, कैलेंडर और ऑटोमेशन को सुरक्षित और पेशेवर तरीके से संचालित करने के लिए डिज़ाइन की गई हूँ। कहिए, मैं आपकी क्या सेवा करूँ?"
                elif any(w in words for w in ["kaise", "kaisa", "kaisi", "hal", "haal"]):
                    content = "नमस्ते! मैं बिल्कुल ठीक हूँ, धन्यवाद। उम्मीद है आपका दिन भी शानदार बीत रहा होगा। कहिए, आज आपके किस काम में हाथ बंटाऊँ?"
                elif any(w in words for w in ["dhanyawad", "shukriya", "thanks"]):
                    content = "यह तो मेरा सौभाग्य है! यदि आपको किसी अन्य कार्य में सहायता चाहिए, तो निसंकोच बताइए।"
                else:
                    content = (
                        "नमस्ते! मैं वर्तमान में ऑफलाइन डेमो मोड में संचालित हो रही हूँ। "
                        "ChatGPT या Gemini जैसी किसी भी विषय पर असीमित बुद्धिमत्ता के लिए, कृपया अपनी फ्री Google Gemini API Key `.env` फाइल में दर्ज करें। "
                        "तब तक आप मुझे सीधे अपने ईमेल्स, कैलेंडर या वर्कस्पेस टास्क एक्ज़ीक्यूट करने के निर्देश दे सकते हैं।"
                    )
            else:
                if any(kw in prompt_lower for kw in ["what can you do", "features", "capabilities", "what do you do"]):
                    content = (
                        "Hello! I am Friday, your personal AI operating system. Here is what I can autonomously handle for you:\n\n"
                        "1. 📧 Email: Search unread emails, triage priority messages, and create verified drafts.\n"
                        "2. 📅 Calendar: Inspect your daily agenda and schedule new events seamlessly.\n"
                        "3. 📁 Drive: Search and manage documents with post-condition verification.\n"
                        "4. 📊 Sheets: Read and append tabular records with re-read validation.\n"
                        "5. 🌅 Proactive Loop: Deliver automated morning briefings and advance meeting reminders.\n\n"
                        "How may I assist you today?"
                    )
                elif "who are you" in prompt_lower or "your name" in prompt_lower:
                    content = "Hello! I am Friday, your personal autonomous AI operating system assistant. All systems and security policies are active and operational. How may I assist you?"
                elif any(w in words for w in ["hello", "hi", "hey"]):
                    content = "Good day! All systems are online. How may I assist you with your workspace tasks today?"
                else:
                    content = (
                        "I am currently running in offline fallback mode. "
                        "To unlock full dynamic general intelligence (answering any question like ChatGPT/Claude), please paste your free Google Gemini API key into the .env file!"
                    )
        return ModelResponse(
            content=content,
            structured_data=None,
            model=model_name or "mock-model",
            tokens_in=40,
            tokens_out=20,
            cost_usd=Decimal("0.000000"),
            latency_ms=10,
            provider="mock",
        )

