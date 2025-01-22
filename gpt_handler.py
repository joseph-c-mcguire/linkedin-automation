import openai
from typing import Dict
import logging


class GPTHandler:
    def __init__(self, api_key: str, resume_content: str):
        openai.api_key = api_key
        self.resume_content = resume_content
        self.logger = logging.getLogger("linkedin_bot")

    def generate_response(self, question: str, context: str = "") -> str:
        try:
            prompt = f"""
            Based on my resume: {self.resume_content}
            
            And this additional context: {context}
            
            Please provide a professional response to this question: {question}
            
            Keep the response concise, professional, and relevant to my experience.
            """

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant creating job application responses.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"Error generating GPT response: {str(e)}")
            return ""
