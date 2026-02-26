import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../models/chat_message.dart';

class MessageBubble extends StatelessWidget {
  final ChatMessage message;
  final bool animate;

  const MessageBubble({super.key, required this.message, this.animate = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        mainAxisAlignment: message.isUser
            ? MainAxisAlignment.end
            : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!message.isUser) ...[
            _buildBotAvatar(),
            const SizedBox(width: 12),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: message.isUser
                    ? const Color(0xFFFAFAFA)
                    : const Color(0xFF18181B).withOpacity(0.8),
                borderRadius: BorderRadius.circular(12),
                border: message.isUser
                    ? null
                    : Border.all(color: const Color(0xFF27272A)),
              ),
              child: message.isUser
                  ? Text(
                      message.text,
                      style: const TextStyle(
                        color: Color(0xFF09090B),
                        fontSize: 14,
                        height: 1.5,
                      ),
                    )
                  : animate
                  ? _TypewriterMarkdown(fullText: message.text)
                  : _botMarkdown(message.text),
            ),
          ),
          if (message.isUser) ...[
            const SizedBox(width: 12),
            _buildUserAvatar(),
          ],
        ],
      ),
    );
  }

  static Widget _botMarkdown(String text) {
    return MarkdownBody(data: text, styleSheet: _markdownStyle);
  }

  static final _markdownStyle = MarkdownStyleSheet(
    p: const TextStyle(color: Color(0xFFFAFAFA), fontSize: 14, height: 1.5),
    h1: const TextStyle(
      color: Color(0xFFFAFAFA),
      fontSize: 22,
      fontWeight: FontWeight.bold,
    ),
    h2: const TextStyle(
      color: Color(0xFFFAFAFA),
      fontSize: 18,
      fontWeight: FontWeight.bold,
    ),
    h3: const TextStyle(
      color: Color(0xFFFAFAFA),
      fontSize: 16,
      fontWeight: FontWeight.w600,
    ),
    listBullet: const TextStyle(color: Color(0xFFFAFAFA)),
    strong: const TextStyle(
      color: Color(0xFFFAFAFA),
      fontWeight: FontWeight.bold,
    ),
    em: const TextStyle(color: Color(0xFFE4E4E7), fontStyle: FontStyle.italic),
    code: const TextStyle(
      color: Color(0xFF6366F1),
      backgroundColor: Color(0xFF27272A),
      fontSize: 13,
    ),
    codeblockDecoration: BoxDecoration(
      color: const Color(0xFF27272A),
      borderRadius: BorderRadius.circular(8),
    ),
  );

  Widget _buildBotAvatar() {
    return Container(
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF27272A), Color(0xFF3F3F46)],
        ),
        border: Border.all(color: const Color(0xFF52525B).withOpacity(0.5)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: const Icon(Icons.auto_awesome, size: 16, color: Color(0xFFFAFAFA)),
    );
  }

  Widget _buildUserAvatar() {
    return Container(
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF6366F1), Color(0xFFA855F7)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
        borderRadius: BorderRadius.circular(16),
      ),
      child: const Center(
        child: Text(
          'S',
          style: TextStyle(
            color: Color(0xFFE4E4E7),
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }
}

/// Reveals text word-by-word, rendering as Markdown at each step.
class _TypewriterMarkdown extends StatefulWidget {
  final String fullText;

  const _TypewriterMarkdown({required this.fullText});

  @override
  State<_TypewriterMarkdown> createState() => _TypewriterMarkdownState();
}

class _TypewriterMarkdownState extends State<_TypewriterMarkdown> {
  late List<String> _words;
  int _visibleCount = 0;
  Timer? _timer;
  bool _done = false;

  @override
  void initState() {
    super.initState();
    _words = widget.fullText.split(RegExp(r'(?<=\s)'));
    _startRevealing();
  }

  void _startRevealing() {
    // Reveal 2 words every 30ms = ~66 words/sec, feels fast but visible
    _timer = Timer.periodic(const Duration(milliseconds: 30), (timer) {
      if (_visibleCount >= _words.length) {
        timer.cancel();
        setState(() => _done = true);
        return;
      }
      setState(() {
        _visibleCount = (_visibleCount + 2).clamp(0, _words.length);
      });
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final displayText = _done
        ? widget.fullText
        : _words.take(_visibleCount).join('');

    return MarkdownBody(
      data: displayText,
      styleSheet: MessageBubble._markdownStyle,
    );
  }
}

class LoadingBubble extends StatefulWidget {
  const LoadingBubble({super.key});

  @override
  State<LoadingBubble> createState() => _LoadingBubbleState();
}

class _LoadingBubbleState extends State<LoadingBubble>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF27272A), Color(0xFF3F3F46)],
              ),
              border: Border.all(
                color: const Color(0xFF52525B).withOpacity(0.5),
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.auto_awesome,
              size: 16,
              color: Color(0xFFFAFAFA),
            ),
          ),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: const Color(0xFF18181B).withOpacity(0.8),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF27272A)),
            ),
            child: AnimatedBuilder(
              animation: _controller,
              builder: (context, _) {
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: List.generate(3, (i) {
                    final delay = i * 0.2;
                    final value = _controller.value;
                    final offset = ((value - delay) % 1.0).clamp(0.0, 1.0);
                    final opacity = offset < 0.5
                        ? (offset * 2).clamp(0.3, 1.0)
                        : ((1.0 - offset) * 2).clamp(0.3, 1.0);

                    return Padding(
                      padding: EdgeInsets.only(right: i < 2 ? 6 : 0),
                      child: Opacity(
                        opacity: opacity,
                        child: Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: Color(0xFF6366F1),
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                    );
                  }),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
