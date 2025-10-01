#!/usr/bin/env python3
"""
팀 캘린더 & 챗봇 애플리케이션 실행 스크립트
"""
import uvicorn
import os
from pathlib import Path

def main():
    # 필요한 디렉토리 생성
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("RAG/VectorDB/user", exist_ok=True)
    
    print("🚀 팀 캘린더 & 챗봇 애플리케이션을 시작합니다...")
    print("📅 왼쪽: 캘린더 뷰")
    print("🤖 오른쪽: 일정 관리 챗봇")
    print("🔍 RAG 기반 의미 검색 지원")
    print("\n🌐 브라우저에서 http://localhost:8000 으로 접속하세요!")
    print("⏹️  종료하려면 Ctrl+C를 누르세요.\n")
    
    # FastAPI 애플리케이션 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
