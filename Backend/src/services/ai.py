import asyncio
import logging
import os
import numpy as np
from google import genai
from google.genai import types as genai_types
from tenacity import retry, stop_after_attempt, wait_exponential
from .cache import CacheService
from .embeddings import EmbeddingService
from .vector_db import VectorDB
from ..config import settings

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, api_key: str, model_name: str, cache_service: CacheService, 
                 document_loader=None):  # document_loader is deprecated but kept for compatibility
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.cache = cache_service
        self.system_prompt = self._load_system_prompt_from_file()
        
        # Initialize vector search components
        self.use_vector_search = True
        try:
            self.embedding_service = EmbeddingService()
            self.vector_db = VectorDB(db_path=settings.VECTOR_DB_PATH)
            
            # Check if database has data
            db_stats = self.vector_db.get_database_stats()
            if db_stats.get('total_chunks', 0) == 0:
                logger.warning("Vector database is empty! Run 'python scripts/index_documents.py' first")
                self.use_vector_search = False
            else:
                logger.info(f"Vector search ready: {db_stats['total_chunks']} chunks available")
        except Exception as e:
            logger.error(f"Failed to initialize vector search: {e}")
            self.use_vector_search = False

        # Pre-compute chit-chat centroid for semantic routing
        self._chit_chat_centroid = None
        self._rag_threshold = 0.45  # below this similarity → educational → run RAG
        if self.use_vector_search:
            self._init_semantic_router()

        if not self.system_prompt:
            logger.warning("System prompt could not be loaded")
            raise SystemExit()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _generate_with_retry(self, prompt: str):
        return await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model_name,
            contents=prompt,
        )

    def _load_system_prompt_from_file(self, filename: str = None) -> str:
        """Load system prompt from a text file."""
        if filename is None:
            filename = settings.SYSPROMPT_PATH

        try:
            project_root = os.getcwd()
            file_path = os.path.join(project_root, filename)
            
            with open(file_path, 'r', encoding='utf-8') as file:
                system_prompt = file.read().strip()
                logger.info(f"Successfully loaded system prompt from {filename}")
                return system_prompt
                
        except FileNotFoundError:
            logger.error(f"System prompt file '{filename}' not found in project root")
            return ""
        except Exception as e:
            logger.error(f"Error reading system prompt file '{filename}': {str(e)}")
            return ""

    def _init_semantic_router(self):
        """
        Pre-compute a chit-chat centroid vector at startup.
        Embedding a diverse set of greetings/thanks/identity phrases in
        Kazakh, Russian, and English, then averaging them into one vector.
        Cost: a single API call at boot, stored forever in RAM (~12KB).
        """
        CHIT_CHAT_EXAMPLES = [
            # Kazakh greetings & small talk
            "Сәлем", "Сәлеметсіз бе", "Қалайсың", "Қалайсыз", "Қалың қалай",
            "Саламатсыз ба", "Қайырлы таң", "Қайырлы кеш",
            # Kazakh thanks & farewell
            "Рахмет", "Рақмет", "Көп рахмет", "Сау бол", "Сау болыңыз",
            "Жақсы", "Жарайды", "Түсіндім", "Мақұл",
            # Kazakh identity
            "Сен кімсің", "Атың кім", "Сенің атың кім",
            "Не істей аласың", "Сенің міндетің не", "Сен бот сың ба",
            # Kazakh generic
            "Көмектес", "Баста", "Бастайық", "Жалғастыр",
            # Russian greetings & small talk
            "Привет", "Здравствуй", "Здравствуйте", "Как дела", "Как ты",
            "Доброе утро", "Добрый вечер",
            # Russian thanks & farewell
            "Спасибо", "Благодарю", "Большое спасибо", "Пока", "До свидания",
            "Хорошо", "Ладно", "Понял", "Ок",
            # Russian identity
            "Ты кто", "Кто ты", "Что ты умеешь", "Что ты можешь",
            "Ты бот", "Ты искусственный интеллект",
            # English greetings
            "Hi", "Hello", "Hey", "Good morning", "How are you",
            # English thanks & farewell
            "Thanks", "Thank you", "Bye", "Goodbye", "See you",
            "OK", "Okay", "Sure", "Got it", "Alright",
            # English identity
            "Who are you", "What are you", "What can you do",
            "Are you a bot", "Are you AI",
        ]

        try:
            embeddings = self.embedding_service.encode(CHIT_CHAT_EXAMPLES)
            centroid = np.mean(embeddings, axis=0)
            # Normalize to unit vector for fast cosine via dot product
            self._chit_chat_centroid = centroid / np.linalg.norm(centroid)
            logger.info(f"Semantic router initialized: {len(CHIT_CHAT_EXAMPLES)} chit-chat examples embedded")
        except Exception as e:
            logger.error(f"Failed to init semantic router: {e}")
            self._chit_chat_centroid = None

    def _needs_rag(self, message: str) -> bool:
        """
        Semantic router using embedding cosine distance.
        Compares the message embedding to a pre-computed chit-chat centroid.
        If close enough -> chit-chat -> skip RAG.
        """
        # Fallback: if centroid failed to init, always run RAG (safe default)
        if self._chit_chat_centroid is None:
            return True

        try:
            # Embed the user message (we'll reuse this embedding for search too)
            msg_embedding = self.embedding_service.encode(message)[0]

            # Cosine similarity = dot product of normalized vectors
            similarity = float(np.dot(msg_embedding, self._chit_chat_centroid))

            if similarity >= self._rag_threshold:
                logger.info(f"Router: SKIP RAG (chit-chat, sim={similarity:.3f}): '{message[:50]}'")
                return False
            else:
                logger.debug(f"Router: RUN RAG (educational, sim={similarity:.3f}): '{message[:50]}'")
                return True

        except Exception as e:
            logger.error(f"Router error, defaulting to RAG: {e}")
            return True  # safe fallback


    def _retrieve_relevant_documents(self, query: str, top_k: int = None) -> str:
        """
        Retrieve relevant educational content using semantic search.
        Skips the DB entirely for chit-chat via the semantic router.
        """
        if top_k is None:
            top_k = settings.TOP_K_RESULTS

        if not self.use_vector_search:
            logger.debug("Vector search not available, skipping retrieval")
            return ""

        # === SEMANTIC ROUTER: skip RAG for non-educational messages ===
        if not self._needs_rag(query):
            return ""

        try:
            # Generate embedding for query
            query_embedding = self.embedding_service.encode(query)[0]

            
            # Search for similar chunks
            results = self.vector_db.search(
                query_embedding=query_embedding,
                top_k=top_k,
                min_similarity=settings.MIN_SIMILARITY
            )
            
            if not results:
                logger.info(f"No relevant documents found for query: {query[:50]}...")
                return ""
            
            # Format results for AI context
            context_parts = []
            for i, result in enumerate(results, 1):
                similarity_pct = result['similarity'] * 100
                
                context_parts.append(
                    f"[Дереккөз {i}] (релеванттылық: {similarity_pct:.1f}%)\n"
                    f"Пән: {result.get('subject', 'Белгісіз')} | "
                    f"Тақырып: {result.get('topic', 'Белгісіз')}\n"
                    f"Мазмұны: {result['content']}\n"
                )
            
            context = "\n" + "="*50 + "\n" + "\n".join(context_parts)
            
            # Форматируем список similarity для логирования
            similarities_str = ', '.join([f"{r['similarity']:.2f}" for r in results])
            
            logger.info(f"Retrieved {len(results)} relevant chunks for query "
                       f"(similarities: [{similarities_str}])")
            
            return context

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return ""

    async def generate_response(self, user_id: int, text: str) -> str:
        try:
            history = self.cache.get_user_history(user_id)
            history.append(f'User: {text}')

            recent_history = history[-10:]

            # Retrieve relevant educational content via semantic search
            relevant_context = self._retrieve_relevant_documents(text)

            full_prompt = f"{self.system_prompt}\n\nConversation History:\n" + "\n".join(recent_history)

            # Add RAG context if available
            if relevant_context:
                full_prompt += f"\n\nРелевантты оқу материалдары:\n{relevant_context}"
            else:
                logger.info(f"No relevant context found for user {user_id} query: {text[:50]}...")

            # Check cache
            cached_response = self.cache.get_cached_response(full_prompt)
            if cached_response:
                logger.info(f"Using cached response for user {user_id}")
                history.append(f"AsylBILIM: {cached_response}")
                self.cache.save_user_history(user_id, history)
                return cached_response

            # Generate new response with retry
            response = await self._generate_with_retry(full_prompt)

            if not response or not response.text:
                logger.error(f"Empty response from AI model for user {user_id}")
                return "Кешіріңіз, жауап алу мүмкін болмады. Қайталап көріңіз."

            history.append(f"Quint AI: {response.text}")
            self.cache.save_user_history(user_id, history)
            self.cache.cache_response(full_prompt, response.text)

            return response.text

        except Exception as e:
            err = str(e).lower()
            if 'blocked' in err or 'safety' in err:
                logger.error(f"Content blocked for user {user_id}: {e}")
                return "Кешіріңіз, сұрақ қауіпсіздік фильтрлерімен бөгелді. Басқаша сұраңыз."
            logger.error(f"Unexpected error for user {user_id}: {type(e).__name__}: {str(e)}")
            return "Кешіріңіз, техникалық қате орын алды. Кейінірек қайталап көріңіз."
         
    async def generate_response_for_chat(
        self, 
        user_id: int, 
        chat_id: str, 
        text: str, 
        history: list
    ) -> str:
        """
        Генерация ответа для конкретного чата
        """
        try:
            recent_history = history[-10:] if len(history) > 10 else history
            relevant_context = self._retrieve_relevant_documents(text)

            full_prompt = (
                f"{self.system_prompt}\n\n"
                f"Conversation History:\n" + "\n".join(recent_history)
            )

            if relevant_context:
                full_prompt += f"\n\n{relevant_context}"

            cached_response = self.cache.get_cached_response(full_prompt)
            if cached_response:
                logger.info(f"Using cached response for chat {chat_id}")
                return cached_response

            response = await self._generate_with_retry(full_prompt)

            if not response or not response.text:
                return "Кешіріңіз, жауап алу мүмкін болмады."

            self.cache.cache_response(full_prompt, response.text)
            return response.text

        except Exception as e:
            logger.error(f"Error for chat {chat_id}: {e}")
            return "Кешіріңіз, техникалық қате орын алды."

    def stream_response_for_chat(
        self,
        user_id: int,
        chat_id: str,
        text: str,
        history: list
    ):
        """
        Стриминговая генерация ответа для конкретного чата.
        Возвращает генератор SSE-событий.

        plain def (не async) — намеренно, так как generate_content_stream
        является синхронным блокирующим вызовом. FastAPI автоматически
        запустит его в отдельном потоке через iterate_in_threadpool().
        """
        import time

        recent_history = history[-10:] if len(history) > 10 else history
        relevant_context = self._retrieve_relevant_documents(text)

        full_prompt = (
            f"{self.system_prompt}\n\n"
            f"Conversation History:\n" + "\n".join(recent_history)
        )

        if relevant_context:
            full_prompt += f"\n\n{relevant_context}"

        # --- Кэш: если есть точное совпадение — стримим из кэша ---
        cached_response = self.cache.get_cached_response(full_prompt)
        if cached_response:
            logger.info(f"Streaming cached response for chat {chat_id}")
            for word in cached_response.split(" "):
                yield f"data: {word} \n\n"
                time.sleep(0.04)  # имитируем скорость генерации
            yield "data: [DONE]\n\n"
            return  # выходим, Redis не трогаем — история уже была сохранена ранее

        # --- Нет кэша — стримим от Gemini ---
        try:
            gemini_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=full_prompt
            )

            full_response = ""  # накапливаем для Redis и кэша

            for chunk in gemini_stream:
                if chunk.text:
                    full_response += chunk.text
                    # Экранируем переносы строк для SSE-формата
                    safe_chunk = chunk.text.replace("\n", "\\n")
                    yield f"data: {safe_chunk}\n\n"

            # Стриминг завершён — пишем в Redis и кэш
            if full_response:
                self.cache.cache_response(full_prompt, full_response)

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Streaming error for chat {chat_id}: {e}")
            yield "data: [ERROR]\n\n"

    async def generate_chat_title(self, user_message: str, ai_response: str) -> str:
        """Generate a short chat title from the first exchange."""
        try:
            prompt = (
                "Берілген сұхбат негізінде 3-5 сөзден тұратын қысқа тақырып жаз. "
                "Тек тақырыпты жаз, басқа ештеңе жазба. Тырнақшасыз.\n\n"
                f"Қолданушы: {user_message[:200]}\n"
                f"Жауап: {ai_response[:200]}"
            )
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
            )
            if response and response.text:
                title = response.text.strip().strip('"\'')
                return title[:60]  # Cap at 60 chars
            return "Жаңа чат"
        except Exception as e:
            logger.error(f"Title generation error: {e}")
            return "Жаңа чат"