import 'package:flutter/material.dart';

import '../models/models.dart';
import '../services/api_service.dart';
import '../widgets/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final ApiService _apiService = ApiService();

  int _userId = 0;

  List<ChatMessage> _messages = [];
  List<ChatInfo> _chats = [];
  ChatInfo? _currentChat;
  bool _isLoading = false;
  RateLimitInfo? _rateLimitInfo;
  bool _isServerHealthy = false;
  bool _isLoadingChats = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initialize();
    });
  }

  Future<void> _initialize() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedId = prefs.getInt('user_id');

      if (savedId != null) {
        _userId = savedId;
      } else {
        _userId = DateTime.now().millisecondsSinceEpoch % 1000000;
        await prefs.setInt('user_id', _userId);
      }

      await _checkServerHealth();
      await _loadChats();
    } catch (e) {
      debugPrint('Initialize error: $e');
    }
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _checkServerHealth() async {
    try {
      final isHealthy = await _apiService.checkHealth();
      if (!mounted) return;
      setState(() => _isServerHealthy = isHealthy);
    } catch (e) {
      debugPrint('Health check error: $e');
      if (!mounted) return;
      setState(() => _isServerHealthy = false);
    }
  }

  Future<void> _loadChats() async {
    if (!mounted) return;
    setState(() => _isLoadingChats = true);

    try {
      final chats = await _apiService.getUserChats(_userId);
      if (!mounted) return;

      setState(() {
        _chats = chats;
        _isLoadingChats = false;
        if (_chats.isEmpty) {
          _createNewChatSilent();
        } else {
          _currentChat = _chats.first;
          _loadChatHistory(_chats.first.chatId);
        }
      });
    } catch (e) {
      debugPrint('Load chats error: $e');
      if (!mounted) return;
      setState(() => _isLoadingChats = false);
      _createNewChatSilent();
    }
  }

  Future<void> _createNewChatSilent() async {
    try {
      final newChat = await _apiService.createNewChat(_userId);
      if (!mounted) return;

      setState(() {
        _chats.insert(0, newChat);
        _currentChat = newChat;
      });
    } catch (e) {
      debugPrint('Create chat error: $e');
      if (!mounted) return;

      final localChat = ChatInfo(
        chatId: 'local-${DateTime.now().millisecondsSinceEpoch}',
        title: 'Чат #1',
        createdAt: DateTime.now().toIso8601String(),
      );

      setState(() {
        _chats = [localChat];
        _currentChat = localChat;
      });
    }
  }

  Future<void> _createNewChat({String? title}) async {
    try {
      final newChat = await _apiService.createNewChat(_userId, title: title);
      if (!mounted) return;

      setState(() {
        _chats.insert(0, newChat);
        _currentChat = newChat;
        _messages.clear();
      });

      if (Navigator.canPop(context)) {
        Navigator.pop(context);
      }

      _showSnackBar('✅ Жаңа чат жасалды');
    } catch (e) {
      debugPrint('Create chat error: $e');
      if (!mounted) return;
      _showSnackBar('Қате: сервер қолжетімсіз');
    }
  }

  Future<void> _switchChat(ChatInfo chat) async {
    if (!mounted) return;

    setState(() {
      _currentChat = chat;
      _messages.clear();
    });

    if (Navigator.canPop(context)) {
      Navigator.pop(context);
    }

    await _loadChatHistory(chat.chatId);
  }

  Future<void> _loadChatHistory(String chatId) async {
    try {
      final history = await _apiService.getChatHistory(_userId, chatId);
      if (!mounted) return;

      if (history.isNotEmpty) {
        setState(() {
          _messages = history;
        });
        _scrollToBottom();
      }
    } catch (e) {
      debugPrint('Load history error: $e');
    }
  }

  Future<void> _deleteChat(ChatInfo chat) async {
    try {
      final success = await _apiService.deleteChat(_userId, chat.chatId);
      if (!mounted) return;

      if (success) {
        setState(() {
          _chats.remove(chat);
          if (_currentChat?.chatId == chat.chatId) {
            if (_chats.isNotEmpty) {
              _currentChat = _chats.first;
              _messages.clear();
            } else {
              _createNewChatSilent();
            }
          }
        });
        _showSnackBar('Чат жойылды');
      }
    } catch (e) {
      debugPrint('Delete chat error: $e');
      if (mounted) {
        _showSnackBar('Қате: чатты жою мүмкін емес');
      }
    }
  }

  Future<void> _renameChat(ChatInfo chat, String newTitle) async {
    try {
      final updated = await _apiService.renameChat(_userId, chat.chatId, newTitle);
      if (!mounted) return;

      if (updated != null) {
        setState(() {
          final idx = _chats.indexWhere((c) => c.chatId == chat.chatId);
          if (idx != -1) {
            _chats[idx] = updated;
          }
          if (_currentChat?.chatId == chat.chatId) {
            _currentChat = updated;
          }
        });
        _showSnackBar('Чат аты өзгертілді');
      }
    } catch (e) {
      debugPrint('Rename chat error: $e');
      if (mounted) {
        _showSnackBar('Қате: чат атын өзгерту мүмкін емес');
      }
    }
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      Future.delayed(const Duration(milliseconds: 100), () {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      });
    }
  }

  void _showSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: const Color(0xFF27272A),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  Future<void> _sendMessage() async {
    if (_currentChat == null) {
      _showSnackBar('Алдымен чат жасаңыз');
      return;
    }

    final text = _messageController.text.trim();
    if (text.isEmpty || _isLoading || !mounted) return;

    if (!_isServerHealthy) {
      _showSnackBar('Серверге қосылу мүмкін емес');
      await _checkServerHealth();
      return;
    }

    final userMessage = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      text: text,
      isUser: true,
      timestamp: DateTime.now(),
    );

    setState(() {
      _messages.add(userMessage);
      _isLoading = true;
    });

    _messageController.clear();
    _scrollToBottom();

    try {
      final response = await _apiService.sendMessage(
        _userId,
        _currentChat!.chatId,
        text,
      );

      if (!mounted) return;

      final botMessage = ChatMessage(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        text: response['response'] ?? 'Жауап алынбады',
        isUser: false,
        timestamp: DateTime.now(),
      );

      setState(() {
        _messages.add(botMessage);
        _isLoading = false;

        _rateLimitInfo = RateLimitInfo(
          count: response['message_count'] ?? 0,
          limit: 15,
          remaining: response['remaining_messages'] ?? 15,
        );
      });

      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;

      final errorMessage = ChatMessage(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        text: 'Қате: ${e.toString().replaceAll('Exception: ', '')}',
        isUser: false,
        timestamp: DateTime.now(),
      );

      setState(() {
        _messages.add(errorMessage);
        _isLoading = false;
      });

      _scrollToBottom();
      await _checkServerHealth();
    }
  }

  Future<void> _sendVoiceMessage(String audioPath) async {
    if (_currentChat == null) return;

    setState(() => _isLoading = true);

    try {
      final result = await _apiService.sendVoiceMessage(
        _userId,
        _currentChat!.chatId,
        audioPath,
      );

      if (!mounted) return;

      if (result.containsKey('error')) {
        final errorMsg = ChatMessage(
          id: DateTime.now().toString(),
          text: result['message'] ?? 'Қате орын алды',
          isUser: false,
          timestamp: DateTime.now(),
        );
        setState(() {
          _messages.add(errorMsg);
          _isLoading = false;
        });
      } else {
        final recognizedText = result['recognized_text'] ?? '';
        final aiResponse = result['response'] ?? '';

        final userMsg = ChatMessage(
          id: '${DateTime.now().millisecondsSinceEpoch}_user',
          text: '🎙️ $recognizedText',
          isUser: true,
          timestamp: DateTime.now(),
        );
        final botMsg = ChatMessage(
          id: '${DateTime.now().millisecondsSinceEpoch}_bot',
          text: aiResponse,
          isUser: false,
          timestamp: DateTime.now(),
        );

        setState(() {
          _messages.addAll([userMsg, botMsg]);
          _isLoading = false;
        });
      }

      _scrollToBottom();
    } catch (e) {
      debugPrint('Voice message error: $e');
      if (mounted) {
        setState(() => _isLoading = false);
        _showSnackBar('Дауыстық хабарлама жіберу мүмкін емес');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF09090B),
      appBar: _buildAppBar(),
      drawer: ChatDrawer(
        chats: _chats,
        currentChat: _currentChat,
        rateLimitInfo: _rateLimitInfo,
        isLoadingChats: _isLoadingChats,
        onCreateNewChat: () => _createNewChat(),
        onSwitchChat: _switchChat,
        onDeleteChat: _deleteChat,
        onRenameChat: _renameChat,
      ),
      body: Column(
        children: [
          if (!_isServerHealthy) _buildOfflineBanner(),
          Expanded(
            child: _messages.isEmpty
                ? WelcomeScreen(isServerHealthy: _isServerHealthy)
                : _buildMessageList(),
          ),
          ChatInputArea(
            controller: _messageController,
            isLoading: _isLoading,
            isServerHealthy: _isServerHealthy,
            hasChatSelected: _currentChat != null,
            rateLimitInfo: _rateLimitInfo,
            onSend: _sendMessage,
            onSendVoice: _sendVoiceMessage,
          ),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: const Color(0xFF09090B),
      elevation: 0,
      centerTitle: true,
      leading: Builder(
        builder: (context) => IconButton(
          icon: const Icon(Icons.menu, color: Color(0xFFA1A1AA)),
          onPressed: () => Scaffold.of(context).openDrawer(),
        ),
      ),
      title: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Flexible(
            child: Text(
              _currentChat?.title ?? 'AsylBILIM',
              style: const TextStyle(
                color: Color(0xFFFAFAFA),
                fontSize: 16,
                fontWeight: FontWeight.w500,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: _isServerHealthy
                  ? const Color(0xFF10B981)
                  : const Color(0xFFEF4444),
              shape: BoxShape.circle,
            ),
          ),
        ],
      ),
      actions: [
        IconButton(
          icon: const Icon(Icons.refresh, color: Color(0xFFA1A1AA)),
          onPressed: () {
            _checkServerHealth();
            _loadChats();
          },
        ),
      ],
    );
  }

  Widget _buildMessageList() {
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.all(16),
      itemCount: _messages.length + (_isLoading ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == _messages.length) {
          return const LoadingBubble();
        }
        return MessageBubble(message: _messages[index]);
      },
    );
  }

  Widget _buildOfflineBanner() {
    return Container(
      width: double.infinity,
      color: const Color(0xFFEF4444),
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: const Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.wifi_off, size: 14, color: Colors.white),
          SizedBox(width: 8),
          Text(
            'Серверге қосылу мүмкін емес. Қайта қосылуда...',
            style: TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

