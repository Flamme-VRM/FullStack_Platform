# api_server.py - REST API с множественными чатами
"""
Запуск из корня проекта:
python -m uvicorn src.api_server:app --host 0.0.0.0 --port 8000 --reload
или
python -m src.api_server
"""

import os
import logging
import uuid
import tempfile
import json
import msgpack
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse as FastAPIStreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from .services.ai import AIService
from .services.cache import CacheService
from .services.speech_to_text import SpeechToTextService
from .config import settings

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (ЗАГЛУШКИ)
# ============================================================================

cache_service: Optional[CacheService] = None
ai_service: Optional[AIService] = None
speech_service: Optional[SpeechToTextService] = None

# ============================================================================
# LIFESPAN - ИНИЦИАЛИЗАЦИЯ И ОЧИСТКА
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    Инициализация выполняется ОДИН РАЗ при старте рабочего процесса.
    """
    global cache_service, ai_service, speech_service
    
    logger.info("🚀 Initializing AsylBILIM services...")
    
    try:
        # Инициализация Redis
        cache_service = CacheService(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            username=settings.REDIS_USERNAME,
            password=settings.REDIS_PASSWORD
        )
        logger.info("✅ Redis cache service initialized")
        
        # Инициализация AI сервиса
        ai_service = AIService(
            api_key=settings.LLM_API_KEY,
            model_name=settings.MODEL,
            cache_service=cache_service,
        )
        logger.info(f"✅ AI service initialized (model: {settings.MODEL})")
        
        # Инициализация Speech-to-Text
        speech_service = SpeechToTextService()
        logger.info("✅ Speech-to-Text service initialized")
        
        logger.info("🎉 All services initialized successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise
    
    yield  # Здесь приложение работает
    
    # === GRACEFUL SHUTDOWN ===
    logger.info("🛑 Shutting down AsylBILIM services...")
    
    try:
        if cache_service:
            cache_service.close()
            logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing cache service: {e}")
    
    try:
        if speech_service:
            speech_service.cleanup()
            logger.info("✅ Speech service cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up speech service: {e}")
    
    try:
        if ai_service and hasattr(ai_service, 'embedding_service'):
            ai_service.embedding_service.unload_model()
            logger.info("✅ Embedding model unloaded")
    except Exception as e:
        logger.error(f"Error unloading embedding model: {e}")
    
    logger.info("👋 Shutdown complete")

# ============================================================================
# FASTAPI ПРИЛОЖЕНИЕ
# ============================================================================

app = FastAPI(
    title="AsylBILIM API",
    description="REST API для UNT подготовки с множественными чатами",
    version="2.1.0",
    lifespan=lifespan  # 🔥 КРИТИЧЕСКИ ВАЖНО!
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

class ChatRequest(BaseModel):
    message: str
    user_id: int
    chat_id: str
    language: str = "kk"

class ChatResponse(BaseModel):
    response: str
    message_count: int
    remaining_messages: int

class NewChatRequest(BaseModel):
    user_id: int
    title: Optional[str] = None

class ChatInfo(BaseModel):
    chat_id: str
    title: str
    created_at: str
    last_message: Optional[str] = None
    message_count: int = 0

class ChatsListResponse(BaseModel):
    chats: List[ChatInfo]

class RateLimitInfo(BaseModel):
    count: int
    limit: int
    remaining: int
    reset_time: int

class MessageItem(BaseModel):
    role: str
    content: str

class ChatHistoryResponse(BaseModel):
    messages: List[MessageItem]

class RenameChatRequest(BaseModel):
    user_id: int
    title: str

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def generate_chat_id() -> str:
    """Генерация уникального ID чата"""
    return str(uuid.uuid4())

def get_chat_history_key(user_id: int, chat_id: str) -> str:
    """Ключ для истории чата в Redis"""
    return f"chat_history:{user_id}:{chat_id}"

def get_chat_metadata_key(user_id: int, chat_id: str) -> str:
    """Ключ для метаданных чата"""
    return f"chat_metadata:{user_id}:{chat_id}"

def get_user_chats_key(user_id: int) -> str:
    """Ключ для списка чатов пользователя"""
    return f"user_chats:{user_id}"

# ============================================================================
# API ЭНДПОИНТЫ
# ============================================================================

@app.get("/")
async def root():
    return {
        "app": "AsylBILIM API",
        "version": "2.1.0",
        "status": "running",
        "features": ["Multiple chats", "RAG", "Voice input"],
        "endpoints": {
            "chat": "/api/chat",
            "new_chat": "/api/chats/new",
            "list_chats": "/api/chats/{user_id}",
            "delete_chat": "/api/chats/{chat_id}",
            "voice": "/api/voice",
            "status": "/api/status/{user_id}",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    try:
        cache_service.client.ping()
        return {
            "status": "healthy",
            "redis": "connected",
            "ai_model": settings.MODEL,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/api/chats/new", response_model=ChatInfo)
async def create_new_chat(request: NewChatRequest):
    """
    Создание нового чата
    
    Пример:
```json
    {
        "user_id": 123456,
        "title": "Математика - Алгебра"
    }
```
    """
    try:
        chat_id = generate_chat_id()
        user_id = request.user_id
        
        # Генерируем заголовок если не указан
        if not request.title:
            # Подсчитываем количество существующих чатов
            user_chats_key = get_user_chats_key(user_id)
            existing_chats = cache_service.client.llen(user_chats_key) or 0
            title = "Жаңа чат"
        else:
            title = request.title
        
        # Создаём метаданные чата
        metadata = {
            "chat_id": chat_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "last_message": None,
            "message_count": 0
        }
        
        # Сохраняем метаданные
        metadata_key = get_chat_metadata_key(user_id, chat_id)
        cache_service.client.setex(
            metadata_key,
            86400 * 30,  # 30 дней
            msgpack.packb(metadata)
        )
        
        # Добавляем chat_id в список чатов пользователя
        user_chats_key = get_user_chats_key(user_id)
        cache_service.client.lpush(user_chats_key, chat_id)
        cache_service.client.expire(user_chats_key, 86400 * 30)
        
        logger.info(f"Created new chat {chat_id} for user {user_id}")
        
        return ChatInfo(**metadata)
        
    except Exception as e:
        logger.error(f"Error creating chat: {e}")
        raise HTTPException(status_code=500, detail="Не удалось создать чат")

@app.get("/api/chats/{user_id}", response_model=ChatsListResponse)
async def get_user_chats(user_id: int):
    """Получить список всех чатов пользователя"""
    try:
        user_chats_key = get_user_chats_key(user_id)
        chat_ids = cache_service.client.lrange(user_chats_key, 0, -1)
        
        chats = []
        for chat_id in chat_ids:
            if isinstance(chat_id, bytes):
                chat_id = chat_id.decode('utf-8')
            
            metadata_key = get_chat_metadata_key(user_id, chat_id)
            metadata_str = cache_service.client.get(metadata_key)
            
            if metadata_str:
                try:
                    metadata = msgpack.unpackb(metadata_str)
                    chats.append(ChatInfo(**metadata))
                except:
                    # Если метаданные повреждены, создаём базовые
                    chats.append(ChatInfo(
                        chat_id=chat_id,
                        title=f"Чат {chat_id[:8]}",
                        created_at=datetime.now().isoformat(),
                        message_count=0
                    ))
        
        # Сортируем по времени создания (новые первые)
        chats.sort(key=lambda x: x.created_at, reverse=True)
        
        return ChatsListResponse(chats=chats)
        
    except Exception as e:
        logger.error(f"Error getting chats for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Не удалось загрузить чаты")

@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str, user_id: int):
    """Удалить чат"""
    try:
        # Удаляем историю
        history_key = get_chat_history_key(user_id, chat_id)
        cache_service.client.delete(history_key)
        
        # Удаляем метаданные
        metadata_key = get_chat_metadata_key(user_id, chat_id)
        cache_service.client.delete(metadata_key)
        
        # Удаляем из списка чатов
        user_chats_key = get_user_chats_key(user_id)
        cache_service.client.lrem(user_chats_key, 0, chat_id)
        
        logger.info(f"Deleted chat {chat_id} for user {user_id}")
        
        return {"success": True, "message": "Чат удалён"}
        
    except Exception as e:
        logger.error(f"Error deleting chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Не удалось удалить чат")

@app.patch("/api/chats/{chat_id}")
async def rename_chat(chat_id: str, request: RenameChatRequest):
    """Переименовать чат"""
    try:
        metadata_key = get_chat_metadata_key(request.user_id, chat_id)
        metadata_raw = cache_service.client.get(metadata_key)
        
        if not metadata_raw:
            raise HTTPException(status_code=404, detail="Чат не найден")
        
        metadata = msgpack.unpackb(metadata_raw)
        metadata["title"] = request.title
        
        cache_service.client.setex(
            metadata_key,
            86400 * 30,
            msgpack.packb(metadata)
        )
        
        logger.info(f"Renamed chat {chat_id} to '{request.title}'")
        return ChatInfo(**metadata)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail="Не удалось переименовать чат")

@app.get("/api/chats/{user_id}/{chat_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(user_id: int, chat_id: str):
    """Получить историю сообщений чата"""
    try:
        history_key = get_chat_history_key(user_id, chat_id)
        history_raw = cache_service.client.get(history_key)
        
        if not history_raw:
            return ChatHistoryResponse(messages=[])
        
        history = msgpack.unpackb(history_raw, use_list=True)
        messages = []
        
        for entry in history:
            if isinstance(entry, bytes):
                entry = entry.decode('utf-8')
            
            if entry.startswith('User: '):
                messages.append(MessageItem(
                    role='user',
                    content=entry[6:]
                ))
            elif entry.startswith('AsylBILIM: '):
                messages.append(MessageItem(
                    role='assistant',
                    content=entry[11:]
                ))
        
        return ChatHistoryResponse(messages=messages)
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Не удалось загрузить историю")

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Отправка сообщения в конкретный чат
    
    Пример:
```json
    {
        "message": "Математикалық литерацияға қалай дайындаламын?",
        "user_id": 123456,
        "chat_id": "uuid-here",
        "language": "kk"
    }
```
    """
    try:
        user_id = request.user_id
        chat_id = request.chat_id
        message = request.message
        
        # Проверка rate limit
        is_allowed, current_count, time_until_reset = cache_service.check_rate_limit(user_id)
        
        if not is_allowed:
            hours_left = time_until_reset // 3600
            minutes_left = (time_until_reset % 3600) // 60
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Күнделікті лимит асталды. Қалған уақыт: {hours_left}с {minutes_left}м",
                    "current_count": current_count,
                    "limit": 15,
                    "retry_after": time_until_reset
                }
            )
        
        # Получаем историю конкретного чата
        history_key = get_chat_history_key(user_id, chat_id)
        history_raw = cache_service.client.get(history_key)
        
        history = msgpack.unpackb(history_raw, use_list=True) if history_raw else []
        
        # Добавляем новое сообщение
        history.append(f'User: {message}')
        
        # Генерируем ответ (используем модифицированный метод)
        ai_response = await ai_service.generate_response_for_chat(
            user_id, 
            chat_id, 
            message, 
            history
        )
        
        # Сохраняем историю
        history.append(f"AsylBILIM: {ai_response}")
        
        cache_service.client.setex(
            history_key,
            86400 * 7,  # 7 дней
            msgpack.packb(history[-50:])  # Храним последние 50 сообщений
        )
        
        # Обновляем метаданные чата
        metadata_key = get_chat_metadata_key(user_id, chat_id)
        metadata_raw = cache_service.client.get(metadata_key)
        
        if metadata_raw:
            metadata = msgpack.unpackb(metadata_raw)
            was_first_message = metadata.get('message_count', 0) == 0
            metadata['last_message'] = message[:50] + "..." if len(message) > 50 else message
            metadata['message_count'] = len(history) // 2
            
            # Auto-generate title on first message
            if was_first_message:
                try:
                    generated_title = await ai_service.generate_chat_title(message, ai_response)
                    metadata['title'] = generated_title
                    logger.info(f"Auto-titled chat {chat_id}: '{generated_title}'")
                except Exception as e:
                    logger.error(f"Auto-title failed: {e}")
            
            cache_service.client.setex(
                metadata_key,
                86400 * 30,
                msgpack.packb(metadata)
            )
        
        # Получаем информацию о лимите
        rate_info = cache_service.get_rate_limit_info(user_id)
        
        return ChatResponse(
            response=ai_response,
            message_count=rate_info['count'],
            remaining_messages=rate_info['remaining']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Сервердегі қате орын алды")

@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Стриминговая версия /api/chat.
    Возвращает SSE-поток токенов по мере генерации.

    Клиент должен читать тело ответа как поток и парсить события
    формата: data: <текст>\\n\\n
    Конец стрима сигнализируется: data: [DONE]\\n\\n
    """
    user_id = request.user_id
    chat_id = request.chat_id
    message = request.message

    # Rate limit — до начала стриминга, пока ещё можем вернуть 429
    is_allowed, current_count, time_until_reset = cache_service.check_rate_limit(user_id)

    if not is_allowed:
        hours_left = time_until_reset // 3600
        minutes_left = (time_until_reset % 3600) // 60
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Күнделікті лимит асталды. Қалған уақыт: {hours_left}с {minutes_left}м",
                "current_count": current_count,
                "limit": 15,
                "retry_after": time_until_reset
            }
        )

    # Загружаем историю чата
    history_key = get_chat_history_key(user_id, chat_id)
    history_raw = cache_service.client.get(history_key)
    history = msgpack.unpackb(history_raw, use_list=True) if history_raw else []

    # Добавляем сообщение пользователя в историю
    history.append(f"User: {message}")

    def save_history_after_stream(generator):
        """
        Обёртка над генератором: после того как стриминг завершился,
        собираем полный ответ из накопленных чанков и пишем в Redis.
        """
        full_response_parts = []

        for chunk in generator:
            # Перехватываем data-чанки чтобы накопить текст
            if chunk.startswith("data: ") and chunk.strip() not in ("data: [DONE]", "data: [ERROR]"):
                # Возвращаем экранированные \n обратно
                text_part = chunk[6:].rstrip().replace("\\n", "\n")
                full_response_parts.append(text_part)
            yield chunk

        # Генератор исчерпан — сохраняем историю
        full_response = "".join(full_response_parts)
        if full_response:
            updated_history = history + [f"AsylBILIM: {full_response}"]
            cache_service.client.setex(
                history_key,
                86400 * 7,
                msgpack.packb(updated_history[-50:])
            )

            # Обновляем метаданные чата
            metadata_key = get_chat_metadata_key(user_id, chat_id)
            metadata_raw = cache_service.client.get(metadata_key)
            if metadata_raw:
                metadata = msgpack.unpackb(metadata_raw)
                metadata["last_message"] = message[:50] + "..." if len(message) > 50 else message
                metadata["message_count"] = len(updated_history) // 2
                cache_service.client.setex(
                    metadata_key,
                    86400 * 30,
                    msgpack.packb(metadata)
                )

    gemini_generator = ai_service.stream_response_for_chat(
        user_id, chat_id, message, history
    )

    return FastAPIStreamingResponse(
        save_history_after_stream(gemini_generator),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/voice")
async def voice_endpoint(
    user_id: int,
    chat_id: str,
    language: str = "kk",
    audio: UploadFile = File(...)
):
    """Обработка голосовых сообщений для конкретного чата"""
    try:
        # Проверка rate limit
        is_allowed, current_count, time_until_reset = cache_service.check_rate_limit(user_id)
        
        if not is_allowed:
            hours_left = time_until_reset // 3600
            minutes_left = (time_until_reset % 3600) // 60
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Күнделікті лимит асталды",
                    "current_count": current_count
                }
            )
        
        # Сохраняем аудио
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Распознаём речь
        recognized_text = await speech_service.convert_voice_to_text(temp_path, language)
        
        if not recognized_text:
            raise HTTPException(
                status_code=400,
                detail="Аудионы танымады"
            )
        
        # Получаем историю чата
        history_key = get_chat_history_key(user_id, chat_id)
        history_raw = cache_service.client.get(history_key)
        
        history = msgpack.unpackb(history_raw, use_list=True) if history_raw else []
        history.append(f'User: {recognized_text}')
        
        # Генерируем ответ
        ai_response = await ai_service.generate_response_for_chat(
            user_id, 
            chat_id, 
            recognized_text, 
            history
        )
        
        # Сохраняем историю
        history.append(f"AsylBILIM: {ai_response}")
        cache_service.client.setex(history_key, 86400 * 7, msgpack.packb(history[-50:]))
        
        rate_info = cache_service.get_rate_limit_info(user_id)
        
        return {
            "recognized_text": recognized_text,
            "response": ai_response,
            "message_count": rate_info['count'],
            "remaining_messages": rate_info['remaining']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Аудионы өңдеуде қате")

@app.get("/api/status/{user_id}", response_model=RateLimitInfo)
async def get_status(user_id: int):
    """Получить информацию о лимите"""
    try:
        rate_info = cache_service.get_rate_limit_info(user_id)
        return RateLimitInfo(**rate_info)
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail="Сервердегі қате")

if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║        AsylBILIM API Server v2.1 - Multiple Chats         ║
    ╚═══════════════════════════════════════════════════════════╝
    
    📚 API Documentation: http://localhost:8000/docs
    🔧 Server: http://localhost:8000
    
    Новые возможности:
    ✅ Множественные чаты для каждого пользователя
    ✅ Автоматическое управление историей
    ✅ Удаление ненужных чатов
    """)
    
    uvicorn.run("src.api_server:app", host="0.0.0.0", port=8000, reload=True)