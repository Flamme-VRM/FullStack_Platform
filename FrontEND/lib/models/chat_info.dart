class ChatInfo {
  final String chatId;
  final String title;
  final String createdAt;
  final String? lastMessage;
  final int messageCount;

  ChatInfo({
    required this.chatId,
    required this.title,
    required this.createdAt,
    this.lastMessage,
    this.messageCount = 0,
  });

  factory ChatInfo.fromJson(Map<String, dynamic> json) {
    return ChatInfo(
      chatId: json['chat_id'],
      title: json['title'],
      createdAt: json['created_at'],
      lastMessage: json['last_message'],
      messageCount: json['message_count'] ?? 0,
    );
  }
}
