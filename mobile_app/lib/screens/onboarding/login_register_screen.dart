import 'package:flutter/material.dart';
import '../../config/app_config.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../services/api_service.dart';
import '../worker/worker_shell.dart';
import '../provider/provider_shell.dart';
import '../admin/admin_shell.dart';
import 'otp_verification_screen.dart';

class LoginRegisterScreen extends StatefulWidget {
  const LoginRegisterScreen({super.key});

  @override
  State<LoginRegisterScreen> createState() => _LoginRegisterScreenState();
}

class _LoginRegisterScreenState extends State<LoginRegisterScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = false;

  // Login Controllers
  final _loginEmailCtrl = TextEditingController();
  final _loginPwdCtrl = TextEditingController();

  // Register Controllers
  final _regNameCtrl = TextEditingController();
  final _regEmailCtrl = TextEditingController();
  final _regPwdCtrl = TextEditingController();
  final _regPhoneCtrl = TextEditingController();
  String _selectedRole = 'worker';
  final String _regGender = 'prefer_not_to_say';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _loginEmailCtrl.dispose();
    _loginPwdCtrl.dispose();
    _regNameCtrl.dispose();
    _regEmailCtrl.dispose();
    _regPwdCtrl.dispose();
    _regPhoneCtrl.dispose();
    super.dispose();
  }

  void _handleLogin() async {
    final email = _loginEmailCtrl.text.trim();
    final pwd = _loginPwdCtrl.text.trim();

    if (email.isEmpty || pwd.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in email and password')),
      );
      return;
    }

    setState(() => _isLoading = true);
    final res = await ApiService.login(email, pwd);
    setState(() => _isLoading = false);

    if (!mounted) return;

    if (res['success'] == true) {
      final role = res['role'];
      if (role == 'worker') {
        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const WorkerShell()));
      } else if (role == 'provider') {
        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const ProviderShell()));
      } else if (role == 'admin') {
        Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const AdminShell()));
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res['message'] ?? 'Login failed')),
      );
    }
  }

  void _handleRegister() async {
    final name = _regNameCtrl.text.trim();
    final email = _regEmailCtrl.text.trim();
    final pwd = _regPwdCtrl.text.trim();
    final phone = _regPhoneCtrl.text.trim();

    if (name.isEmpty || email.isEmpty || pwd.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all required fields')),
      );
      return;
    }

    setState(() => _isLoading = true);
    final res = await ApiService.register(
      email: email,
      password: pwd,
      fullName: name,
      role: _selectedRole,
      phone: phone.isNotEmpty ? phone : '+919876543210',
      gender: _regGender,
    );
    setState(() => _isLoading = false);

    if (!mounted) return;

    if (res['success'] == true) {
      if (res['requires_verification'] == true) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => OtpVerificationScreen(
              email: email,
              role: _selectedRole,
              fullName: name,
            ),
          ),
        );
      } else {
        final role = res['role'] ?? _selectedRole;
        if (role == 'worker') {
          Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const WorkerShell()));
        } else if (role == 'provider') {
          Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const ProviderShell()));
        } else if (role == 'admin') {
          Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const AdminShell()));
        }
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res['message'] ?? 'Registration failed')),
      );
    }
  }

  void _showServerConfigDialog() {
    final ctrl = TextEditingController(text: ApiService.baseUrl);
    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (dialogCtx, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(
            children: [
              const Icon(Icons.dns_rounded, color: AppColors.forest900),
              const SizedBox(width: 8),
              const Expanded(
                child: Text('API Config', style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold)),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: ApiService.isProduction ? AppColors.cream100 : AppColors.cream50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: ApiService.isProduction ? AppColors.success : AppColors.goldAccent,
                  ),
                ),
                child: Text(
                  AppConfig.activeEnvironmentName,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    color: ApiService.isProduction ? AppColors.success : AppColors.forest900,
                  ),
                ),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Quick Presets:',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppColors.ink900),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    ActionChip(
                      avatar: const Icon(Icons.cloud_done_rounded, size: 14, color: AppColors.success),
                      label: const Text('Render Prod', style: TextStyle(fontSize: 11)),
                      backgroundColor: AppColors.cream50,
                      onPressed: () {
                        setDialogState(() {
                          ctrl.text = AppConfig.prodBaseUrl;
                        });
                      },
                    ),
                    ActionChip(
                      avatar: const Icon(Icons.wifi_rounded, size: 14, color: AppColors.forest900),
                      label: const Text('Laptop Wi-Fi', style: TextStyle(fontSize: 11)),
                      backgroundColor: AppColors.cream100,
                      onPressed: () {
                        setDialogState(() {
                          ctrl.text = AppConfig.devLanBaseUrl;
                        });
                      },
                    ),
                    ActionChip(
                      avatar: const Icon(Icons.phone_android_rounded, size: 14, color: AppColors.slate600),
                      label: const Text('Emulator (10.0.2.2)', style: TextStyle(fontSize: 11)),
                      backgroundColor: AppColors.cream50,
                      onPressed: () {
                        setDialogState(() {
                          ctrl.text = AppConfig.devEmulatorBaseUrl;
                        });
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: ctrl,
                  decoration: const InputDecoration(
                    labelText: 'Base URL',
                    hintText: 'http://10.84.225.101:8000',
                  ),
                  onChanged: (_) => setDialogState(() {}),
                ),
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.cream50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Active Endpoint Preview:',
                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppColors.slate600),
                      ),
                      const SizedBox(height: 4),
                      SelectableText(
                        ctrl.text.trim().isNotEmpty ? '${ctrl.text.trim()}/api/v1' : ApiService.formattedBaseUrl,
                        style: const TextStyle(fontSize: 11, color: AppColors.forest900, fontFamily: 'monospace'),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                setState(() {
                  ApiService.baseUrl = ApiService.defaultBaseUrl;
                });
                Navigator.pop(ctx);
              },
              child: const Text('Reset Default'),
            ),
            ElevatedButton(
              onPressed: () {
                if (ctrl.text.trim().isNotEmpty) {
                  setState(() {
                    ApiService.baseUrl = ctrl.text.trim();
                  });
                }
                Navigator.pop(ctx);
              },
              child: const Text('Save & Apply'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.cream50,
      body: SafeArea(
        child: Stack(
          children: [
            // Top Right Discreet Server Developer Settings Icon
            Positioned(
              top: 12,
              right: 16,
              child: IconButton(
                onPressed: _showServerConfigDialog,
                icon: const Icon(Icons.settings_ethernet_rounded, color: AppColors.slate600, size: 22),
                tooltip: 'Developer API Config (${ApiService.formattedBaseUrl})',
              ),
            ),

            // Main Content Area (Centered and Constrained for Desktop/Web)
            Center(
              child: SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
                child: AppResponsiveContainer(
                  maxWidth: 460,
                  padding: EdgeInsets.zero,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Header Logo & Branding
                      Container(
                        padding: const EdgeInsets.all(18),
                        decoration: BoxDecoration(
                          color: AppColors.forest900,
                          borderRadius: BorderRadius.circular(24),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.forest900.withValues(alpha: 0.2),
                              blurRadius: 16,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.handshake_rounded,
                          color: AppColors.goldAccent,
                          size: 42,
                        ),
                      ),
                      const SizedBox(height: 14),
                      const Text(
                        'ServEase',
                        style: TextStyle(
                          fontFamily: 'Sora',
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                          color: AppColors.ink900,
                          letterSpacing: -0.5,
                        ),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Skilled Workforce Marketplace & Digital Trust Platform',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 13,
                          color: AppColors.slate600,
                        ),
                      ),
                      const SizedBox(height: 28),

                      // Auth Card Container
                      AppCard(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          children: [
                            // Tab Bar Selector
                            Container(
                              height: 46,
                              decoration: BoxDecoration(
                                color: AppColors.cream100,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: TabBar(
                                controller: _tabController,
                                indicator: BoxDecoration(
                                  borderRadius: BorderRadius.circular(10),
                                  color: AppColors.forest900,
                                ),
                                indicatorSize: TabBarIndicatorSize.tab,
                                labelColor: AppColors.white,
                                unselectedLabelColor: AppColors.slate600,
                                labelStyle: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontFamily: 'Sora',
                                  fontSize: 14,
                                ),
                                tabs: const [
                                  Tab(text: 'Sign In'),
                                  Tab(text: 'Create Account'),
                                ],
                              ),
                            ),
                            const SizedBox(height: 24),

                            // Tab Content Views
                            SizedBox(
                              height: 440,
                              child: TabBarView(
                                controller: _tabController,
                                children: [
                                  _buildLoginTab(),
                                  _buildRegisterTab(),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 24),
                      const Text(
                        'VTU Project Phase-2 • Dept. of CSE(AIML)',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 12, color: AppColors.slate600),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoginTab() {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _loginEmailCtrl,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(
              labelText: 'Email Address',
              prefixIcon: Icon(Icons.email_outlined, size: 20),
            ),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _loginPwdCtrl,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: 'Password',
              prefixIcon: Icon(Icons.lock_outline, size: 20),
            ),
          ),
          const SizedBox(height: 20),

          AppButton(
            label: 'Sign In to Workspace',
            icon: Icons.login_rounded,
            isLoading: _isLoading,
            isFullWidth: true,
            onPressed: _handleLogin,
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _buildRegisterTab() {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Account Role:',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppColors.ink900),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: ChoiceChip(
                  label: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.engineering_rounded, size: 16),
                      SizedBox(width: 6),
                      Text('Worker'),
                    ],
                  ),
                  selected: _selectedRole == 'worker',
                  selectedColor: AppColors.forest900,
                  labelStyle: TextStyle(
                    color: _selectedRole == 'worker' ? AppColors.white : AppColors.ink900,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                  onSelected: (sel) {
                    if (sel) setState(() => _selectedRole = 'worker');
                  },
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ChoiceChip(
                  label: const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.person_search_rounded, size: 16),
                      SizedBox(width: 6),
                      Text('Job Provider'),
                    ],
                  ),
                  selected: _selectedRole == 'provider',
                  selectedColor: AppColors.forest900,
                  labelStyle: TextStyle(
                    color: _selectedRole == 'provider' ? AppColors.white : AppColors.ink900,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                  onSelected: (sel) {
                    if (sel) setState(() => _selectedRole = 'provider');
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          TextField(
            controller: _regNameCtrl,
            decoration: const InputDecoration(
              labelText: 'Full Name',
              prefixIcon: Icon(Icons.person_outline, size: 20),
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _regEmailCtrl,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(
              labelText: 'Email Address',
              prefixIcon: Icon(Icons.email_outlined, size: 20),
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _regPhoneCtrl,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(
              labelText: 'Phone Number',
              prefixIcon: Icon(Icons.phone_outlined, size: 20),
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _regPwdCtrl,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: 'Password',
              prefixIcon: Icon(Icons.lock_outline, size: 20),
            ),
          ),
          const SizedBox(height: 18),

          AppButton(
            label: 'Register ${_selectedRole == 'worker' ? 'Worker' : 'Provider'} Account',
            icon: Icons.person_add_rounded,
            isLoading: _isLoading,
            isFullWidth: true,
            onPressed: _handleRegister,
          ),
        ],
      ),
    );
  }
}
