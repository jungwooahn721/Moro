"""
멀티미디어 입력을 LLM으로 전처리하는 모듈
음성, 이미지 등을 텍스트로 변환하여 에이전트가 이해할 수 있게 처리
"""
import os
import base64
import io
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class MultimediaProcessor:
    def __init__(self):
        """멀티미디어 전처리기 초기화"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def process_audio(self, audio_data: bytes, audio_format: str = "webm") -> Dict[str, Any]:
        """
        음성 데이터를 텍스트로 변환
        
        Args:
            audio_data: 음성 파일 바이트 데이터
            audio_format: 음성 파일 형식 (webm, mp3, wav 등)
        
        Returns:
            Dict: 처리 결과
        """
        try:
            # OpenAI Whisper API를 사용하여 음성을 텍스트로 변환
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{audio_format}"
            
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko"  # 한국어 설정
            )
            
            return {
                "success": True,
                "type": "audio",
                "transcript": transcript.text,
                "original_format": audio_format
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"음성 처리 중 오류가 발생했습니다: {str(e)}",
                "type": "audio"
            }
    
    def process_image(self, image_data: bytes, image_format: str = "png") -> Dict[str, Any]:
        """
        이미지 데이터를 텍스트로 변환 (이미지 분석)
        
        Args:
            image_data: 이미지 파일 바이트 데이터
            image_format: 이미지 파일 형식 (png, jpg, jpeg 등)
        
        Returns:
            Dict: 처리 결과
        """
        try:
            # 이미지를 base64로 인코딩
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # GPT-4 Vision을 사용하여 이미지 분석
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """이 이미지를 분석하여 다음 정보를 추출해주세요:
1. 이미지에 무엇이 보이는지 설명
2. 일정이나 캘린더와 관련된 정보가 있다면 추출
3. 텍스트가 있다면 읽어주세요
4. 날짜, 시간, 장소 등의 정보가 있다면 추출
5. 사용자가 일정 관리에 도움이 될 수 있는 정보를 정리

한국어로 답변해주세요."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "success": True,
                "type": "image",
                "analysis": analysis,
                "original_format": image_format
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"이미지 처리 중 오류가 발생했습니다: {str(e)}",
                "type": "image"
            }
    
    def process_clipboard_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        클립보드에서 붙여넣은 이미지 처리
        
        Args:
            image_data: 클립보드 이미지 바이트 데이터
        
        Returns:
            Dict: 처리 결과
        """
        return self.process_image(image_data, "png")
    
    def process_mixed_content(self, text: str, audio_data: Optional[bytes] = None, 
                            image_data: Optional[bytes] = None) -> Dict[str, Any]:
        """
        텍스트와 멀티미디어가 혼합된 입력 처리
        
        Args:
            text: 텍스트 입력
            audio_data: 음성 데이터 (선택사항)
            image_data: 이미지 데이터 (선택사항)
        
        Returns:
            Dict: 처리 결과
        """
        try:
            results = {
                "success": True,
                "type": "mixed",
                "text": text,
                "processed_content": []
            }
            
            # 음성 처리
            if audio_data:
                audio_result = self.process_audio(audio_data)
                if audio_result["success"]:
                    results["processed_content"].append({
                        "type": "audio",
                        "content": audio_result["transcript"]
                    })
                else:
                    results["processed_content"].append({
                        "type": "audio_error",
                        "content": audio_result["error"]
                    })
            
            # 이미지 처리
            if image_data:
                image_result = self.process_image(image_data)
                if image_result["success"]:
                    results["processed_content"].append({
                        "type": "image",
                        "content": image_result["analysis"]
                    })
                else:
                    results["processed_content"].append({
                        "type": "image_error",
                        "content": image_result["error"]
                    })
            
            # 최종 통합 메시지 생성
            final_message = text
            if results["processed_content"]:
                final_message += "\n\n[추가 정보]\n"
                for item in results["processed_content"]:
                    if item["type"] == "audio":
                        final_message += f"음성 내용: {item['content']}\n"
                    elif item["type"] == "image":
                        final_message += f"이미지 분석: {item['content']}\n"
                    elif "error" in item["type"]:
                        final_message += f"오류: {item['content']}\n"
            
            results["final_message"] = final_message
            return results
            
        except Exception as e:
            return {
                "success": False,
                "error": f"혼합 콘텐츠 처리 중 오류가 발생했습니다: {str(e)}",
                "type": "mixed"
            }
    
    def format_for_agent(self, processed_result: Dict[str, Any]) -> str:
        """
        처리된 결과를 에이전트가 이해할 수 있는 형식으로 포맷
        
        Args:
            processed_result: 멀티미디어 처리 결과
        
        Returns:
            str: 에이전트용 포맷된 메시지
        """
        if not processed_result["success"]:
            return f"멀티미디어 처리 실패: {processed_result.get('error', 'Unknown error')}"
        
        if processed_result["type"] == "audio":
            return f"[음성 메시지] {processed_result['transcript']}"
        elif processed_result["type"] == "image":
            return f"[이미지 메시지] {processed_result['analysis']}"
        elif processed_result["type"] == "mixed":
            return processed_result["final_message"]
        else:
            return "알 수 없는 멀티미디어 형식입니다."
