import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/models.dart';

class ApiService {
  static String get baseUrl {
    if (Platform.isAndroid) return 'http://10.0.2.2:8000/api';
    return 'http://localhost:8000/api';
  }

  static String get _healthUrl {
    if (Platform.isAndroid) return 'http://10.0.2.2:8000/health';
    return 'http://localhost:8000/health';
  }

  Future<ChatInfo> createNewChat(int userId, {String? title}) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/chats/new'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'user_id': userId,
              if (title != null) 'title': title,
            }),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return ChatInfo.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Failed to create chat');
      }
    } catch (e) {
      throw Exception('Error: $e');
    }
  }

  Future<List<ChatInfo>> getUserChats(int userId) async {
    try {
      final response = await http
          .get(
            Uri.parse('$baseUrl/chats/$userId'),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final chats = (data['chats'] as List)
            .map((chat) => ChatInfo.fromJson(chat))
            .toList();
        return chats;
      } else {
        throw Exception('Failed to load chats');
      }
    } catch (e) {
      throw Exception('Error: $e');
    }
  }

  Future<bool> deleteChat(int userId, String chatId) async {
    try {
      final response = await http
          .delete(
            Uri.parse('$baseUrl/chats/$chatId?user_id=$userId'),
          )
          .timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  Future<ChatInfo?> renameChat(
      int userId, String chatId, String newTitle) async {
    try {
      final response = await http
          .patch(
            Uri.parse('$baseUrl/chats/$chatId'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'user_id': userId,
              'title': newTitle,
            }),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return ChatInfo.fromJson(jsonDecode(response.body));
      }
      return null;
    } catch (e) {
      debugPrint('Error renaming chat: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>> sendMessage(
    int userId,
    String chatId,
    String message,
  ) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/chat'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'message': message,
              'user_id': userId,
              'chat_id': chatId,
              'language': 'kk',
            }),
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else if (response.statusCode == 429) {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['detail']['message'] ?? 'Лимит аяқталды');
      } else {
        throw Exception('Server error: ${response.statusCode}');
      }
    } on TimeoutException {
      throw Exception('Уақыт асып кетті');
    } on SocketException {
      throw Exception('Интернет байланысын тексеріңіз');
    } catch (e) {
      throw Exception('Error: $e');
    }
  }

  Stream<String> sendMessageStream(
    int userId,
    String chatId,
    String message,
  ) async* {
    final request = http.Request(
      'POST',
      Uri.parse('$baseUrl/chat/stream'),
    );

    request.headers['Content-Type'] = 'application/json';
    request.body = jsonEncode({
      'message': message,
      'user_id': userId,
      'chat_id': chatId,
      'language': 'kk',
    });

    final streamedResponse = await request.send();

    if (streamedResponse.statusCode == 429) {
      // Rate limit — читаем тело и бросаем исключение
      final body = await streamedResponse.stream.bytesToString();
      final errorData = jsonDecode(body);
      throw Exception(errorData['detail']['message'] ?? 'Лимит аяқталды');
    }

    if (streamedResponse.statusCode != 200) {
      throw Exception('Server error: ${streamedResponse.statusCode}');
    }

    // Буфер для неполных SSE-событий между TCP-пакетами
    String buffer = '';

    await for (final bytes in streamedResponse.stream) {
      buffer += utf8.decode(bytes);

      // SSE события разделяются двойным переносом строки
      final parts = buffer.split('\n\n');

      // Последняя часть может быть неполным событием — оставляем в буфере
      buffer = parts.removeLast();

      for (final part in parts) {
        if (part.startsWith('data: ')) {
          final data = part.substring(6); // убираем 'data: '

          if (data == '[DONE]') return;
          if (data == '[ERROR]') throw Exception('Генерация қатесі');

          // Возвращаем \n обратно (они были экранированы на бэкенде)
          yield data.replaceAll('\\n', '\n');
        }
      }
    }
  }

  Future<List<ChatMessage>> getChatHistory(int userId, String chatId) async {
    try {
      final response = await http
          .get(
            Uri.parse('$baseUrl/chats/$userId/$chatId/history'),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final messages =
            (data['messages'] as List).asMap().entries.map((entry) {
          final i = entry.key;
          final msg = entry.value;
          return ChatMessage(
            id: '${chatId}_$i',
            text: msg['content'],
            isUser: msg['role'] == 'user',
            timestamp: DateTime.now(),
          );
        }).toList();
        return messages;
      } else {
        return [];
      }
    } catch (e) {
      debugPrint('Error loading chat history: $e');
      return [];
    }
  }

  Future<RateLimitInfo> getRateLimitInfo(int userId) async {
    try {
      final response = await http
          .get(
            Uri.parse('$baseUrl/status/$userId'),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return RateLimitInfo.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Failed to get status');
      }
    } catch (e) {
      throw Exception('Error: $e');
    }
  }

  Future<bool> checkHealth() async {
    try {
      final response = await http
          .get(
            Uri.parse(_healthUrl),
          )
          .timeout(const Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  Future<Map<String, dynamic>> sendVoiceMessage(
    int userId,
    String chatId,
    String audioPath, {
    String language = 'kk',
  }) async {
    try {
      final uri = Uri.parse(
        '$baseUrl/voice?user_id=$userId&chat_id=$chatId&language=$language',
      );
      final request = http.MultipartRequest('POST', uri);
      request.files.add(
        await http.MultipartFile.fromPath('audio', audioPath),
      );

      final streamedResponse = await request.send().timeout(
            const Duration(seconds: 60),
          );

      if (streamedResponse.statusCode == 200) {
        final body = await streamedResponse.stream.bytesToString();
        return jsonDecode(body);
      } else if (streamedResponse.statusCode == 429) {
        return {'error': 'rate_limit', 'message': 'Күнделікті лимит асталды'};
      } else {
        final body = await streamedResponse.stream.bytesToString();
        return {'error': 'server_error', 'message': body};
      }
    } on TimeoutException {
      return {'error': 'timeout', 'message': 'Сервер жауап бермеді'};
    } catch (e) {
      debugPrint('Voice API error: $e');
      return {'error': 'unknown', 'message': e.toString()};
    }
  }
}
