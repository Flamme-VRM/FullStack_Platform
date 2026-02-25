import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../models/rate_limit_info.dart';

class ChatInputArea extends StatefulWidget {
  final TextEditingController controller;
  final bool isLoading;
  final bool isServerHealthy;
  final bool hasChatSelected;
  final RateLimitInfo? rateLimitInfo;
  final VoidCallback onSend;
  final ValueChanged<String>? onSendVoice;

  const ChatInputArea({
    super.key,
    required this.controller,
    required this.isLoading,
    required this.isServerHealthy,
    required this.hasChatSelected,
    required this.onSend,
    this.onSendVoice,
    this.rateLimitInfo,
  });

  @override
  State<ChatInputArea> createState() => _ChatInputAreaState();
}

class _ChatInputAreaState extends State<ChatInputArea> {
  final AudioRecorder _recorder = AudioRecorder();
  bool _isRecording = false;
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onTextChanged);
    _recorder.dispose();
    super.dispose();
  }

  void _onTextChanged() {
    final hasText = widget.controller.text.trim().isNotEmpty;
    if (hasText != _hasText) {
      setState(() => _hasText = hasText);
    }
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      await _stopRecording();
    } else {
      await _startRecording();
    }
  }

  Future<void> _startRecording() async {
    try {
      if (await _recorder.hasPermission()) {
        final dir = await getTemporaryDirectory();
        final path = '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a';

        await _recorder.start(
          const RecordConfig(
            encoder: AudioEncoder.aacLc,
            sampleRate: 16000,
            numChannels: 1,
          ),
          path: path,
        );

        setState(() => _isRecording = true);
      }
    } catch (e) {
      debugPrint('Recording start error: $e');
    }
  }

  Future<void> _stopRecording() async {
    try {
      final path = await _recorder.stop();
      setState(() => _isRecording = false);

      if (path != null && widget.onSendVoice != null) {
        widget.onSendVoice!(path);
      }
    } catch (e) {
      debugPrint('Recording stop error: $e');
      setState(() => _isRecording = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool inputEnabled =
        !widget.isLoading && widget.isServerHealthy && widget.hasChatSelected;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF09090B),
        border: Border(
          top: BorderSide(
            color: const Color(0xFF27272A).withOpacity(0.5),
            width: 1,
          ),
        ),
      ),
      child: Column(
        children: [
          if (widget.rateLimitInfo != null) _buildRateLimitBadge(),
          _buildTextField(inputEnabled),
          const Padding(
            padding: EdgeInsets.only(top: 12),
            child: Text(
              'AsylBILIM қателер жібере алады. Маңызды ақпаратты тексеріңіз.',
              style: TextStyle(
                color: Color(0xFF52525B),
                fontSize: 10,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRateLimitBadge() {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF18181B).withOpacity(0.5),
        border: Border.all(
            color: const Color(0xFF27272A).withOpacity(0.5)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'КҮНДЕЛІКТІ ЛИМИТ',
            style: TextStyle(
              color: Color(0xFF71717A),
              fontSize: 10,
              fontWeight: FontWeight.w500,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '${widget.rateLimitInfo!.remaining}/${widget.rateLimitInfo!.limit}',
            style: const TextStyle(
              color: Color(0xFFFAFAFA),
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextField(bool enabled) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF18181B).withOpacity(0.8),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: _isRecording
              ? const Color(0xFFEF4444)
              : const Color(0xFF27272A),
        ),
      ),
      child: Column(
        children: [
          if (_isRecording)
            const Padding(
              padding: EdgeInsets.fromLTRB(16, 14, 16, 0),
              child: Row(
                children: [
                  Icon(Icons.fiber_manual_record, color: Color(0xFFEF4444), size: 12),
                  SizedBox(width: 8),
                  Text(
                    'Жазу жүріп жатыр...',
                    style: TextStyle(color: Color(0xFFEF4444), fontSize: 14),
                  ),
                ],
              ),
            )
          else
            TextField(
              controller: widget.controller,
              maxLines: null,
              keyboardType: TextInputType.multiline,
              style: const TextStyle(
                color: Color(0xFFFAFAFA),
                fontSize: 14,
              ),
              decoration: const InputDecoration(
                hintText: 'Сұрақ қойыңыз...',
                hintStyle: TextStyle(
                  color: Color(0xFF71717A),
                  fontSize: 14,
                ),
                border: InputBorder.none,
                contentPadding: EdgeInsets.all(16),
              ),
              enabled: enabled,
              onSubmitted: (_) => widget.onSend(),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                // Mic button
                if (widget.onSendVoice != null && !_hasText)
                  Container(
                    margin: const EdgeInsets.only(right: 8),
                    decoration: BoxDecoration(
                      color: _isRecording
                          ? const Color(0xFFEF4444)
                          : const Color(0xFF27272A),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: IconButton(
                      icon: Icon(
                        _isRecording ? Icons.stop : Icons.mic,
                        size: 20,
                      ),
                      color: const Color(0xFFFAFAFA),
                      onPressed: enabled ? _toggleRecording : null,
                    ),
                  ),
                // Send button
                Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFFFAFAFA),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.arrow_upward, size: 20),
                    color: const Color(0xFF09090B),
                    onPressed: enabled && _hasText ? widget.onSend : null,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
