import 'package:flutter/material.dart';

import '../models/models.dart';

class ChatDrawer extends StatelessWidget {
  final List<ChatInfo> chats;
  final ChatInfo? currentChat;
  final RateLimitInfo? rateLimitInfo;
  final bool isLoadingChats;
  final VoidCallback onCreateNewChat;
  final ValueChanged<ChatInfo> onSwitchChat;
  final ValueChanged<ChatInfo> onDeleteChat;
  final void Function(ChatInfo chat, String newTitle) onRenameChat;

  const ChatDrawer({
    super.key,
    required this.chats,
    required this.currentChat,
    required this.isLoadingChats,
    required this.onCreateNewChat,
    required this.onSwitchChat,
    required this.onDeleteChat,
    required this.onRenameChat,
    this.rateLimitInfo,
  });

  @override
  Widget build(BuildContext context) {
    return Drawer(
      backgroundColor: const Color(0xFF18181B),
      child: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            const Divider(color: Color(0xFF27272A), height: 1),
            _buildNewChatButton(),
            Expanded(child: _buildChatList()),
            if (rateLimitInfo != null) _buildRateLimitFooter(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6366F1), Color(0xFFA855F7)],
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.auto_awesome, size: 18),
          ),
          const SizedBox(width: 12),
          const Text(
            'Чаттар',
            style: TextStyle(
              color: Color(0xFFFAFAFA),
              fontSize: 18,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNewChatButton() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: SizedBox(
        width: double.infinity,
        child: ElevatedButton.icon(
          onPressed: onCreateNewChat,
          icon: const Icon(Icons.add, size: 18),
          label: const Text('Жаңа чат'),
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFFFAFAFA),
            foregroundColor: const Color(0xFF09090B),
            padding: const EdgeInsets.symmetric(vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildChatList() {
    if (isLoadingChats) {
      return const Center(child: CircularProgressIndicator());
    }

    if (chats.isEmpty) {
      return const Center(
        child: Text(
          'Чаттар жоқ',
          style: TextStyle(color: Color(0xFF71717A)),
        ),
      );
    }

    return ListView.builder(
      itemCount: chats.length,
      itemBuilder: (context, index) {
        final chat = chats[index];
        final isActive = chat.chatId == currentChat?.chatId;

        return ListTile(
          selected: isActive,
          selectedTileColor: const Color(0xFF27272A),
          leading: Icon(
            Icons.chat_bubble_outline,
            color: isActive
                ? const Color(0xFF6366F1)
                : const Color(0xFF71717A),
          ),
          title: Text(
            chat.title,
            style: TextStyle(
              color: isActive
                  ? const Color(0xFFFAFAFA)
                  : const Color(0xFFA1A1AA),
              fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
            ),
          ),
          subtitle: chat.lastMessage != null
              ? Text(
                  chat.lastMessage!,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF71717A),
                    fontSize: 12,
                  ),
                )
              : null,
          trailing: PopupMenuButton<String>(
            icon: const Icon(Icons.more_vert, size: 18, color: Color(0xFF71717A)),
            color: const Color(0xFF27272A),
            onSelected: (value) {
              if (value == 'rename') {
                _showRenameDialog(context, chat);
              } else if (value == 'delete') {
                onDeleteChat(chat);
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'rename',
                child: Row(
                  children: [
                    Icon(Icons.edit_outlined, size: 16, color: Color(0xFFA1A1AA)),
                    SizedBox(width: 8),
                    Text('Атын өзгерту', style: TextStyle(color: Color(0xFFA1A1AA))),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'delete',
                child: Row(
                  children: [
                    Icon(Icons.delete_outline, size: 16, color: Color(0xFFEF4444)),
                    SizedBox(width: 8),
                    Text('Жою', style: TextStyle(color: Color(0xFFEF4444))),
                  ],
                ),
              ),
            ],
          ),
          onTap: () => onSwitchChat(chat),
        );
      },
    );
  }

  void _showRenameDialog(BuildContext context, ChatInfo chat) {
    final controller = TextEditingController(text: chat.title);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF18181B),
        title: const Text('Чат атын өзгерту', style: TextStyle(color: Color(0xFFFAFAFA))),
        content: TextField(
          controller: controller,
          autofocus: true,
          style: const TextStyle(color: Color(0xFFFAFAFA)),
          decoration: InputDecoration(
            hintText: 'Жаңа ат...',
            hintStyle: const TextStyle(color: Color(0xFF71717A)),
            enabledBorder: OutlineInputBorder(
              borderSide: const BorderSide(color: Color(0xFF27272A)),
              borderRadius: BorderRadius.circular(8),
            ),
            focusedBorder: OutlineInputBorder(
              borderSide: const BorderSide(color: Color(0xFF6366F1)),
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Болдырмау', style: TextStyle(color: Color(0xFF71717A))),
          ),
          TextButton(
            onPressed: () {
              final newTitle = controller.text.trim();
              if (newTitle.isNotEmpty && newTitle != chat.title) {
                onRenameChat(chat, newTitle);
              }
              Navigator.pop(ctx);
            },
            child: const Text('Сақтау', style: TextStyle(color: Color(0xFF6366F1))),
          ),
        ],
      ),
    );
  }

  Widget _buildRateLimitFooter() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: Color(0xFF27272A)),
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline,
              size: 16, color: Color(0xFF71717A)),
          const SizedBox(width: 8),
          Text(
            'Лимит: ${rateLimitInfo!.remaining}/${rateLimitInfo!.limit}',
            style: const TextStyle(
              color: Color(0xFF71717A),
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}
