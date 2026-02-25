import 'package:flutter/material.dart';

class WelcomeScreen extends StatelessWidget {
  final bool isServerHealthy;

  const WelcomeScreen({super.key, required this.isServerHealthy});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(height: 40),
          _buildStatusBadge(),
          const SizedBox(height: 24),
          const Text(
            'Ready to learn,',
            style: TextStyle(
              color: Color(0xFFFAFAFA),
              fontSize: 28,
              fontWeight: FontWeight.w500,
            ),
          ),
          const Text(
            'Student?',
            style: TextStyle(
              color: Color(0xFF71717A),
              fontSize: 28,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Мен ЕНТ-ға дайындалуға көмектесетін AI ассистентімін. Сұрақтарыңызды қазақ тілінде жазыңыз!',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Color(0xFF71717A),
              fontSize: 14,
              fontWeight: FontWeight.w300,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 32),
          _buildCapabilityCard(
            icon: Icons.calculate_outlined,
            color: const Color(0xFF6366F1),
            title: 'Математикалық сауаттылық',
            subtitle: 'Логарифмдік теңдеулерді шешу',
          ),
          const SizedBox(height: 12),
          _buildCapabilityCard(
            icon: Icons.history_edu_outlined,
            color: const Color(0xFF10B981),
            title: 'Қазақстан тарихы',
            subtitle: 'Қазақ хандығының құрылуы',
          ),
          const SizedBox(height: 12),
          _buildCapabilityCard(
            icon: Icons.psychology_outlined,
            color: const Color(0xFFF59E0B),
            title: 'Сыни ойлау',
            subtitle: 'Оқу сауаттылығы сұрақтары',
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF18181B).withOpacity(0.8),
        border: Border.all(color: const Color(0xFF27272A)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: isServerHealthy
                  ? const Color(0xFF10B981)
                  : const Color(0xFFEF4444),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            isServerHealthy
                ? 'UNT Preparation Model v2.4'
                : 'Серверге қосылу мүмкін емес',
            style: const TextStyle(
              color: Color(0xFFA1A1AA),
              fontSize: 11,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCapabilityCard({
    required IconData icon,
    required Color color,
    required String title,
    required String subtitle,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF18181B).withOpacity(0.2),
        border: Border.all(color: const Color(0xFF27272A)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF18181B),
              border: Border.all(color: const Color(0xFF27272A)),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, color: color, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Color(0xFFE4E4E7),
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: Color(0xFF71717A),
                    fontSize: 12,
                    fontWeight: FontWeight.w300,
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
