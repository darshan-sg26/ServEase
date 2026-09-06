import 'package:flutter/material.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../worker/worker_shell.dart';
import '../provider/provider_shell.dart';
import '../admin/admin_shell.dart';

class RoleSelectionScreen extends StatelessWidget {
  const RoleSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.cream50,
      body: SafeArea(
        child: SingleChildScrollView(
          physics: const BouncingScrollPhysics(),
          child: AppResponsiveContainer(
            maxWidth: 600,
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 12),
                // Brand Logo & Title
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppColors.forest900,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: const Icon(
                        Icons.handshake_outlined,
                        color: AppColors.goldAccent,
                        size: 32,
                      ),
                    ),
                    const SizedBox(width: 14),
                    const Text(
                      'ServEase',
                      style: TextStyle(
                        fontFamily: 'Sora',
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        color: AppColors.ink900,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                const Text(
                  'Digital Trust & Skilled Workforce Marketplace',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: 'Inter',
                    fontSize: 14,
                    color: AppColors.slate600,
                  ),
                ),
                const SizedBox(height: 28),

                const Text(
                  'Select your workspace role:',
                  style: TextStyle(
                    fontFamily: 'Sora',
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: AppColors.ink900,
                  ),
                ),
                const SizedBox(height: 16),

                // Role Card 1: Worker App
                _RoleCard(
                  title: 'Skilled Worker Portal',
                  subtitle: 'Build verified digital trust score, browse nearby open job opportunities, and receive direct job offers.',
                  icon: Icons.engineering_rounded,
                  badge: 'Worker Workspace',
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const WorkerShell()),
                    );
                  },
                ),

                const SizedBox(height: 14),

                // Role Card 2: Job Provider App
                _RoleCard(
                  title: 'Job Provider Portal',
                  subtitle: 'Post job requirements to get ML hybrid matched candidates, or search directory & send direct job offers.',
                  icon: Icons.person_search_rounded,
                  badge: 'Provider Workspace',
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const ProviderShell()),
                    );
                  },
                ),

                const SizedBox(height: 14),

                // Role Card 3: Admin Dashboard
                _RoleCard(
                  title: 'Admin Analytics & Security',
                  subtitle: 'Monitor platform hiring metrics, verify user credentials, and review automated fraud detection flags.',
                  icon: Icons.admin_panel_settings_rounded,
                  badge: 'Admin Console',
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const AdminShell()),
                    );
                  },
                ),

                const SizedBox(height: 32),
                const Text(
                  'VTU Project Phase-1 • Department of CSE(AIML)',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.slate600,
                  ),
                ),
                const SizedBox(height: 12),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RoleCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final String badge;
  final VoidCallback onTap;

  const _RoleCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.badge,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.cream100,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: AppColors.forest900, size: 26),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontFamily: 'Sora',
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppColors.ink900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.slate600,
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppColors.forest600),
        ],
      ),
    );
  }
}
